import re

from filecheck.ops import Literal, RE, Capture, NumSubst, Subst, UOp, CheckOp
from filecheck.options import Options

UNESCAPED_BRACKETS = re.compile(r"^\(|[^\\]\(")

CHECK_EMPTY_EXPR = re.compile(r"[^\n]*\n\n")


def compile_uops(
    check: CheckOp, variables: dict[str, str | int], opts: Options
) -> tuple[re.Pattern, dict[Capture, int]]:
    """
    Compile a series of uops, given a set of variables, to a regex pattern and an extraction dictionary
    """
    groups = 0
    expr: list[str] = []
    if check.name == "NEXT":
        expr.append(r"\n")
        if not opts.strict_whitespace:
            expr.append(r"( \t)*")
            groups += 1
    elif check.name == "SAME":
        expr.append("[^\n]*")
    elif check.name == "EMPTY":
        return CHECK_EMPTY_EXPR, dict()

    captures: dict[Capture, int] = dict()
    var_to_group: dict[str, int] = dict()

    for uop in check.uops:
        if isinstance(uop, Literal):
            expr.append(re.escape(uop.content))
        elif isinstance(uop, RE):
            # count number of capture groups
            groups += len(UNESCAPED_BRACKETS.findall(uop.content))
        elif isinstance(uop, Capture):

            captures[uop] = groups + 1
            var_to_group[uop.name] = groups + 1

            expr.append(f"({uop.pattern})")
        elif isinstance(uop, Subst):
            if uop.variable in var_to_group:
                expr.append(f"\\{var_to_group[uop.variable]}")
            else:
                if uop.variable not in variables:
                    raise RuntimeError(
                        f"Variable {uop.variable} referenced before assignment"
                    )
                expr.append(re.escape(str(variables[uop.variable])))
        elif isinstance(uop, NumSubst):
            raise NotImplementedError("Numerical substitutions not supported!")

    return re.compile("".join(expr)), captures
