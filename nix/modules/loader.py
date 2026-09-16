from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

BUNDLED_DIR = Path(__file__).resolve().parent / "bundled"
USER_HOME = Path(os.environ.get("NIX_HOME", "~")).expanduser()
USER_MODULES_DIR = USER_HOME / ".nix" / "modules"


@dataclass
class CodeModule:
    id: str
    name: str
    version: str
    extensions: list[str] = field(default_factory=list)
    blocks: dict = field(default_factory=dict)
    ops: dict = field(default_factory=dict)
    gen: dict = field(default_factory=dict)
    probe: dict = field(default_factory=dict)
    source: str = "bundled"

    def block_def(self, kind: str) -> dict:
        return self.blocks.get(kind, {})

    def matches(self, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in self.extensions


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_dir(module_dir: Path, source: str) -> CodeModule | None:
    manifest = module_dir / "module.json"
    if not manifest.exists():
        return None
    data = _read_json(manifest)
    mod = CodeModule(
        id=data.get("id", module_dir.name),
        name=data.get("name", module_dir.name),
        version=data.get("version", "0.0"),
        extensions=list(data.get("extensions", [])),
        source=source,
    )
    blocks_path = module_dir / "blocks.json"
    if blocks_path.exists():
        mod.blocks = _read_json(blocks_path).get("blocks", {})
    ops_path = module_dir / "ops.json"
    if ops_path.exists():
        mod.ops = _read_json(ops_path).get("ops", {})
    gen_dir = module_dir / "gen"
    if gen_dir.is_dir():
        for tmpl in sorted(gen_dir.glob("*.tmpl")):
            mod.gen[tmpl.stem] = tmpl.read_text(encoding="utf-8")
    probe_path = module_dir / "probe.json"
    if probe_path.exists():
        mod.probe = _read_json(probe_path)
    return mod


def _module_dir_for(user_dir: Path, modules_dir: Path) -> Path | None:
    candidates = [
        modules_dir / f"lang-{user_dir.name}" / user_dir.name,
        modules_dir / user_dir.name,
    ]
    for cand in candidates:
        if (cand / "module.json").exists():
            return cand
    return None


def load_module(module_id: str) -> CodeModule | None:
    """Load a code module.  A user module (NIX_HOME/~/.nix/modules)
    shadows the bundled one with the same id."""
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", module_id):
        return None
    if USER_MODULES_DIR.is_dir():
        for child in sorted(USER_MODULES_DIR.iterdir()):
            if not child.is_dir():
                continue
            resolved = _module_dir_for(child, USER_MODULES_DIR)
            if resolved is not None:
                candidate = _read_dir(resolved, "user")
                if candidate is not None and candidate.id == module_id:
                    return candidate
    bundled = BUNDLED_DIR / module_id
    if bundled.is_dir():
        return _read_dir(bundled, "bundled")
    return None


def all_modules() -> list[CodeModule]:
    mods: dict[str, CodeModule] = {}
    for child in sorted(BUNDLED_DIR.iterdir()):
        if child.is_dir():
            mod = _read_dir(child, "bundled")
            if mod is not None:
                mods[mod.id] = mod
    if USER_MODULES_DIR.is_dir():
        for child in sorted(USER_MODULES_DIR.iterdir()):
            if not child.is_dir():
                continue
            by_id = _read_dir(child, "user")
            if by_id is not None:
                mods[by_id.id] = by_id  # simplest form: a module in its own folder
                continue
            resolved = _module_dir_for(child, USER_MODULES_DIR)
            if resolved is None:
                continue
            mod = _read_dir(resolved, "user")
            if mod is not None:
                mods[mod.id] = mod  # user wins
    return sorted(mods.values(), key=lambda m: m.id)


def module_for_file(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    for mod in all_modules():
        if ext in mod.extensions:
            return mod.id
    return None