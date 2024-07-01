import re
from typing import Callable

POSIX_REGEXP_PATTERN = re.compile(
    r"\[:(alpha|upper|lower|digit|alnum|xdigit|space|blank|print|punct|graph|word|ascii|cntrl):]"
)
POSIX_REGEXP_REPLACEMENTS = {
    "alpha": "[A-Za-z]",
    "upper": "[A-Z]",
    "lower": "[a-z]",
    "digit": "[0-9]",
    "alnum": "[A-Za-z0-9]",
    "xdigit": "[A-Fa-f0-9]",
    "space": r"\s",
    "blank": r"[ \t]",
    "word": r"\w+",
}


def posix_to_python_regex(expr: str) -> str:
    """
    We need to translate things like `[:alpha:]` to `[A-Za-z]`, etc.

    LLVM supports them, but pythons regex doesn't.
    """
    while (match := POSIX_REGEXP_PATTERN.search(expr)) is not None:
        if match.group(1) not in POSIX_REGEXP_REPLACEMENTS:
            raise ValueError(
                f"Can't translate posix regex, unknown character set: {match.group(1)}"
            )
        expr = expr.replace(match.group(0), POSIX_REGEXP_REPLACEMENTS[match.group(1)])
    return expr


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
