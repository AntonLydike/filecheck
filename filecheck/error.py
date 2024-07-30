from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from filecheck.ops import CheckOp

if TYPE_CHECKING:
    from filecheck.compiler import MatchT


class CheckError(Exception):
    message: str
    op: CheckOp

    def __init__(self, msg: str, op: CheckOp, *args: Any):
        super().__init__(*args)
        self.message = msg
        self.op = op


@dataclass
class ErrorOnMatch(Exception):
    """
    Signal error on the provided match
    """

    message: str
    op: CheckOp
    match: "MatchT"


@dataclass
class ParseError(Exception):
    """
    Signal an error during parsing
    """

    message: str
    line_no: int
    offset: int
    offending_line: str
