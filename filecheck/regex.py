import re
import sys
from dataclasses import dataclass
from typing import Callable

POSIX_REGEXP_PATTERN = re.compile(
    r"\[:(alpha|upper|lower|digit|alnum|xdigit|space|blank|print|punct|graph|word|ascii|cntrl):]"
)
POSIX_REGEXP_REPLACEMENTS = {
    "alpha": "A-Za-z",
    "upper": "A-Z",
    "lower": "a-z",
    "digit": "0-9",
    "alnum": "A-Za-z0-9",
    "xdigit": "A-Fa-f0-9",
    "space": r"\s",
    "blank": r" \t",
}

NEGATED_SET_WITHOUT_NEWLINES = re.compile(r"([^\\]|^)\[\^((?!\\n))")


def posix_to_python_regex(expr: str) -> str:
    """
    We need to translate things like `[:alpha:]` to `[A-Za-z]`, etc.

    This also takes care of a little known fact about the llvm::Regex implementation:

    ```
    enum llvm::Regex::RegexFlags::Newline = 2U

    Compile for newline-sensitive matching. With this flag '[^' bracket
    expressions and '.' never match newline. A ^ anchor matches the
    null string after any newline in the string in addition to its normal
    function, and the $ anchor matches the null string before any
    newline in the string in addition to its normal function.
    ```

    This bad boy is enabled in all FileCheck cases, meaning we need to also add `\n` to all
    negative bracket expressions, otherwise we'll eat *so* many newlines.

    LLVM supports them, but pythons regex doesn't.
    """
    while (match := POSIX_REGEXP_PATTERN.search(expr)) is not None:
        if match.group(1) not in POSIX_REGEXP_REPLACEMENTS:
            raise ValueError(
                f"Can't translate posix regex, unknown character set: {match.group(1)}"
            )
        expr = expr.replace(match.group(0), POSIX_REGEXP_REPLACEMENTS[match.group(1)])

    expr = NEGATED_SET_WITHOUT_NEWLINES.sub(r"\1[^\\n\2", expr)

    return expr


def mlir_regex_extensions(expr: str) -> str:
    """
    This implements the special extensions for MLIR regex classes, enabled with the
    FILECHECK_FEATURE_ENABLE=MLIR_REGEX_CLS feature flag.
    """
    return expr.replace(r"\V", r"%([0-9]+|[A-Za-z_.$-][A-Za-z_.$0-9-]*)(#\d+)?")


ENCODINGS_MAP = {
    "u": r"\d",
    "d": r"[+-]?\d",
    "x": "[a-f0-9]",
    "X": "[A-F0-9]",
}


def pattern_from_num_subst_spec(
    digits: str | None, encoding: str | None
) -> tuple[str, Callable[[str], int]]:
    digits_expr = "+" if digits is None else f"{{{int(digits[1:])}}}"
    if encoding is None:
        encoding = "u"
    return f"{ENCODINGS_MAP[encoding]}{digits_expr}", (
        hex_int if encoding.lower() == "x" else int
    )


def hex_int(v: str):
    return int(v, base=16)


class LiteralMatch:
    """
    Replaces re.Match class for literal matches
    """

    _start: int
    _end: int
    _content: str

    def __init__(self, start: int, content: str):
        self._start = start
        self._end = start + len(content)
        self._content = content

    def start(self, group: int = 0):
        assert group == 0
        return self._start

    def end(self, group: int = 0):
        assert group == 0
        return self._end

    def group(self, group: int):
        assert group == 0
        return self._content


@dataclass
class LiteralMatcher:
    """
    Class meant to emulate re.Pattern class for strictly literal patterns
    """

    pattern: str
    strict_whitespace: bool
    match_on_next_line: bool

    def search(
        self, string: str, pos: int = 0, endpos: int = sys.maxsize
    ) -> LiteralMatch | None:
        """
        Scan through string looking for the first location where this regular expression produces a match, and return a
        corresponding Match. Return None if no position in the string matches the pattern; note that this is different
        from finding a zero-length match at some point in the string.
        """
        start = string.find(self.pattern, pos, endpos)
        if start != -1:
            return LiteralMatch(start, self.pattern)

        if self.strict_whitespace:
            return None

        # match whitespace insensitive
        parts = re.split(r"\s+", self.pattern)

        while pos < endpos:
            candidate_start = string.find(parts[0], pos, endpos)
            if candidate_start == -1:
                return None
            match_pos = candidate_start + len(parts[0])
            did_match = False
            for part in parts[1:]:
                # eat space
                while string[match_pos].isspace():
                    match_pos += 1
                if string.startswith(part, match_pos, endpos):
                    match_pos += len(part)
                else:
                    break
            else:
                # set did_match to true, if loop didn't break
                did_match = True
            if did_match:
                return LiteralMatch(candidate_start, string[candidate_start:match_pos])
            pos = candidate_start + 1

    def match(
        self, string: str, pos: int = 0, endpos: int = sys.maxsize
    ) -> LiteralMatch | None:
        """
        If zero or more characters at the beginning of string match this regular expression, return a corresponding
        Match. Return None if the string does not match the pattern; note that this is different from a zero-length
        match.
        """
        if self.match_on_next_line:
            if string[pos] == "\n":
                pos += 1
            new_endpos = string.find("\n", pos, endpos)
            if new_endpos == -1:
                new_endpos = endpos
            return self.search(string, pos, new_endpos)

        if string.startswith(self.pattern, pos, endpos):
            return LiteralMatch(pos, self.pattern)

        if self.strict_whitespace:
            return None

        # match space insensitive
        match_pos = pos
        parts = re.split(r"\s+", self.pattern)
        # for each part but not the last one, check the part and eat whitespace
        for part in parts[:-1]:
            # check that we start with the part
            if not string.startswith(part, match_pos, endpos):
                return None
            match_pos += len(part)
            # then eat space
            while string[match_pos].isspace():
                match_pos += 1
        # check last part of pattern
        if not string.startswith(parts[-1], match_pos, endpos):
            return None
        match_pos += len(parts[-1])
        return LiteralMatch(pos, string[pos:match_pos])
