from __future__ import annotations

"""Internal representation of FileCheck operations ("opcodes").

This module needs to run on Python versions < 3.10.  The implementation was
originally written for Python 3.10+ and makes use of the ``kw_only`` keyword
argument that became available for ``dataclasses.field`` starting with Python
3.10.  When executed under Python 3.9 this argument is unknown and therefore
raises a ``TypeError`` at *import time* – long before any of the library's
public API can be used.

To keep the codebase compatible with Python 3.9 we intercept calls to
``dataclasses.field`` and strip the unsupported ``kw_only`` parameter when the
interpreter version is < 3.10.  This is a narrow and targeted shim so that the
rest of the source code can stay unchanged and continue to declare
keyword-only fields in a forward-compatible way for newer Python versions.
"""

from dataclasses import dataclass, field as _dataclass_field
import sys

# ---------------------------------------------------------------------------
# Compatibility shim for *kw_only* support on Python < 3.10
# ---------------------------------------------------------------------------

if sys.version_info < (3, 10):
    # ``dataclasses.field`` does not accept *kw_only* prior to 3.10.  Provide a
    # tiny wrapper that silently discards this keyword so that later uses like
    # ``field(kw_only=True)`` keep working when running on 3.9.

    def field(*args, **kwargs):  # type: ignore[override]
        """Drop the *kw_only* argument when unsupported (Python < 3.10)."""

        kwargs.pop("kw_only", None)
        return _dataclass_field(*args, **kwargs)

else:
    # On Python 3.10+ the real ``dataclasses.field`` already supports *kw_only*.
    from dataclasses import field  # type: ignore  # re-export for mypy

from typing import Callable, Union

from filecheck.options import Options

OP_KINDS = ("DAG", "COUNT", "NOT", "EMPTY", "NEXT", "SAME", "LABEL", "CHECK")

VALUE_MAPPER_T = Union[Callable[[str], int], Callable[[str], str]]


@dataclass(slots=True)
class CheckOp:
    """
    Represents a concrete check instruction (e.g. CHECK-NEXT)
    """

    prefix: str
    name: str
    arg: str
    source_line: int
    uops: list[UOp]
    is_literal: bool = field(default=False, kw_only=True)

    def check_line_repr(self):
        return f"{self.check_name}: {self.arg}"

    def source_repr(self, opts: Options) -> str:
        return (
            f"Check rule at {opts.match_filename}:{self.source_line}\n"
            f"{self.check_line_repr()}"
        )

    def _suffix(self):
        suffix = "{LITERAL}" if self.is_literal else ""
        if self.name == "CHECK":
            return suffix
        return f"-{self.name}{suffix}"

    @property
    def check_name(self):
        return f"{self.prefix}{self._suffix()}"


@dataclass(slots=True)
class CountOp(CheckOp):
    """
    special case for COUNT-<number>
    """

    # NOTE: ``kw_only`` is not supported prior to Python 3.10.  To keep the
    # original public API we still accept ``count=`` as a keyword argument in
    # all Python versions but, on 3.9, we also provide a *fallback* default so
    # that the field does not violate the dataclass rule that *non-default*
    # fields must not follow fields with a default from a base class.  The
    # parser always passes an explicit value, therefore the default should
    # never be observed at runtime.

    count: int = field(default=0)

    def _suffix(self):
        suffix = "{LITERAL}" if self.is_literal else ""
        return f"-COUNT{self.count}{suffix}"


@dataclass(frozen=True, slots=True)
class UOp:
    """
    micro-ops, thse make up the filecheck matching logic
    """

    pass


@dataclass(frozen=True, slots=True)
class Literal(UOp):
    """
    literal match
    """

    content: str


@dataclass(frozen=True, slots=True)
class RE(UOp):
    """
    Regular expression matching
    """

    content: str


@dataclass(frozen=True, slots=True)
class Capture(UOp):
    """
    Variable capture expression

    Stuff like this:
    ```
    ; CHECK: test5:
    ; CHECK:    notw     [[REGISTER:%[a-z]+]]
    ; CHECK:    andw     {{.*}}[[REGISTER]]
    ```
    """

    name: str
    pattern: str
    value_mapper: VALUE_MAPPER_T


@dataclass(frozen=True, slots=True)
class Subst(UOp):
    """
    Variable substitution, e.g. expect the contents of a variable here.

    Stuff like this:
    ```
    ; CHECK: test5:
    ; CHECK:    notw     [[REGISTER:%[a-z]+]]
    ; CHECK:    andw     {{.*}}[[REGISTER]]
    ````
    """

    variable: str


@dataclass(frozen=True, slots=True)
class NumSubst(UOp):
    """
    Numeric substitution (substitute variable with derived expression).

    Stuff like this:
    ```
    ; CHECK: load r[[#REG:]], [r0]
    ; CHECK: load r[[#REG+1]], [r1]
    ; CHECK: Loading from 0x[[#%x,ADDR:]]
    ; CHECK-SAME: to 0x[[#ADDR + 7]]
    ```
    """

    variable: str
    expr: str
