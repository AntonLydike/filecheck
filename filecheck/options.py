from dataclasses import dataclass
from typing import Iterable


@dataclass
class Options:
    match_filename: str
    input_file: str = "-"
    check_prefix: str = "CHECK"
    strict_whitespace: bool = False
    enable_var_scope: bool = False
    comment_prefixes: list[str] = "COM,RUN"  # type: ignore[reportAssignmentType]

    def __post_init__(self):
        # make sure we split the comment prefixes
        if isinstance(self.comment_prefixes, str):
            self.comment_prefixes = self.comment_prefixes.split(",")


def parse_argv_options(argv: list[str]) -> Options:
    # pop the name off of argv
    _ = argv.pop(0)

    # final options to return
    opts = {}
    # args that were consumed
    remove: list[int] = []
    argv = list(normalise_args(argv))

    for i, arg in enumerate(argv):
        if arg.startswith("--"):
            arg = arg[2:].replace("-", "_")
        elif arg.startswith("-"):
            arg = arg[1:].replace("-", "_")
        else:
            continue
        if arg not in Options.__dataclass_fields__:
            continue

        remove.append(i)
        if Options.__dataclass_fields__[arg].type == bool:
            opts[arg] = True
        else:
            if i == len(argv) - 1:
                raise RuntimeError("Out of range arguments")
            opts[arg] = argv[i + 1]
            remove.append(i + 1)

    for idx in sorted(remove, reverse=True):
        argv.pop(idx)

    if len(argv) > 1:
        raise RuntimeError(
            f"Unconsumed arguments: {argv}, expected one remaining arg, the match-filename."
        )

    opts["match_filename"] = argv[0]

    return Options(**opts)  # pyright: ignore[reportUnknownArgumentType]


def normalise_args(argv: list[str]) -> Iterable[str]:
    """
    Normalize arguments by splitting "--key=value" pairs into separate "--key" and
    "value" entries.
    """
    for arg in argv:
        if arg.startswith("-") and "=" in arg:
            yield from arg.split("=", 1)
        else:
            yield arg
