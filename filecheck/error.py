import re
from typing import Any

from filecheck.ops import CheckOp


class CheckError(Exception):
    message: str
    op: CheckOp
    pattern: re.Pattern[str] | None

    def __init__(
        self, msg: str, op: CheckOp, *args: Any, pattern: re.Pattern[str] | None = None
    ):
        super().__init__(*args)
        self.message = msg
        self.op = op
        self.pattern = pattern


class ParseError(Exception):
    message: str
    line_no: int
    offset: int
    offending_line: str

    def __init__(
        self, message: str, line_no: int, offset: int, offending_line: str, *args: Any
    ):
        super().__init__(*args)
        self.message = message
        self.line_no = line_no
        self.offset = offset
        self.offending_line = offending_line
