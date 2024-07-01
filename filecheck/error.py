import re
from typing import Any


class CheckError(Exception):
    message: str
    pattern: re.Pattern[str] | None

    def __init__(self, msg: str, *args: Any, pattern: re.Pattern[str] | None = None):
        self.message = msg
        self.pattern = pattern
        super().__init__(args)
