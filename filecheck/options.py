from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Options:
    match_filename: str
    input_file: str = "-"
    check_prefix: str = "CHECK"
    strict_whitespace: bool = False
    enable_var_scope: bool = False
    match_full_lines: bool = False
    comment_prefixes: list[str] = "COM,RUN"  # type: ignore[reportAssignmentType]
    variables: dict[str, str | int] = field(default_factory=dict)

    def __post_init__(self):
        # make sure we split the comment prefixes
        if isinstance(self.comment_prefixes, str):
            self.comment_prefixes = self.comment_prefixes.split(",")


def parse_argv_options(argv: list[str]) -> Options:
    # pop the name off of argv
    _ = argv.pop(0)

    # final options to return
    opts: dict[str, str | bool] = {}
    variables: dict[str, str | int] = {}
    # args that were consumed
    remove: set[int] = set()
    argv = list(normalise_args(argv))

    for i, arg in enumerate(argv):
        # skip consumed args
        if i in remove:
            continue
        if arg.startswith("-D"):
            if i == len(argv) - 1:
                raise RuntimeError("Out of range arguments")
            key, val = arg[2:], argv[i + 1]
            variables[key] = val
            remove.update((i, i + 1))
        elif arg.startswith("--"):
            arg = arg[2:].replace("-", "_")
        elif arg.startswith("-"):
            arg = arg[1:].replace("-", "_")
        else:
            continue
        if arg not in Options.__dataclass_fields__:
            continue

        remove.add(i)
        if Options.__dataclass_fields__[arg].type == bool:
            opts[arg] = True
        else:
            if i == len(argv) - 1:
                raise RuntimeError("Out of range arguments")
            opts[arg] = argv[i + 1]
            remove.add(i + 1)

    for idx in sorted(remove, reverse=True):
        argv.pop(idx)

    if len(argv) > 1:
        raise RuntimeError(
            f"Unconsumed arguments: {argv}, expected one remaining arg, the match-filename."
        )

    opts["match_filename"] = argv[0]

    return Options(
        **opts,  # pyright: ignore[reportArgumentType]
        variables=variables,
    )


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
