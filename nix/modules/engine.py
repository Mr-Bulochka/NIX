from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Block:
    kind: str
    start: int  # 1-based line of the header
    end: int  # 1-based last line of the block body (header if empty)
    name: str
    indent: int  # leading whitespace width of the header


def leading_ws(line: str) -> int:
    return len(line) - len(line.lstrip())


def _compile(start_re) -> "re.Pattern[str] | None":
    try:
        return re.compile(start_re)
    except re.error:
        return None


def block_end(lines: list[str], start_i: int, body: str, indent: int) -> int:
    """Given the header line index, find 1-based end of the block body."""
    n = len(lines)
    if body == "indent":
        i = start_i + 1
        last = start_i
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            if leading_ws(line) > indent:
                last = i
                i += 1
                continue
            break
        return max(start_i, last)
    if body == "braces":
        depth_in = False
        for i in range(start_i, n):
            for ch in lines[i]:
                if ch == "{":
                    depth_in = True
                elif ch == "}":
                    if depth_in:
                        return i
        return n - 1
    if body == "do-end":
        end_re = re.compile(r"^\s*end\b")
        depth = 1
        for i in range(start_i, n):
            if end_re.match(lines[i]):
                depth -= 1
                if depth == 0:
                    return i
        return n - 1
    # default: until dedent, but keep a bounded horizon
    i = start_i + 1
    last = start_i
    while i < n and i - start_i < 5000:
        if not lines[i].strip():
            i += 1
            continue
        if leading_ws(lines[i]) > indent:
            last = i
            i += 1
            continue
        break
    return max(start_i, last)


def scan_blocks(lines: list[str], kind: str, block_def: dict) -> list[Block]:
    """Yield every top-level block of this kind detected by its start regex."""
    pattern = _compile(block_def.get("start", ""))
    if pattern is None:
        return []
    body = block_def.get("body", "indent")
    results: list[Block] = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        m = pattern.match(line.rstrip("\n"))
        if not m:
            continue
        indent = leading_ws(line)
        name = m.group("name") if "name" in m.groupdict() else ""
        end = block_end(lines, i, body, indent)
        results.append(Block(kind=kind, start=i + 1, end=end + 1,
                             name=name, indent=indent))
    return results


def find_block_at_line(lines: list[str], line_no: int,
                       block_defs: dict) -> Block | None:
    """Locate the deepest block whose span contains line_no (1-based)."""
    best: Block | None = None
    for kind, block_def in block_defs.items():
        for block in scan_blocks(lines, kind, block_def):
            if block.start <= line_no <= block.end:
                if best is None or (block.start, block.end) != (best.start, best.end):
                    # prefer the innermost: bigger start wins
                    if best is None or block.start >= best.start:
                        best = block
    return best


def fill_slots(text: str, slots: dict) -> str:
    for key, value in slots.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def apply_wrap(lines: list[str], block: Block, op_def: dict,
               slots: dict | None = None) -> list[str]:
    """Wrap a block body inside the template given by op_def, returning
    a new list of lines (block header untouched).
    op_def:  { "before": [...], "inner_indent": N, "after": [...],
               "slots": {"err": "Exception", ...} }
    """
    merged = dict(op_def.get("slots", {}))
    merged.update({"name": block.name, "kind": block.kind})
    if slots:
        merged.update(slots)

    head = lines[: block.start]
    body_lines = lines[block.start:block.end]
    tail = lines[block.end:]

    inner = int(op_def.get("inner_indent", 4))
    ws = " " * (block.indent + inner)
    ws_len = len(ws)
    bi = block.indent

    out_body: list[str] = []
    for line in body_lines:
        if not line.strip() and not out_body:
            continue  # drop leading blank lines inside the body
        if len(line) >= bi:
            inner_text = line[bi:]
        else:
            inner_text = line.lstrip()
        out_body.append(ws + inner_text)

    before = [fill_slots(" " * block.indent + ln, merged)
              for ln in op_def.get("before", [])]
    after = [fill_slots(" " * block.indent + ln, merged)
             for ln in op_def.get("after", [])]

    return list(head) + before + out_body + after + list(tail)


def render_template(template: str, slots: dict) -> str:
    """Fill a gen/*.tmpl template.  Lines that are a single slot with an
    empty value are dropped entirely (keeps templates clean)."""
    out: list[str] = []
    for line in template.split("\n"):
        stripped = line.strip()
        if stripped.startswith("{{") and stripped.endswith("}}"):
            key = stripped[2:-2].strip()
            if key in slots and not str(slots[key]).strip():
                continue
        out.append(fill_slots(line, slots))
    return "\n".join(out).rstrip("\n") + "\n"