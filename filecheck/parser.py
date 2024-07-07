"""
parser for filecheck syntax
"""

from dataclasses import dataclass, field
from typing import Iterator, TextIO
import re

from filecheck.error import ParseError
from filecheck.ops import CheckOp, Literal, RE, Capture, Subst, NumSubst, UOp, CountOp
from filecheck.options import Options, parse_argv_options, Extension
from filecheck.regex import (
    posix_to_python_regex,
    pattern_from_num_subst_spec,
    mlir_regex_extensions,
)


def pattern_for_opts(opts: Options) -> tuple[re.Pattern[str], re.Pattern[str]]:
    return re.compile(
        re.escape(opts.check_prefix)
        + r"(-(DAG|COUNT-\d+|NOT|EMPTY|NEXT|SAME|LABEL))?(\{LITERAL})?:\s?([^\n]*)\n?"
    ), re.compile(
        "("
        + "|".join(map(re.escape, opts.comment_prefixes))
        + ").*"
        + re.escape(opts.check_prefix)
    )


# see https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-string-substitution-blocks
VAR_CAPTURE_PATTERN = re.compile(r"\[\[(\$?[a-zA-Z_][a-zA-Z0-9_]*):([^\n]+)]]")

# see https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-string-substitution-blocks
VAR_SUBST_PATTERN = re.compile(r"\[\[(\$?[a-zA-Z_][a-zA-Z0-9_]*)]]")

# numeric substitution blocks, see:
# https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-numeric-substitution-blocks
NUMERIC_CAPTURE_PATTERN = re.compile(
    r"\[\[#(%(\.[0-9]+)?([udxX])?,)?((\$?[a-zA-Z_][a-zA-Z0-9_]+):(\d+)?)?]]"
)

# numeric substitution blocks, see:
# https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-numeric-substitution-blocks
NUMERIC_SUBST_PATTERN = re.compile(
    r"\[\[#(\$?[a-zA-Z_][a-zA-Z0-9_]*)([a-z0-9 +\-()]*)]]"
)


LINE_SPLIT_RE = split = re.compile(r"(\{\{|\[\[|]]|}})")


@dataclass
class Parser(Iterator[CheckOp]):
    """
    parse a file containing filecheck directives and returns all found check directives
    """

    opts: Options

    input: TextIO

    check_line_regexp: re.Pattern[str]
    comment_line_regexp: re.Pattern[str]

    line_no: int = field(default=0)
    line: str = field(default="")

    @classmethod
    def from_opts(cls, opts: Options):
        return Parser(opts, open(opts.match_filename), *pattern_for_opts(opts))

    def __next__(self) -> CheckOp:
        """
        Scans forward in self.input until a line matching  self.check_line_regexp is
        found. Returns the kind (CHECK/NEXT/DAG/EMPTY/NOT) and the arg (whatever comes
        after the colon).

        Note that for all CHECK-<thing>: it returns <thing> as kind, but for CHECK: it
        returns CHECK.
        """
        while True:
            self.line_no += 1
            line = self.input.readline()
            if line == "":
                raise StopIteration()
            # skip any lines containing comment markers before checks
            if self.comment_line_regexp.search(line) is not None:
                continue
            match = self.check_line_regexp.search(line)
            # no check line = skip
            if match is None:
                continue
            kind = match.group(2)
            literal = match.group(3)
            arg = match.group(4)
            if kind is None:
                kind = "CHECK"
            if arg is None:
                arg = ""
            # verify that non-empty checks have an actual thing to match
            if kind != "EMPTY":
                if not arg:
                    raise ParseError(
                        f"found empty check string with prefix '{kind}:'",
                        self.line_no,
                        match.start(3),
                        line,
                    )
            if not self.opts.strict_whitespace:
                arg = arg.strip()

            # parse the uops, but only if we are not in LITERAL mode
            uops: list[UOp]
            if literal is None:
                uops = self.parse_args(arg, line)
            else:
                uops = [Literal(arg)]

            # special case for COUNT ops
            if kind.startswith("COUNT"):
                count = int(kind[6:])
                if count == 0:
                    raise ParseError(
                        f"invalid count in -COUNT specification on prefix '{opts.check_prefix}' (count can't be 0)",
                        self.line_no,
                        match.end(2),
                        line,
                    )
                return CountOp(
                    "COUNT",
                    arg,
                    self.line_no,
                    uops,
                    is_literal=literal is not None,
                    count=count,
                )
            return CheckOp(
                kind, arg, self.line_no, uops, is_literal=literal is not None
            )

    def parse_args(self, arg: str, line: str) -> list[UOp]:
        """
        parse check args into uops that can later be compiled into a regex

        Returns a list of uops
        """
        uops: list[UOp] = []
        parts = LINE_SPLIT_RE.split(arg)
        offset = len(line) - len(arg)
        while parts:
            part = parts.pop(0)
            if part == "[[":
                # grab parts greedily until we hit a ]]
                while not part.endswith("]]"):
                    if not parts:
                        raise ParseError(
                            "Invalid substitution block, no ]]",
                            self.line_no,
                            offset,
                            line,
                        )
                    part += parts.pop(0)
                # check if we are a simple capture pattern [[<name>:<regex>]]
                if match := VAR_CAPTURE_PATTERN.fullmatch(part):
                    re_expr = posix_to_python_regex(match.group(2))
                    if Extension.MLIR_REGEX_CLS in Extension:
                        re_expr = mlir_regex_extensions(re_expr)
                    uops.append(
                        Capture(
                            match.group(1),
                            re_expr,
                            str,
                        )
                    )
                # check if we are a simple substitution pattern: [[<<name>>]]
                elif match := VAR_SUBST_PATTERN.fullmatch(part):
                    uops.append(Subst(match.group(1)))
                # check if we are a numeric substitution pattern [[#<name>(<expr>)?]]
                elif match := NUMERIC_SUBST_PATTERN.fullmatch(part):
                    # simplify to non-numeric substitution if expr is empty
                    if match.group(2) is None or match.group(2).strip() == "":
                        uops.append(Subst(match.group(1)))
                    else:
                        uops.append(NumSubst(match.group(1), match.group(2)))
                # numeric capture patterns are a tricky bunch
                # see https://llvm.org/docs/CommandGuide/FileCheck.html#filecheck-numeric-substitution-blocks
                elif match := NUMERIC_CAPTURE_PATTERN.fullmatch(part):
                    pattern, mapper = pattern_from_num_subst_spec(
                        match.group(2), match.group(3)
                    )
                    uops.append(Capture(match.group(5), pattern, mapper))
                else:
                    raise ParseError(
                        f"Invalid substitution block, unknown format: {part}",
                        self.line_no,
                        offset,
                        line,
                    )
            elif part == "{{":
                while not part.endswith("}}"):
                    if not parts:
                        raise ParseError(
                            "Invalid regex block, no }}", self.line_no, offset, line
                        )
                    part += parts.pop(0)

                pattern = part[2:-2]

                re_expr = posix_to_python_regex(pattern)
                if Extension.MLIR_REGEX_CLS in Extension:
                    re_expr = mlir_regex_extensions(re_expr)

                uops.append(RE(re_expr))
            elif part != "":
                uops.append(Literal(part))
            offset += len(part)
        return uops


if __name__ == "__main__":
    import sys

    opts = parse_argv_options(sys.argv)
    for p in Parser.from_opts(opts):
        print(p)
