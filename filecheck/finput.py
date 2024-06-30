"""
Manages the file input and the position we are at
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import TextIO

from filecheck.options import Options


@dataclass
class FInput:
    fname: str
    content: str
    pos: int = field(default=0)

    line_no: int = field(default=0)

    @staticmethod
    def from_opts(opts: Options) -> FInput:
        if opts.input_file == "-":
            f = sys.stdin
        else:
            f = open(opts.input_file, "r")
        return FInput(opts.input_file, f.read())

    def advance_by(self, dist: int):
        """
        Move forward by dist characters in the input
        """
        assert dist >= 0
        self.line_no += self.content.count("\n", self.pos, self.pos + dist)
        self.pos += dist

    def move_to(self, new_pos: int):
        """
        Move forwards or backwards to a specific point
        """
        sign = 1 if new_pos > self.pos else -1
        lines = self.content.count("\n", min(new_pos, self.pos), max(new_pos, self.pos))
        print(
            f"moved {new_pos - self.pos} chars, {repr(self.content[min(new_pos, self.pos):max(new_pos, self.pos)])} ({lines} lines)"
        )
        self.line_no += sign * lines
        self.pos = new_pos

    def match(self, pattern: re.Pattern) -> re.Match | None:
        print(f"matching on {pattern}")
        return pattern.match(self.content, pos=self.pos)

    def find(self, pattern: re.Pattern) -> re.Match | None:
        print(f"searching for {pattern}")
        return pattern.search(self.content, pos=self.pos)

    def print_line_with_current_pos(self):
        last_newline_at = max(0, self.content.rfind("\n", 0, self.pos))
        next_newline_at = self.content.find("\n", self.pos)
        char_pos = self.pos - last_newline_at
        print(f"Matching at {self.fname}:{self.line_no}:{char_pos}")
        print(self.content[last_newline_at + 1 : next_newline_at])
        print(" " * (char_pos - 1), end="^\n")
