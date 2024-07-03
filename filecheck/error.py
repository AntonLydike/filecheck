import re
from typing import Any


class CheckError(Exception):
    message: str
    pattern: re.Pattern[str] | None

    def __init__(self, msg: str, *args: Any, pattern: re.Pattern[str] | None = None):
        self.message = msg
        self.pattern = pattern
        super().__init__(args)


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
