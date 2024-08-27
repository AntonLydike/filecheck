import re
from typing import TypeAlias

from filecheck.error import CheckError
from filecheck.ops import Literal, RE, Capture, NumSubst, Subst, CheckOp, VALUE_MAPPER_T
from filecheck.options import Options
from filecheck.regex import LiteralMatcher, LiteralMatch

UNESCAPED_BRACKETS = re.compile(r"^\(|[^\\]\(")

CHECK_EMPTY_EXPR = re.compile(r"[^\n]*\n\n")

PatternT: TypeAlias = re.Pattern[str] | LiteralMatcher
MatchT: TypeAlias = re.Match[str] | LiteralMatch


def compile_uops(
    check: CheckOp, variables: dict[str, str | int], opts: Options
) -> tuple[PatternT, dict[str, tuple[int, VALUE_MAPPER_T]]]:
    """
    Compile a series of uops, given a set of variables, to a regex pattern and an
    extraction dictionary.

    The extraction dictionary tells you which Capture can be found in which regex
    group.
    """
    groups = 0
    expr: list[str] = []
    if check.name == "NEXT":
        expr.append(r"\n?[^\n]*")
    elif check.name == "EMPTY":
        return CHECK_EMPTY_EXPR, dict()

    captures: dict[str, tuple[int, VALUE_MAPPER_T]] = dict()

    # see if this can be reduced to a simple literal match, which means that we don't need to compile a regex at all
    if can_be_constant_folded(check, variables):
        # grab all the literal parts of the pattern (which are the entire pattern)
        literal = "".join(uop.get_literal(variables) for uop in check.uops)
        return (
            LiteralMatcher(literal, opts.strict_whitespace, check.name == "NEXT"),
            captures,
        )

    for uop in check.uops:
        if isinstance(uop, Literal):
            # literals are matched as is
            if opts.strict_whitespace:
                expr.append(re.escape(uop.content))
            else:
                # TODO: fix this mess
                # basically, I need to replace all whitespaces in the original literal by "\s+"
                # but I still want to regex escape them
                # and re.sub doesn't let me insert \s into the new string for some reason......
                expr.append(
                    re.sub(r"(\\ )+", " ", re.escape(uop.content)).replace(" ", r"\s+")
                )
        elif isinstance(uop, RE):
            # For regexes, we must make sure that we count the number of capture groups
            # present, so that we know which ones contain the Captures, and which ones
            # contain "user supplied" groups.

            # count number of capture groups by counting unescaped brackets
            groups += len(UNESCAPED_BRACKETS.findall(uop.content))
            # add brackets sorrounding patterns that contain ORs (fixes #3)
            if "|" in uop.content:
                expr.append(f"({uop.content})")
                groups += 1
            else:
                expr.append(uop.content)
        elif isinstance(uop, Capture):
            # record the group we capture in the dictionary
            captures[uop.name] = (groups + 1, uop.value_mapper)
            # this is used to match same-line use of variables
            # like this:
            # // CHECK: alloc [[REG:[a-z]+]], [[REG]]
            # here we can't insert the value now, as it will only be determined when we
            # match the pattern. Luckily, python regex has backwards references.
            expr.append(f"({uop.pattern})")
            groups += len(UNESCAPED_BRACKETS.findall(uop.pattern)) + 1
        elif isinstance(uop, Subst):
            # if we have substitutions, check if the variable is defined in this line
            if uop.variable in captures:
                expr.append(f"\\{captures[uop.variable][0]}")
            else:
                # otherwise match immediate
                if uop.variable not in variables:
                    raise CheckError(
                        f"Variable {uop.variable} referenced before assignment",
                        check,
                    )
                expr.append(re.escape(str(variables[uop.variable])))
        elif isinstance(uop, NumSubst):
            # we don't do numerical substitutions yet
            raise NotImplementedError("Numerical substitutions not supported!")

    try:
        # compile with MULTILINE flag, so that `^` and `$` can match start/end of line correctly
        return re.compile("".join(expr), flags=re.MULTILINE), captures
    except re.error:
        raise CheckError(f"Malformed regex expression: '{''.join(expr)}'", check)


def can_be_constant_folded(check: CheckOp, vars: dict[str, str | int]) -> bool:
    """
    Checks to see if a CheckOp is only composed of constant expressible parts, so only
    string literals and pattern substitutions are allowed.

    Note that all pattern substitutions must by definition not be from captures on the same line,
    as no capture ops are allowed.
    """
    for op in check.uops:
        if isinstance(op, (RE, Capture, NumSubst)):
            return False
        if isinstance(op, Subst) and op.variable not in vars:
            return False
    return True
