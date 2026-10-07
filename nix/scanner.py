from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

IGNORED_DIRS = {
    ".git", ".nix", "__pycache__", ".venv", "venv", "env",
    "node_modules", ".idea", ".vscode", ".mypy_cache",
    ".pytest_cache", "dist", "build", ".tox", ".eggs",
}

IGNORED_FILES = {
    "*.pyc", "*.pyo", "*.pyd", "*.dll", "*.so", "*.dylib",
    "*.exe", "*.o", "*.a", "*.lib",
}


from .modules.loader import all_modules, module_for_file
from .modules.engine import scan_blocks

# Module metadata is static for the process, so resolve it once instead of
# walking the package layout for every file we scan.
_MODULE_CACHE: dict = {m.id: m for m in all_modules()}


@dataclass
class ProjectInfo:
    root: Path
    files: int = 0
    directories: int = 0
    extensions: dict[str, int] = field(default_factory=dict)
    functions: int = 0
    classes: int = 0
    total_lines: int = 0
    source_files: int = 0

    @property
    def top_extensions(self) -> list[tuple[str, int]]:
        return sorted(self.extensions.items(), key=lambda x: (-x[1], x[0]))[:10]


def scan_project(root: Path) -> ProjectInfo:
    info = ProjectInfo(root=root)

    for path in root.rglob("*"):
        parts = path.relative_to(root).parts
        if any(p in IGNORED_DIRS for p in parts):
            continue

        if path.is_dir():
            info.directories += 1
        elif path.is_file():
            if any(path.match(pat) for pat in IGNORED_FILES):
                continue
            info.files += 1
            ext = path.suffix.lower() or "<no ext>"
            info.extensions[ext] = info.extensions.get(ext, 0) + 1

            if ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go",
                       ".java", ".c", ".cpp", ".h", ".rb", ".php"):
                info.source_files += 1
                _count_code(path, info)

    return info


def _count_code(path: Path, info: ProjectInfo) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return

    lines = text.splitlines()
    info.total_lines += len(lines)

    lang_id = module_for_file(str(path))
    mod = _MODULE_CACHE.get(lang_id) if lang_id else None
    if mod is not None:
        # Count through the language modules so that `functions` / `classes`
        # are populated for every supported language. Previously this looked for
        # a Python-only `def ` / `class ` prefix, so a Go, Rust or TypeScript
        # project always reported 0 of both -- indistinguishable from an
        # empty project in `scan`.
        for kind, bdef in mod.blocks.items():
            if kind == "function":
                info.functions += len(scan_blocks(lines, kind, bdef))
            elif kind == "class":
                info.classes += len(scan_blocks(lines, kind, bdef))
        return

    # No module for this extension: fall back to the Python shapes rather than
    # reporting nothing at all.
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("def ") and "(" in stripped:
            info.functions += 1
        elif stripped.startswith("class ") and ("(" in stripped or ":" in stripped):
            info.classes += 1
