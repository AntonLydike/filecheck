from dataclasses import dataclass


@dataclass
class Options:
    match_filename: str
    input_file: str = "-"
    check_prefix: str = "CHECK"
    strict_whitespace: bool = False
    enable_var_scope: bool = False
    comment_prefixes: list[str] = "COM,RUN"

    def __post_init__(self):
        # make sure we split the comment prefixes
        if isinstance(self.comment_prefixes, str):
            self.comment_prefixes = self.comment_prefixes.split(",")


def parse_argv_options(argv: list[str]) -> Options:
    name = argv.pop(0)

    # final options to return
    opts = {}
    # args that were consumed
    remove: list[int] = []

    for i, arg in enumerate(argv):
        remainder = None
        split = False
        if '=' in arg:
            split = True
            arg, remainder = arg.split("=", 1)
        elif len(argv) > i+1:
            remainder = argv[i+1]

        if arg.startswith("--"):
            arg = arg[2:].replace("-", "_")
        elif arg.startswith("-"):
            arg = arg[1:].replace("-", "_")
        else:
            continue
        if arg not in Options.__dataclass_fields__:
            continue

        remove.append(i)
        if remainder is not None and not split:
            remove.append(i+1)
        if Options.__dataclass_fields__[arg].type == bool:
            opts[arg] = True
        else:
            if remainder is None:
                raise RuntimeError("Out of range arguments")
            opts[arg] = remainder


    for idx in sorted(remove, reverse=True):
        argv.pop(idx)

    if len(argv) > 1:
        raise RuntimeError(
            f"Unconsumed arguments: {argv}, expected one remaining arg, the match-filename."
        )

    opts["match_filename"] = argv[0]

    return Options(**opts)
