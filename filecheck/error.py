import re


class CheckError(Exception):
    message: str
    pattern: re.Pattern | None

    def __init__(self, msg: str, *args, pattern: re.Pattern | None = None):
        self.message = msg
        self.pattern = pattern
        super().__init__(args)
