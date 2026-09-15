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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def remove_json(self, relative: str) -> bool:
        path = self.nix / relative
        if path.exists():
            path.unlink()
            return True
        return False
