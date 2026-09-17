"""Feature scaffolding engine for NIX.

Parses column specs, builds template slots, and renders scaffold
templates for models, CRUD, and tests.  All language-specific logic
lives in the module's gen/ templates; this file is pure plumbing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── column spec ────────────────────────────────────────────────────

TYPE_MAP: dict[str, tuple[str, str]] = {
    "str":     ("str", '""'),
    "string":  ("str", '""'),
    "int":     ("int", "0"),
    "integer": ("int", "0"),
    "float":   ("float", "0.0"),
    "double":  ("float", "0.0"),
    "bool":    ("bool", "False"),
    "boolean": ("bool", "False"),
    "list":    ("list", "field(default_factory=list)"),
    "dict":    ("dict", "field(default_factory=dict)"),
}


@dataclass
class Column:
    name: str
    type: str = "str"
    is_pk: bool = False
    is_optional: bool = False


def parse_columns(spec: str) -> list[Column]:
    """Parse ``name:str:pk,age:int,email:str:opt`` into a Column list."""
    columns: list[Column] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        tokens = [t.strip() for t in part.split(":")]
        name = tokens[0]
        col_type = tokens[1] if len(tokens) > 1 else "str"
        flags = {t.lower() for t in tokens[2:]}
        columns.append(Column(
            name=name,
            type=col_type,
            is_pk="pk" in flags,
            is_optional="opt" in flags or "optional" in flags,
        ))
    return columns


# ── naming helpers ─────────────────────────────────────────────────

def _to_snake(name: str) -> str:
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    name = name.replace("-", "_").replace(" ", "_")
    return name.lower()


def _to_pascal(name: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+|(?<=[a-z0-9])(?=[A-Z])", name)
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


# ── slot builders ──────────────────────────────────────────────────

def _build_fields(columns: list[Column]) -> str:
    """Render dataclass field lines (indented 4 spaces)."""
    lines: list[str] = []
    for col in columns:
        py_type, default = TYPE_MAP.get(col.type, ("str", '""'))
        if col.is_pk:
            lines.append(f"    {col.name}: {py_type}")
        elif col.is_optional:
            lines.append(f"    {col.name}: {py_type} = {default}")
        else:
            lines.append(f"    {col.name}: {py_type} = {default}")
    return "\n".join(lines)


def _py_value(col: Column) -> str:
    """Return a sample Python literal for a column (used in tests)."""
    mapping = {
        "str": '"test_{name}"',
        "int": "25",
        "float": "1.5",
        "bool": "True",
        "list": "[1]",
        "dict": '{"k": "v"}',
    }
    return mapping.get(col.type, '"test_{name}"').format(name=col.name)


def _py_missing(col: Column) -> str:
    """Return a 'missing' Python literal for a column."""
    mapping = {
        "str": '"__nonexistent__"',
        "int": "-999",
        "float": "-999.0",
        "bool": "False",
        "list": "[]",
        "dict": "{}",
    }
    return mapping.get(col.type, '"__nonexistent__"')


def build_slots(entity: str, columns: list[Column],
                module_name: str = "") -> dict[str, str]:
    """Build all template slots for the given entity and columns."""
    snake = _to_snake(entity)
    ent = _to_pascal(entity)
    upper = snake.upper()

    pk = next((c for c in columns if c.is_pk), columns[0]) if columns else None

    # model fields (indented)
    fields = _build_fields(columns) if columns else "    pass"

    # store line
    store = f"_{upper}_STORE: list[{ent}] = []"

    # create function params
    create_parts: list[str] = []
    create_call_parts: list[str] = []
    for col in columns:
        py_type, default = TYPE_MAP.get(col.type, ("str", '""'))
        if col.is_pk:
            create_parts.append(f"{col.name}: {py_type}")
        elif col.is_optional:
            create_parts.append(f"{col.name}: {py_type} = {default}")
        else:
            create_parts.append(f"{col.name}: {py_type} = {default}")
        create_call_parts.append(f"{col.name}={col.name}")

    create_params = ", ".join(create_parts)
    create_call = ", ".join(create_call_parts)

    # pk slots
    pk_name = pk.name if pk else ""
    pk_type = TYPE_MAP.get(pk.type, ("str", '""'))[0] if pk else "str"

    # test slots
    test_args = ", ".join(_py_value(c) for c in columns)
    test_pk_val = _py_value(pk) if pk else '""'
    test_pk_miss = _py_missing(pk) if pk else '""'

    # test update kwargs: find first non-pk column
    non_pk = [c for c in columns if not (pk and c.name == pk.name)]
    if non_pk:
        first = non_pk[0]
        _, default = TYPE_MAP.get(first.type, ("str", '""'))
        test_update_kw = f'{{"{first.name}": {default}}}'
    else:
        test_update_kw = "{}"

    # docstring
    docstring = ""

    return {
        "Ent": ent,
        "snake": snake,
        "upper": upper,
        "fields": fields,
        "store": store,
        "create_params": create_params,
        "create_call": create_call,
        "pk_name": pk_name,
        "pk_type": pk_type,
        "module": module_name or snake,
        "test_args": test_args,
        "test_pk_val": test_pk_val,
        "test_pk_miss": test_pk_miss,
        "test_update_kw": test_update_kw,
        "docstring": docstring,
    }


# ── public API ─────────────────────────────────────────────────────

def render_scaffold(mod, entity: str, columns: list[Column],
                    module_name: str = "") -> dict[str, str]:
    """Render all scaffold parts using the module's gen templates.

    Returns a dict with keys ``model``, ``crud``, ``test`` mapping to
    rendered source strings.
    """
    from .modules.engine import render_template

    slots = build_slots(entity, columns, module_name)
    parts: dict[str, str] = {}

    for key, tmpl_key in [("model", "scaffold_model"),
                          ("crud", "scaffold_crud"),
                          ("test", "scaffold_test")]:
        tmpl = mod.gen.get(tmpl_key, "")
        if tmpl:
            parts[key] = render_template(tmpl, slots)

    return parts


def render_testgen(mod, symbols: list[dict],
                   module_name: str = "") -> str:
    """Render test stubs for a list of brain-index symbols.

    Each symbol is ``{"kind": "function"|"class", "name": "...", ...}``.
    """
    from .modules.engine import render_template

    tmpl = mod.gen.get("testgen", "")
    if not tmpl:
        return ""

    slots = {
        "module": module_name,
        "functions": "",
        "classes": "",
    }

    func_lines: list[str] = []
    class_lines: list[str] = []

    for sym in symbols:
        name = sym.get("name", "")
        kind = sym.get("kind", "")
        if kind == "function":
            func_lines.append(
                f"    def test_{name}(self):\n"
                f"        # TODO: test {name}\n"
                f"        self.assertTrue(True)\n"
            )
        elif kind == "class":
            class_lines.append(
                f"    def test_{name}_instantiation(self):\n"
                f"        # TODO: test {name}\n"
                f"        self.assertTrue(True)\n"
            )

    slots["functions"] = "\n".join(func_lines) if func_lines else ""
    slots["classes"] = "\n".join(class_lines) if class_lines else ""

    return render_template(tmpl, slots)
