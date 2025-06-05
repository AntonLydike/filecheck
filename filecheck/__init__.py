"""FileCheck package initialisation.

This package relies on the ``slots=True`` feature of ``@dataclasses.dataclass``
which only became available in Python 3.10.  When the library is imported on
an earlier interpreter (e.g. Py-3.9 used by the current test-suite) we patch
``dataclasses.dataclass`` so that the same source code continues to work and
the *effective* behaviour is preserved:

* The additional ``__slots__`` tuple is injected so instances do not obtain a
  per-instance ``__dict__``.
* All other keyword arguments are forwarded unchanged to the original
  decorator so that ordering, immutability, etc. keep functioning exactly as
  before.

The patch **must** run *before* any sub-module that uses
``from dataclasses import dataclass`` is imported, therefore it lives in the
package’s ``__init__.py`` which is executed first during the import process.
"""

from __future__ import annotations

import sys
import types as _types
import dataclasses as _dc


# ---------------------------------------------------------------------------
# Back-port ``@dataclass(slots=True)`` for Python < 3.10
# ---------------------------------------------------------------------------


if sys.version_info < (3, 10):

    _orig_dataclass = _dc.dataclass  # Keep a reference to the real decorator.

    def _patched_dataclass(*args, **kwargs):  # type: ignore[override]
        """A drop-in replacement for ``dataclasses.dataclass``.

        It recognises the *slots* keyword on older Pythons and emulates the
        relevant behaviour by injecting a suitable ``__slots__`` tuple when
        necessary.
        """

        # Extract and remove *slots* because the original decorator does not
        # understand it on these Python versions.
        use_slots: bool = bool(kwargs.pop("slots", False))

        def _add_slots(cls):  # type: ignore[return-type]
            # Only add __slots__ if it is not already defined explicitly.
            if use_slots and not hasattr(cls, "__slots__"):
                # The dataclass spec says that *only* the field names are
                # included.  Other special entries such as '__weakref__' are
                # intentionally omitted, matching the behaviour of the real
                # implementation.
                cls.__slots__ = tuple(cls.__annotations__.keys())  # type: ignore[attr-defined]

            # Delegate to the original decorator *after* modifying the class.
            return _orig_dataclass(cls, **kwargs)

        # ``@dataclass`` supports two invocation forms:
        #   1) As a simple decorator without arguments:  @dataclass
        #   2) As a decorator factory:                  @dataclass(frozen=True)
        # We replicate both calling conventions.

        if args and isinstance(args[0], type):
            # Called directly on a class, e.g.  @dataclass
            cls = args[0]
            return _add_slots(cls)

        if args:
            raise TypeError("Unexpected positional arguments to dataclass")

        # Called with keyword arguments, e.g.  @dataclass(order=True)
        def wrapper(cls):  # type: ignore[missing-return-type-doc]
            return _add_slots(cls)

        return wrapper

    # Replace the attribute in the *module object* so that subsequent
    # `from dataclasses import dataclass` statements pick up our patch.
    _dc.dataclass = _patched_dataclass  # type: ignore[assignment]

    # Additionally, update the already imported module in sys.modules under
    # its canonical key so other import paths continue to agree.
    sys.modules["dataclasses"].dataclass = _patched_dataclass  # type: ignore[attr-defined]


# Public re-exports (none at the moment)
# The package primarily serves as a namespace for sub-modules.
