import sys

from filecheck.help import HELP_TEXT
from filecheck.matcher import Matcher
from filecheck.options import parse_argv_options


def main(argv: list[str] | None = None):
    if argv is None:
        argv = sys.argv

    if "--help" in argv or len(argv) < 2:
        print(HELP_TEXT)
        return

    opts = parse_argv_options(argv)
    m = Matcher.from_opts(opts)
    sys.exit(m.run())
