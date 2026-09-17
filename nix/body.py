"""Function body inference for the gen command.

Given a function's name, parameter list, and return annotation, this
derives a sensible body for the honest, conventional cases:
constructors, getters, and setters.  Anything it is not sure about
stays ``pass`` (the gen default).
"""
from __future__ import annotations

import re


def _param_names(params: str) -> list[str]:
    """Extract plain parameter names from a comma-joined spec.

    Drops ``self``/``cls`` and variadic parameters (``*args``,
    ``**kwargs``).  Handles ``name: str = "x"`` and ``age: int = 0``.
    """
    names: list[str] = []
    for part in params.split(","):
        p = part.strip()
        if not p:
            continue
        base = re.split(r"[:=]", p)[0].strip()
        if not base or base in ("self", "cls") or base.startswith(("*", "**")):
            continue
        names.append(base)
    return names


def infer_body(name: str, params: str, ret: str = "") -> str:
    """Suggest a body for a function, or ``pass`` when unsure.

    The returned string uses 4-space inner indentation so it can be
    dropped straight into a ``    {{body}}`` template line.
    """
    if name == "__init__":
        assigned = _param_names(params)
        if not assigned:
            return "pass"
        return "\n    ".join(f"self.{p} = {p}" for p in assigned)

    if name.startswith("get_"):
        field = name[4:].strip("_")
        if field:
            return f"return self._{field}"

    if name.startswith("set_"):
        field = name[4:].strip("_")
        if field:
            args = _param_names(params)
            value = args[0] if args else field
            return f"self._{field} = {value}"

    return "pass"