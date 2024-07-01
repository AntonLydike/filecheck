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
        checks = 0
        for op in self.operations:
            try:
                checks += 1
                function_table.get(op.name, self.fail_op)(op)
            except CheckError as ex:
                print(f"Error matching: {ex}")
                op.print_source_repr(self.opts)
                self.file.print_line_with_current_pos()
                return 1
        if checks == 0:
            print(f"Error: No check strings found with prefix {self.opts.check_prefix}:")
            return 2
        return 0

    def check_dag(self, op: CheckOp):
        raise NotImplementedError()

    def check_count(self, op: CheckOp):
        raise NotImplementedError()

    def check_not(self, op: CheckOp):
        pattern, repl = compile_uops(op, self.ctx.live_variables, self.opts)
        if self.file.match(pattern) is not None:
            raise CheckError(f"Matched {op.check_line_repr()}")

    def check_label(self, op: CheckOp):
        """
        https://llvm.org/docs/CommandGuide/FileCheck.html#the-check-label-directive

        Looks for a uniquely identified line in the source file.

        CHECK-LABEL: directives cannot contain variable definitions or uses.
        """
        pattern, repl = compile_uops(op, self.ctx.live_variables, self.opts)
        # match in whole file
        matches = pattern.findall(self.file.content)
        # check that we found exactly one match
        if not matches:
            raise CheckError(f'Couldn\'t match "{op.arg}".')
        if len(matches) > 1:
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
            raise CheckError(f'Couldn\'t match "{op.arg}".')

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
            raise CheckError(f'Couldn\'t match "{op.arg}".')

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
