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

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("def ") and "(" in stripped:
            info.functions += 1
        elif stripped.startswith("class ") and ("(" in stripped or ":" in stripped):
            info.classes += 1
