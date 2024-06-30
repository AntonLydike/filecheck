from dataclasses import dataclass


@dataclass
class Options:
    match_filename: str
    input_file: str = "-"
    check_prefix: str = "CHECK"
    strict_whitespace: bool = False
    comment_prefixes: list[str] = "COM,RUN"

    def __post_init__(self):
        # make sure we split the comment prefixes
        if isinstance(self.comment_prefixes, str):
            self.comment_prefixes = self.comment_prefixes.split(",")


def parse_argv_options(argv: list[str]) -> Options:
    name = argv.pop(0)

    # final options to return
    opts = {}
    # map args to their position in the argv array
    args: dict[str, int] = {}
    # args that were consumed
    remove: list[int] = []
    for i, arg in enumerate(argv):
        if arg.startswith("--"):
            args[arg[2:].replace("-", "_")] = i
        elif arg.startswith("-"):
            args[arg[1:].replace("-", "_")] = i

    for field in Options.__dataclass_fields__.values():
        name: str = field.name
        if name in args:
            # if boolean field
            remove.append(args[name])
            if field.type == bool:
                opts[name] = True
            else:
                remove.append(args[name] + 1)
                opts[name] = argv[args[name] + 1]

    for idx in sorted(remove, reverse=True):
        argv.pop(idx)

    if len(argv) > 1:
        raise RuntimeError(
            f"Unconsumed arguments: {argv}, expected one remaining arg, the match-filename."
        )

    opts["match_filename"] = argv[0]

    return Options(**opts)
