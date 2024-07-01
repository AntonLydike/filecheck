import re
from dataclasses import dataclass, field
from typing import Iterator, Callable

from filecheck.finput import FInput
from filecheck.ops import CheckOp
from filecheck.options import Options
from filecheck.parser import Parser
from filecheck.compiler import compile_uops
from filecheck.error import CheckError


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
    operations: Iterator[CheckOp]

    ctx: Context = field(default_factory=Context)

    @classmethod
    def from_opts(cls, opts: Options):
        """
        Construct a matcher form an options object.
        """
        ops = Parser.from_opts(opts)
        fin = FInput.from_opts(opts)
        return Matcher(opts, fin, ops)

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
            "SAME": self.match_immediately,
            "LABEL": self.check_label,
            "CHECK": self.match_eventually,
        }
        checks = 0
        for op in self.operations:
            try:
                checks += 1
                self._pre_check(op)
                function_table.get(op.name, self.fail_op)(op)
                self._post_check(op)
            except CheckError as ex:
                print(f"Error matching: {ex.message}")
                op.print_source_repr(self.opts)
                self.file.print_line_with_current_pos()

                if ex.pattern:
                    if match := self.file.find(ex.pattern):
                        print("Possible match at:")
                        self.file.print_line_with_current_pos(match.start(0))

                return 1

        # run the post-check one last time to make sure all NOT checks are taken care of.
        self._post_check(CheckOp("NOP", "", -1, []))
        if checks == 0:
            print(
                f"Error: No check strings found with prefix {self.opts.check_prefix}:"
            )
            return 2
        return 0

    def _pre_check(self, op: CheckOp):
        if op.name == "NEXT":
            self.file.skip_to_end_of_line()

    def _post_check(self, op: CheckOp):
        if op.name != "NOT":
            # work through CHECK-NOT checks
            for check in self.ctx.negative_matches_stack:
                self.check_not(check, self.ctx.negative_matches_start)
            # reset the state
            if self.ctx.negative_matches_stack:
                self.ctx.negative_matches_start = None
                self.ctx.negative_matches_stack = []

    def check_dag(self, op: CheckOp):
        raise NotImplementedError()

    def check_count(self, op: CheckOp):
        raise NotImplementedError()

    def check_not(self, op: CheckOp, start: int | None):
        """
        Check that op doesn't match between start and current position.
        """
        pattern, _ = compile_uops(op, self.ctx.live_variables, self.opts)
        if start is None:
            start = 0
        start = min(start, self.file.start_of_line())
        end = max(start, self.file.start_of_line())
        if self.file.find_between(pattern, start, end):
            raise CheckError(f"Matched {op.check_line_repr()}")

    def enqueue_not(self, op: CheckOp):
        """
        Enqueue a CHECK-NOT operation to be checked at a later time.

        Since CHECK-NOT matches between the last matched line, and the next matched
        line, we need to postpone matching until we know when the next checked line is.

        """
        if self.ctx.negative_matches_start is None:
            self.ctx.negative_matches_start = self.file.pos
        self.ctx.negative_matches_stack.append(op)

    def check_label(self, op: CheckOp):
        """
        https://llvm.org/docs/CommandGuide/FileCheck.html#the-check-label-directive

        Looks for a uniquely identified line in the source file.

        CHECK-LABEL: directives cannot contain variable definitions or uses.
        """
        pattern, repl = compile_uops(op, self.ctx.live_variables, self.opts)
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
        if new_pos < self.file.pos:
            raise CheckError("Label was already checked")

        self.file.move_to(new_pos)

        # remove non $ variables if option is set
        if self.opts.enable_var_scope:
            self.purge_variables()

    def check_empty(self, op: CheckOp):
        # check immediately
        self.match_immediately(op)
        # roll back the last newline, so that we are located at the end of the last line
        # instead of at the start of the next line. This is important for CHECK-NEXT
        # and friends
        self.file.move_to(self.file.pos - 1)

    def match_immediately(self, op: CheckOp):
        """
        Check that the ops pattern is matched immediately.

        Uses file.match
        """
        pattern, repl = compile_uops(op, self.ctx.live_variables, self.opts)
        if match := self.file.match(pattern):
            print(
                f"matched: {op.check_line_repr()}, groups={match.groups()} mapping to {repl}"
            )

            self.file.move_to(match.end(0))

            for var, group in repl.items():
                print(
                    f"assigning variable {var.name} from group {group} value {match.group(group)} "
                )
                self.ctx.live_variables[var.name] = var.value_mapper(match.group(group))
        else:
            raise CheckError(f'Couldn\'t match "{op.arg}".', pattern=pattern)

    def match_eventually(self, op: CheckOp):
        """
        Check that the ops pattern is matched eventually.

        Uses file.find
        """
        pattern, repl = compile_uops(op, self.ctx.live_variables, self.opts)
        if match := self.file.find(pattern):
            print(
                f"matched: {op.check_line_repr()}, groups={match.groups()} mapping to {repl}"
            )

            self.file.move_to(match.end())

            for var, group in repl.items():
                print(
                    f"assigning variable {var.name} from group {group} value {match.group(group)} "
                )
                self.ctx.live_variables[var.name] = var.value_mapper(match.group(group))

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
