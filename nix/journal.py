from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Journal:
    def __init__(self, nix_dir: Path) -> None:
        self.dir = nix_dir / "journal"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _today_file(self) -> Path:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.dir / f"{date_str}.jsonl"

    def write(self, kind: str, message: str, **extra) -> None:
        entry = {
            "ts": _utc_stamp(),
            "kind": kind.upper(),
            "message": message,
        }
        if extra:
            entry["data"] = extra
        line = json.dumps(entry, ensure_ascii=False)
        with self._today_file().open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def read_today(self) -> list[dict]:
        path = self._today_file()
        if not path.exists():
            return []
        entries = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    def read_all(self) -> list[dict]:
        entries = []
        for path in sorted(self.dir.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries
