import re
from dataclasses import dataclass, field
from typing import Callable

from filecheck.finput import FInput, InputRange
from filecheck.ops import CheckOp, CountOp
from filecheck.options import Options
from filecheck.parser import Parser
from filecheck.compiler import compile_uops
from filecheck.error import CheckError, ParseError


@dataclass
class Context:
    """
    A context object, carrying life variables and such
    """

    live_variables: dict[str, str | int] = field(default_factory=dict)

    negative_matches_stack: list[CheckOp] = field(default_factory=list)
    """
    Keep a stack of CHECK-NOTs around, as we only know the range on which to match
    once we hit the next non-negative check-line.
    """

    negative_matches_start: int | None = field(default=None)


@dataclass
class Matcher:
    """
    The matcher contains the logic for applying the matching, recording variables and
    advancing the file position accordingly.
    """

    opts: Options
    file: FInput
    operations: Parser

    ctx: Context = field(default_factory=Context)

    @classmethod
    def from_opts(cls, opts: Options):
        """
        Construct a matcher form an options object.
        """
        ops = Parser.from_opts(opts)
        fin = FInput.from_opts(opts)
        return Matcher(opts, fin, ops)

    def __post_init__(self):
        self.ctx.live_variables.update(self.opts.variables)

    def run(self) -> int:
        """
        Run the matching, returns the exit code of the program.

        Prints a nice message when it fails.
        """
        function_table: dict[str, Callable[[CheckOp], None]] = {
            "DAG": self.check_dag,
            "COUNT": self.check_count,
            "NOT": self.enqueue_not,
            "EMPTY": self.check_empty,
            "NEXT": self.match_immediately,
            "SAME": self.match_eventually,
            "LABEL": self.check_label,
            "CHECK": self.match_eventually,
        }
        checks = 0
        op: CheckOp | None = None
        try:
            for op in self.operations:
                checks += 1
                self._pre_check(op)
                function_table.get(op.name, self.fail_op)(op)
                self._post_check(op)

            # run the post-check one last time to make sure all NOT checks are taken care of.
            self.file.range.start = len(self.file.content) - 1
            self._post_check(CheckOp("NOP", "", -1, []))
        except CheckError as ex:
            print(
                f"{self.opts.match_filename}:{self.operations.line_no}: error: {ex.message}"
            )
            self.file.print_line_with_current_pos()

            if ex.pattern:
                print(f"Trying to match with regex '{ex.pattern.pattern}'")
                if match := self.file.find(ex.pattern):
                    print("Possible match at:")
                    self.file.print_line_with_current_pos(match.start(0))

            return 1
        except ParseError as ex:
            print(f"{self.opts.match_filename}:{ex.line_no}:{ex.offset} {ex.message}")
            print(ex.offending_line.rstrip("\n"))
            print(" " * (ex.offset - 1) + "^")
            return 1

        if checks == 0:
            print(
                f"Error: No check strings found with prefix {self.opts.check_prefix}:"
            )
            return 2
        return 0

    def _pre_check(self, op: CheckOp):
        if self.file.is_discontigous() and op.name != "DAG":
            self.file.advance_to_last_hole()
        if op.name == "NEXT":
            self.file.skip_to_end_of_line()

    def _post_check(self, op: CheckOp):
        if op.name != "NOT":
            if self.ctx.negative_matches_start is not None:
                end = self.file.range.start
                # catch cases where the CHECK-NOT is followed by CHECK-DAG
                # in that case, go until the first "hole" in the region
                disc = self.file.is_discontigous()
                if disc:
                    end = disc.start_of_first_hole()
                # work through CHECK-NOT checks
                # this is the range we are searching in:
                search_range = InputRange(
                    self.ctx.negative_matches_start,
                    end,
                )
                # run through all statements
                for check in self.ctx.negative_matches_stack:
                    self.check_not(check, search_range)
                # reset the state
                self.ctx.negative_matches_start = None
                self.ctx.negative_matches_stack = []
        elif self.opts.match_full_lines:
            if not self.file.is_end_of_line():
                raise CheckError("Didn't match whole line")

    def check_dag(self, op: CheckOp) -> None:
        if not self.file.is_discontigous():
            self.file.start_discontigous_region()
        pattern, capture = compile_uops(op, self.ctx.live_variables, self.opts)
        match = self.file.match_and_add_hole(pattern)
        if match is None:
            raise CheckError(
                f"{self.opts.check_prefix}-DAG: Can't find match ('{op.arg}')"
            )
        self.capture_results(match, capture)

    def check_count(self, op: CheckOp) -> None:
        # invariant preserved by parser
        assert isinstance(op, CountOp)
        for _ in range(op.count):
            self.match_eventually(op)

    def check_not(self, op: CheckOp, search_range: InputRange):
        """
        Check that op doesn't match between start and current position.
        """
        pattern, _ = compile_uops(op, self.ctx.live_variables, self.opts)
        if self.file.find_between(pattern, search_range):
            raise CheckError(
                f"{self.opts.check_prefix}-NOT: excluded string found in input ('{op.arg}')"
            )

    def enqueue_not(self, op: CheckOp):
        """
        Enqueue a CHECK-NOT operation to be checked at a later time.

        Since CHECK-NOT matches between the last matched line, and the next matched
        line, we need to postpone matching until we know when the next checked line is.

        """
        if self.ctx.negative_matches_start is None:
            self.ctx.negative_matches_start = self.file.range.start
        self.ctx.negative_matches_stack.append(op)

    def check_label(self, op: CheckOp):
        """
        https://llvm.org/docs/CommandGuide/FileCheck.html#the-check-label-directive

        Looks for a uniquely identified line in the source file.

        CHECK-LABEL: directives cannot contain variable definitions or uses.
        """
        pattern, _ = compile_uops(op, self.ctx.live_variables, self.opts)
        # match in whole file
        matches = tuple(pattern.finditer(self.file.content))
        # check that we found exactly one match
        if not matches:
            raise CheckError(f'Couldn\'t match "{op.arg}".', pattern=pattern)
        if len(matches) != 1:
            raise CheckError(f"Non-unique {op.check_line_repr()} found")
        # move to match, if it's not already matched.
        (match,) = matches
        new_pos = match.end(0)
        if new_pos < self.file.range.start:
            raise CheckError("Label was already checked")

        self.file.move_to(new_pos)

        # remove non $ variables if option is set
        if self.opts.enable_var_scope:
            self.purge_variables()

    def check_empty(self, op: CheckOp):
        # check immediately
        if not self.opts.match_full_lines:
            self.file.skip_to_end_of_line()
        if not self.file.starts_with("\n\n"):
            raise CheckError(
                f"{self.opts.check_prefix}-EMPTY: is not on the line after the previous match"
            )
        # consume single newline
        self.file.advance_by(1)

    def match_immediately(self, op: CheckOp):
        """
        Check that the ops pattern is matched immediately.

        Uses file.match
        """
        pattern, repl = compile_uops(op, self.ctx.live_variables, self.opts)
        if match := self.file.match(pattern):
            self.file.move_to(match.end(0))
            self.capture_results(match, repl)
        else:
            raise CheckError(f'Couldn\'t match "{op.arg}".', pattern=pattern)

    def match_eventually(self, op: CheckOp):
        """
        Check that the ops pattern is matched eventually.

        Uses file.find
        """
        pattern, repl = compile_uops(op, self.ctx.live_variables, self.opts)
        if match := self.file.find(pattern, op.name == "SAME"):
            self.file.move_to(match.end())
            self.capture_results(match, repl)
        else:
            raise CheckError(f'Couldn\'t match "{op.arg}".', pattern=pattern)

    def fail_op(self, op: CheckOp):
        """
        Helper used for unknown operations. Should not occur as we check when parsing.
        """
        raise RuntimeError(f"Unknown operation: {op}")

    def purge_variables(self):
        """
        Purge variables not starting with '$'
        """
        for key in tuple(self.ctx.live_variables.keys()):
            if not key.startswith("$"):
                self.ctx.live_variables.pop(key)

    def capture_results(
        self,
        match: re.Match[str],
        capture: dict[str, tuple[int, Callable[[str], int] | Callable[[str], str]]],
    ):
        """
        Capture the results of a match into variables for string substitution
        """
        for name, (group, mapper) in capture.items():
            print(f"assigning variable {name} = {match.group(group)}")
            self.ctx.live_variables[name] = mapper(match.group(group))
