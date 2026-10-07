from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_DIRS = (
    "state",
    "journal",
    "logs",
    "memory",
    "experiments",
    "checkpoints/permanent",
    "checkpoints/temporary",
    "pet",
    "origin",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def utc_now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def atomic_write_text(path: Path, text: str) -> None:
    """Write *text* to *path* so readers never observe a partial file.

    ``Path.write_text`` truncates the target first, so a crash or Ctrl-C midway
    through leaves invalid JSON behind. ``read_json`` swallows the parse error
    and returns the default, which for the config means every user setting
    silently reverts. Writing to a sibling temp file and renaming over the
    target makes the swap atomic on both POSIX and Windows, because a rename
    within one directory is a single filesystem operation.
    """
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(str(tmp), str(path))
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _read_json_text(text: str | None, default=None):
    if text is None:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default


class State:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.nix = project_root / ".nix"

    def exists(self) -> bool:
        return self.nix.is_dir()

    def initialize(self) -> None:
        self.nix.mkdir(parents=True, exist_ok=True)
        for subdir in STATE_DIRS:
            (self.nix / subdir).mkdir(parents=True, exist_ok=True)

    def read_json(self, relative: str, default=None):
        path = self.nix / relative
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default

    def write_json(self, relative: str, value) -> None:
        path = self.nix / relative
        atomic_write_text(
            path, json.dumps(value, indent=2, ensure_ascii=False))

    def remove_json(self, relative: str) -> bool:
        path = self.nix / relative
        if path.exists():
            path.unlink()
            return True
        return False
