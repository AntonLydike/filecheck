"""
Manages the file input and the position we are at
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Iterable

from filecheck.options import Options


@dataclass(slots=True)
class InputRange:
    start: int
    end: int

    def ranges(self) -> Iterable[tuple[int, int]]:
        yield (self.start, self.end)

    def restrict_end(self, new_end: int):
        return InputRange(self.start, new_end)


@dataclass(slots=True)
class DiscontigousRange(InputRange):
    """
    A range with holes in it.
    """

    _holes: list[InputRange] = field(default_factory=list, init=False, repr=False)
    """
    This will only ever contain InputRange, never DiscontigousRange.

    These holes are non-overlapping and sorted in ascending start positions.
    """

    def ranges(self) -> Iterable[tuple[int, int]]:
        start = self.start
        for hole in self._holes:
            if start < hole.start:
                yield start, hole.start
            start = hole.end
        if start < self.end:
            yield start, self.end

    def add_hole(self, range: InputRange | DiscontigousRange):
        may_have_overlap = False
        for start, end in range.ranges():
            for i, hole in enumerate(self._holes):
                # check if they are disjunct:
                if end < hole.start:
                    # if it comes before, insert it
                    self._holes.insert(i, InputRange(start, end))
                    break
                if hole.end < start:
                    # if it comes later, continue
                    continue
                # we must have overlap, widen the hole!
                hole.start = min(start, hole.start)
                hole.end = max(end, hole.end)
                may_have_overlap = True
                break
            else:
                # append to the end otherwise
                self._holes.append(InputRange(start, end))
        if may_have_overlap:
            # if we widened a hole, we need to check for overlap:
            remove: list[InputRange] = list()
            # iterate over pairs
            for h1, h2 in zip(self._holes, self._holes[1:]):
                # if we find overlap:
                if h1.end >= h2.start:
                    # widen the *second* hole
                    h2.start = h1.start
                    h2.end = max(h1.end, h2.end)
                    # remove the first one
                    remove.append(h1)
            for r in remove:
                self._holes.remove(r)

    def end_of_last_hole(self) -> int:
        if self._holes:
            return max(self._holes[-1].end, self.start)
        return self.start

    def start_of_first_hole(self) -> int:
        if self._holes:
            return min(self._holes[0].start, self.end)
        return self.end

    def remainder_to_normal_range(self) -> InputRange:
        return InputRange(self.end_of_last_hole(), self.end)


@dataclass
class FInput:
    """
    A wrapper around file input.

    Handles position keeping and regex searching.
    """

    fname: str
    content: str

    line_no: int = field(default=0)

    range: InputRange = field(default_factory=lambda: InputRange(0, sys.maxsize))
    ranges: list[InputRange] = field(default_factory=list)

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
        self.line_no += self.content.count(
            "\n", self.range.start, self.range.start + dist
        )
        self.range.start += dist
        if self.range.end < self.range.start:
            raise RuntimeError("Ran out of range!")

    def move_to(self, new_pos: int):
        """
        Move forwards to a specific point
        """
        self.advance_by(new_pos - self.range.start)

    def match(self, pattern: re.Pattern[str]) -> re.Match[str] | None:
        """
        Match (exactly from the current position)
        """
        return pattern.match(self.content, pos=self.range.start, endpos=self.range.end)

    def find(
        self,
        pattern: re.Pattern[str],
        this_line: bool = False,
    ) -> re.Match[str] | None:
        """
        Find the first occurance of a pattern, might be far away.

        If this_line is given, match only until the next newline.
        """
        irange = self.range

        newline = (
            self.content.find("\n", irange.start, irange.end)
            if this_line
            else irange.end
        )
        if newline != -1:
            irange = irange.restrict_end(newline)

        return pattern.search(self.content, pos=irange.start, endpos=irange.end)

    def find_between(
        self, pattern: re.Pattern[str], irange: InputRange
    ) -> re.Match[str] | None:
        """
        Find the first occurance of a pattern, might be far away.
        """
        for start, end in irange.ranges():
            match = pattern.search(self.content, pos=start, endpos=end)
            if match is not None:
                return match

    def print_line_with_current_pos(self, pos_override: int | None = None):
        """
        Print the current position in the input file.
        """
        fname = self.fname if self.fname != "-" else "stdin"
        pos = self.range.start if pos_override is None else pos_override
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
            pos = self.range.start
        return max(self.content.rfind("\n", 0, pos), 0)

    def skip_to_end_of_line(self):
        """
        Move to the next \n token (might be at cursor already, then it's a nop)
        """
        if self.range.start == 0:
            return
        next_newline = self.content.find("\n", self.range.start)
        self.move_to(next_newline)

    def is_end_of_line(self) -> bool:
        """
        Check if line ending or EOF has been reached
        """
        # line ending check
        if self.content.startswith("\n", self.range.start):
            return True
        # eof check
        if self.range.start == len(self.content) - 1:
            return True
        return False

    def starts_with(self, expr: str) -> bool:
        return self.content.startswith(expr, self.range.start)

    def print_range(self, frange: InputRange):
        print(f"{self.fname}: ({frange.start} to {frange.end})")
        print(self.content[frange.start : frange.end])

    def start_discontigous_region(self):
        """
        Starts a discontigous matching region, replacing the current range with a
        discontigous one.
        """
        assert not isinstance(self.range, DiscontigousRange)
        self.range = DiscontigousRange(self.range.start, self.range.end)

    def match_and_add_hole(self, pattern: re.Pattern[str]) -> re.Match[str] | None:
        """
        Find the first occurance of a pattern in a discontigous range.

        Adds the matched region as a hole to the range.

        Can only be called *after* start_discontigous_region
        """
        assert isinstance(self.range, DiscontigousRange)
        match = self.find_between(pattern, self.range)
        if match is not None:
            self.range.add_hole(InputRange(match.start(0), match.end(0)))
        return match

    def advance_to_last_hole(self):
        """
        Advance to end of the last hole in the discontigous region
        """
        assert isinstance(self.range, DiscontigousRange)
        print(f"moving to {self.range.end_of_last_hole()} of {self.range}")
        new_range = self.range.remainder_to_normal_range()
        self.move_to(new_range.start)
        self.range = new_range

    def is_discontigous(self) -> DiscontigousRange | None:
        if isinstance(self.range, DiscontigousRange):
            return self.range
