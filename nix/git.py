from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field


@dataclass
class GitResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""

    @property
    def lines(self) -> list[str]:
        return self.stdout.strip().splitlines()


class Git:
    """Thin wrapper around the git CLI.  Every call is isolated,
    stateless, and works from the repo root only."""

    def __init__(self, root) -> None:
        self.root = root

    def _run(self, *args: str) -> GitResult:
        try:
            p = subprocess.run(
                ["git", *args],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=10,
            )
            return GitResult(ok=(p.returncode == 0),
                             stdout=p.stdout, stderr=p.stderr)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return GitResult(ok=False, stderr=str(exc))

    # ---- predicates ----------------------------------------------------

    def is_repo(self) -> bool:
        return self._run("rev-parse", "--is-inside-work-tree").ok

    # ---- read ----------------------------------------------------------

    def status_short(self) -> list[str]:
        return self._run("status", "-sb").lines

    def branch(self) -> str:
        lines = self._run("branch", "--show-current").lines
        return lines[0] if lines else "detached"

    def log(self, n: int = 10) -> list[str]:
        return self._run("log",
                         f"--oneline", f"-{n}").lines

    def diff_stat(self, cached: bool = True) -> list[str]:
        args = ["diff", "--stat"]
        if cached:
            args.append("--cached")
        lines = self._run(*args).lines
        if not lines:
            lines = self._run("diff", "--stat").lines
        return lines

    def diff_summary(self) -> list[dict]:
        """Parsed diff --stat lines into {file, insertions, deletions}."""
        out: list[dict] = []
        for line in self.diff_stat():
            m = re.match(r"\s*([^|]+)\|\s*(\d+)\s*(\+?)\s*(\d*)\s*(-?)",
                         line)
            if not m:
                continue
            file_ = m.group(1).strip()
            if "Bin" in line:
                out.append({"file": file_, "binary": True})
                continue
            out.append({
                "file": file_,
                "insertions": int(m.group(2)) if m.group(3) == "+" else 0,
                "deletions": int(m.group(4)) if m.group(5) == "-" else 0,
            })
        return out

    # ---- write ---------------------------------------------------------

    def add_all(self) -> GitResult:
        return self._run("add", "-A")

    def commit(self, message: str) -> GitResult:
        return self._run("commit", "-m", message)

    def generate_message(self) -> str:
        """Deterministic commit message from current diff summary."""
        summary = self.diff_summary()
        if not summary:
            return "chore: update"
        verbs: list[str] = []
        added = [s for s in summary if s.get("insertions", 0) and s.get("deletions", 0) == 0
                 and not s.get("binary")]
        removed = [s for s in summary if s.get("deletions", 0) and s.get("insertions", 0) == 0
                   and not s.get("binary")]
        updated = [s for s in summary if s not in added and s not in removed
                   and not s.get("binary")]
        parts: list[str] = []
        if added:
            parts.append(f"add {len(added)} file(s)")
        if removed:
            parts.append(f"remove {len(removed)} file(s)")
        if updated:
            parts.append(f"update {len(updated)} file(s)")
        detail = ", ".join(s["file"] for s in summary[:5])
        suffix = f" ({detail})" if len(summary) <= 5 else f" (+{len(summary) - 5} more)"
        return "nix: " + "; ".join(parts) + suffix if parts else "nix: update"