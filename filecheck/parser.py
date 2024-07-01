"""
parser for filecheck syntax
"""

from dataclasses import dataclass, field
from typing import Iterator, TextIO
import re

from filecheck.ops import CheckOp, Literal, RE, Capture, Subst, NumSubst, UOp
from filecheck.options import Options, parse_argv_options
from filecheck.regex import posix_to_python_regex, pattern_from_num_subst_spec


def pattern_for_opts(opts: Options) -> re.Pattern:
    return re.compile(
        "((" + "|".join(map(re.escape, opts.comment_prefixes)) + r"):)?[^\n]*"
        + re.escape(opts.check_prefix)
        + r"(-(DAG|COUNT|NOT|EMPTY|NEXT|SAME|LABEL))?:\s?([^\n]*)\n?"
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

    check_line_regexp: re.Pattern

    _line: int = field(default=0)

    @classmethod
    def from_opts(cls, opts: Options):
        return Parser(opts, open(opts.match_filename), pattern_for_opts(opts))

    def __next__(self):
        kind, arg, line = self.next_matching_line()
        return CheckOp(kind, arg, line, self.parse_args(arg))

    def next_matching_line(self) -> tuple[str, str, int]:
        """
        Scans forward in self.input until a line matching  self.check_line_regexp is
        found. Returns the kind (CHECK/NEXT/DAG/EMPTY/NOT) and the arg (whatever comes
        after the colon).

        Note that for all CHECK-<thing>: it returns <thing> as kind, but for CHECK: it
        returns CHECK.
        """
        while True:
            self._line += 1
            line = self.input.readline()
            if line == "":
                raise StopIteration()

            match = self.check_line_regexp.search(line)
            # no check line = skip
            if match is None:
                continue
            # skip lines containing comment markers, even through they also contain check lines
            if match.group(1) is not None:
                continue
            kind = match.group(4)
            arg = match.group(5)
            if kind is None:
                kind = "CHECK"
            if arg is None:
                arg = ""
            if not self.opts.strict_whitespace:
                arg = arg.strip()
            return kind, arg, self._line

    def parse_args(self, arg: str) -> list[UOp]:
        """
        parse check args into uops that can later be compiled into a regex

        Returns a list of uops
        """
        uops = []
        parts = LINE_SPLIT_RE.split(arg)
        while parts:
            part = parts.pop(0)
            if part == "[[":
                # grab parts greedily until we hit a ]]
                while not part.endswith("]]"):
                    assert len(parts) > 0, "Malformed substitution pattern"
                    part += parts.pop(0)
                # check if we are a simple capture pattern [[<name>:<regex>]]
                if match := VAR_CAPTURE_PATTERN.fullmatch(part):
                    uops.append(Capture(match.group(1), match.group(2), str))
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
            elif part == "{{":
                assert len(parts) > 0, "Malformed regex pattern"
                next_part = parts.pop(0)
                while not next_part.endswith("}}"):
                    assert len(parts) > 0, "Malformed regex pattern"
                    next_part += parts.pop(0)

                pattern = next_part[:-2]
                uops.append(RE(posix_to_python_regex(pattern)))
            elif part != "":
                uops.append(Literal(part))
        return uops


if __name__ == "__main__":
    import sys

    opts = parse_argv_options(sys.argv)
    for p in Parser.from_opts(opts):
        print(p)
