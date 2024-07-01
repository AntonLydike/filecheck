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

    _in_dag: bool = field(default=False)

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
            "NOT": self.check_not,
            "EMPTY": self.check_empty,
            "NEXT": self.match_immediately,
            "SAME": self.match_immediately,
            "LABEL": self.match_eventually,
            "CHECK": self.match_eventually,
        }

        for op in self.operations:
            try:
                function_table.get(op.name, self.fail_op)(op)
            except CheckError as ex:
                print(f"Error matching: {ex}")
                op.print_source_repr(self.opts)
                self.file.print_line_with_current_pos()
                return 1
        return 0

    def check_dag(self, op: CheckOp):
        raise NotImplementedError()

    def check_count(self, op: CheckOp):
        raise NotImplementedError()

    def check_not(self, op: CheckOp):
        pattern, repl = compile_uops(op, self.ctx.live_variables, self.opts)
        if match := self.file.match(pattern):
            raise CheckError(f"Matched {op.check_line_repr()}")

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
            raise CheckError(f"Couldn't match {op.arg}.")

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
            raise CheckError(f"Couldn't match {op.arg}.")

    def check_label(self, op: CheckOp):
        raise NotImplementedError()

    def fail_op(self, op: CheckOp):
        """
        Helper used for unknown operations. Should not occur as we check when parsing.
        """
        raise RuntimeError(f"Unknown operation: {op}")
