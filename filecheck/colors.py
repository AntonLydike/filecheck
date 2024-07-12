import sys
from enum import Flag, auto

COLOR_SUPPORT = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class FMT(Flag):
    RED = auto()
    BLUE = auto()
    YELLOW = auto()
    GREEN = auto()
    ORANGE = auto()
    BOLD = auto()
    GRAY = auto()
    UNDERLINE = auto()
    RESET = auto()

    def __str__(self) -> str:
        if not COLOR_SUPPORT:
            return ""
        fmt_str: list[str] = []
        for f in self:
            match f:
                case FMT.RED:
                    fmt_str.append("\033[31m")
                case FMT.ORANGE:
                    fmt_str.append("\033[33m")
                case FMT.GRAY:
                    fmt_str.append("\033[37m")
                case FMT.GREEN:
                    fmt_str.append("\033[32m")
                case FMT.BLUE:
                    fmt_str.append("\033[34m")
                case FMT.YELLOW:
                    fmt_str.append("\033[93m")
                case FMT.BOLD:
                    fmt_str.append("\033[1m")
                case FMT.RESET:
                    fmt_str.append("\033[0m")
                case FMT.UNDERLINE:
                    fmt_str.append("\033[4m")
                case _:
                    raise ValueError(f"Unknown color {f}")
        return "".join(fmt_str)


WARN = FMT.ORANGE | FMT.UNDERLINE
ERR = FMT.RED | FMT.BOLD
