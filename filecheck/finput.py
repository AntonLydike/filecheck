"""
Manages the file input and the position we are at
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

from filecheck.options import Options


@dataclass
class FInput:
    """
    A wrapper around file input.

    Handles position keeping and regex searching.
    """

    fname: str
    content: str
    pos: int = field(default=0)

    line_no: int = field(default=0)

    @staticmethod
    def from_opts(opts: Options) -> FInput:
        """
        Create a FInput object from options objects
        """
        # treat - as stding
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

    def match(self, pattern: re.Pattern[str]) -> re.Match[str] | None:
        """
        Match (exactly from the current position)
        """
        print(f"matching on r'{pattern.pattern}'")
        return pattern.match(self.content, pos=self.pos)

    def find(
        self, pattern: re.Pattern[str], this_line: bool = False
    ) -> re.Match[str] | None:
        """
        Find the first occurance of a pattern, might be far away.

        If this_line is given, match only until the next newline.
        """
        print(f"searching for r'{pattern.pattern}'")
        endpos = self.content.find("\n", self.pos) if this_line else -1
        if endpos == -1:
            endpos = sys.maxsize
        return pattern.search(self.content, pos=self.pos, endpos=endpos)

    def find_between(
        self, pattern: re.Pattern[str], start: int, end: int
    ) -> re.Match[str] | None:
        """
        Find the first occurance of a pattern, might be far away.
        """
        print(f"searching for r'{pattern.pattern}' in input[{start}:{end}]")
        return pattern.search(self.content, pos=start, endpos=end)

    def print_line_with_current_pos(self, pos_override: int | None = None):
        """
        Print the current position in the input file.
        """
        fname = self.fname if self.fname != "-" else "stdin"
        pos = self.pos if pos_override is None else pos_override
        next_newline_at = self.content.find("\n", pos)

        # print the next line if we are pointing at a line end.
        if next_newline_at == pos:
            pos += 1
            next_newline_at = self.content.find("\n", pos)

        last_newline_at = self.start_of_line(pos)
        char_pos = pos - last_newline_at
        print(f"Matching at {fname}:{self.line_no}:{char_pos}")
        print(self.content[last_newline_at + 1 : next_newline_at])
        print(" " * (char_pos - 1), end="^\n")

    def start_of_line(self, pos: int | None = None) -> int:
        """
        Find the start of the line at position pos (defaults to current position)
        """
        if pos is None:
            pos = self.pos
        return max(self.content.rfind("\n", 0, pos), 0)

    def skip_to_end_of_line(self):
        """
        Move to the next \n token (might be at cursor already, then it's a nop)
        """
        if self.pos == 0:
            return
        next_newline = self.content.find("\n", self.pos)
        self.move_to(next_newline)

    def is_end_of_line(self) -> bool:
        """
        Check if line ending or EOF has been reached
        """
        # line ending check
        if self.content.startswith("\n", self.pos):
            return True
        # eof check
        if self.pos == len(self.content) - 1:
            return True
        return False
