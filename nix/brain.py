from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from .modules.loader import all_modules, module_for_file
from .modules.engine import scan_blocks
from .scanner import IGNORED_DIRS

MAX_FILE_BYTES = 1_000_000

_NAME_STYLE = {
    "snake": re.compile(r"^[a-z][a-z0-9_]*$"),
    "camel": re.compile(r"^[a-z][a-zA-Z0-9]*$"),
    "pascal": re.compile(r"^[A-Z][a-zA-Z0-9]*$"),
    "kebab": re.compile(r"^[a-z][a-z0-9-]*$"),
}
_DOCSTR_OPEN = re.compile(r'^\s*(?:"""|\'\'\'+?|#|//|\*|\*)')
_EXCEPT_VAR = re.compile(r"\bexcept\s+[\w.]+\s+as\s+(\w+)\b")


class Brain:
    """The pet's memory of this project: structure index + style
    patterns.  Lives in .nix/brain/ and is rebuilt lazily, so the pet
    always knows the project fresher than the developer does."""

    def __init__(self, nix_dir: Path, root: Path) -> None:
        self.dir = nix_dir / "brain"
        self.root = Path(root)
        self.modules = {m.id: m for m in all_modules()}

    # ---- paths --------------------------------------------------------

    @property
    def index_path(self) -> Path:
        return self.dir / "index.json"

    @property
    def patterns_path(self) -> Path:
        return self.dir / "patterns.json"

    # ---- building -----------------------------------------------------

    def build(self) -> dict:
        if not self.modules:
            return {"files": 0, "symbols": []}
        symbols: list[dict] = []
        file_count = 0
        for path in self._iter_source_files():
            lang_id = module_for_file(str(path))
            if lang_id is None:
                continue
            mod = self.modules.get(lang_id)
            if mod is None:
                continue
            try:
                text = self._read_text(path)
            except OSError:
                continue
            lines = text.splitlines()
            file_count += 1
            rel = str(path.relative_to(self.root)).replace("\\", "/")
            for kind, bdef in mod.blocks.items():
                if kind not in ("function", "class"):
                    continue
                for block in scan_blocks(lines, kind, bdef):
                    symbols.append({
                        "kind": kind,
                        "name": block.name,
                        "file": rel,
                        "line": block.start,
                        "end": block.end,
                    })
        index = {"files": file_count, "symbols": symbols,
                 "built_at": _now()}
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=1),
            encoding="utf-8")
        patterns = self._derive_patterns(index)
        self._save_json(self.patterns_path, patterns)
        return index

    def _iter_source_files(self):
        import os
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
            for fn in filenames:
                p = Path(dirpath) / fn
                try:
                    if p.stat().st_size > MAX_FILE_BYTES:
                        continue
                except OSError:
                    continue
                yield p

    # ---- patterns -----------------------------------------------------

    def _derive_patterns(self, index: dict) -> dict:
        names: Counter = Counter()
        doc_count = 0
        fun_count = 0
        exc_vars: Counter = Counter()
        for sym in index.get("symbols", []):
            names[sym["kind"]] += 1
            if sym["kind"] == "function":
                fun_count += 1
        # naming style + docstrings is derived from source re-scan
        style_counts: Counter = Counter()
        for path in self._iter_source_files():
            lang_id = module_for_file(str(path))
            if lang_id is None:
                continue
            mod = self.modules.get(lang_id)
            if mod is None:
                continue
            try:
                text = self._read_text(path)
            except OSError:
                continue
            lines = text.splitlines()
            for kind in ("function", "class"):
                bdef = mod.blocks.get(kind)
                if not bdef:
                    continue
                pat = re.compile(bdef.get("start", "")) if bdef else None
                if pat is None:
                    continue
                for i, line in enumerate(lines):
                    m = pat.match(line)
                    if not m:
                        continue
                    name = m.group("name") if "name" in m.groupdict() else ""
                    for style, rx in _NAME_STYLE.items():
                        if rx.match(name):
                            style_counts[style] += 1
                            break
                    if kind == "function":
                        doc_open = False
                        for j in range(i + 1, min(len(lines), i + 4)):
                            if not lines[j].strip():
                                continue
                            if _DOCSTR_OPEN.match(lines[j]):
                                doc_open = True
                            break
                        if doc_open:
                            doc_count += 1
                for m in _EXCEPT_VAR.finditer(text):
                    exc_vars[m.group(1)] += 1
        return {
            "naming": dict(style_counts),
            "naming_top": style_counts.most_common(1)[0][0]
            if style_counts else "unknown",
            "functions": fun_count,
            "docstrings": doc_count,
            "function_doc_ratio": round(doc_count / max(1, fun_count), 2),
            "exception_var": exc_vars.most_common(1)[0][0]
            if exc_vars else "e",
            "modules_seen": names,
        }

    def load(self) -> tuple[dict, dict]:
        index = self._load_json(self.index_path) or {}
        patterns = self._load_json(self.patterns_path) or {}
        return index, patterns

    def ensure(self) -> tuple[dict, dict]:
        if not self.index_path.exists():
            self.build()
        return self.load()

    # ---- helpers ------------------------------------------------------

    @staticmethod
    def _read_text(path: Path) -> str:
        """Read source tolerating a UTF-8 BOM (common on Windows)."""
        text = path.read_text(encoding="utf-8", errors="replace")
        if text.startswith("\ufeff"):
            text = text[1:]
        return text

    def _save_json(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    @staticmethod
    def _load_json(path: Path) -> dict | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None


def _now() -> str:
    from .state import utc_now_iso
    return utc_now_iso()