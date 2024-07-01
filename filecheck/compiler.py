import re

from filecheck.ops import Literal, RE, Capture, NumSubst, Subst, CheckOp
from filecheck.options import Options

UNESCAPED_BRACKETS = re.compile(r"^\(|[^\\]\(")

CHECK_EMPTY_EXPR = re.compile(r"[^\n]*\n\n")


def compile_uops(
    check: CheckOp, variables: dict[str, str | int], opts: Options
) -> tuple[re.Pattern, dict[Capture, int]]:
    """
    Compile a series of uops, given a set of variables, to a regex pattern and an
    extraction dictionary.

    The extraction dictionary tells you which Capture can be found in which regex
    group.
    """
    groups = 0
    expr: list[str] = []
    if check.name == "NEXT":
        expr.append(r"\n[^\n]*")
    elif check.name == "SAME":
        expr.append("[^\n]*")
    elif check.name == "EMPTY":
        return CHECK_EMPTY_EXPR, dict()

    captures: dict[Capture, int] = dict()
    var_to_group: dict[str, int] = dict()

    for uop in check.uops:
        if isinstance(uop, Literal):
            # literals are matched as is
            expr.append(re.escape(uop.content))
        elif isinstance(uop, RE):
            # For regexes, we must make sure that we count the number of capture groups
            # present, so that we know which ones contain the Captures, and which ones
            # contain "user supplied" groups.

            # count number of capture groups by counting unescaped brackets
            groups += len(UNESCAPED_BRACKETS.findall(uop.content))
            expr.append(uop.content)
        elif isinstance(uop, Capture):
            # record the group we capture in the dictionary
            captures[uop] = groups + 1
            # this is used to match same-line use of variables
            # like this:
            # // CHECK: alloc [[REG:[a-z]+]], [[REG]]
            # here we can't insert the value now, as it will only be determined when we
            # match the pattern. Luckily, python regex has backwards references.
            var_to_group[uop.name] = groups + 1
            expr.append(f"({uop.pattern})")
        elif isinstance(uop, Subst):
            # if we have substitutions, check if the variable is defined in this line
            if uop.variable in var_to_group:
                expr.append(f"\\{var_to_group[uop.variable]}")
            else:
                # otherwise match immediate
                if uop.variable not in variables:
                    raise RuntimeError(
                        f"Variable {uop.variable} referenced before assignment"
                    )
                expr.append(re.escape(str(variables[uop.variable])))
        elif isinstance(uop, NumSubst):
            # we don't do numerical substitutions yet
            raise NotImplementedError("Numerical substitutions not supported!")

    # make sure CHECK-LABEL consumes entire line
    if check.name == "LABEL":
        expr.append(r"[^\n]*")

    return re.compile("".join(expr)), captures
