from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class SessionLogger:
    def __init__(self, nix_dir: Path) -> None:
        self.dir = nix_dir / "logs"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "session.log"

    def write(self, kind: str, message: str) -> str:
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        line = f"[{stamp}] [{kind.upper():>10}] {message}"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        return line

    def read_last(self, n: int = 50) -> list[str]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return lines[-n:]
