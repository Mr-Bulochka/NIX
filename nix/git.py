from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass


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
            m = re.match(r"\s*([^|]+)\|\s*(\d+)\s*(\+*-*)\s*$", line.strip())
            if not m:
                if "Bin" in line:
                    file_ = line.split("|")[0].strip()
                    out.append({"file": file_, "binary": True})
                continue
            file_ = m.group(1).strip()
            total = int(m.group(2))
            marks = m.group(3) or ""
            inserts = marks.count("+")
            deletes = marks.count("-")
            if not marks:
                inserts, deletes = total, 0
            out.append({
                "file": file_,
                "insertions": inserts,
                "deletions": deletes,
            })
        return out

    # ---- remote ---------------------------------------------------------

    def remote_name(self) -> str:
        return self._run("remote", "get-url", "origin").stdout.strip()

    def remote_urls(self) -> list[tuple[str, str]]:
        """[(name, url)] via `git remote -v` (deduplicated fetch lines)."""
        seen: dict[str, str] = {}
        for line in self._run("remote", "-v").lines:
            parts = line.split()
            if len(parts) >= 3 and parts[2] == "(fetch)":
                seen.setdefault(parts[0], parts[1])
        return list(seen.items())

    def ahead_behind(self) -> tuple[int, int] | None:
        """(ahead, behind) vs upstream; None when no upstream tracked."""
        res = self._run("rev-list", "--left-right", "--count", "HEAD...@{u}")
        if not res.ok:
            return None
        parts = res.stdout.split()
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None

    def unsent_commits(self, branch: str) -> list[str]:
        """Commits on *branch* not yet present on origin/<branch>."""
        return self._run("log", "--oneline", "--no-decorate",
                         f"origin/{branch}..{branch}").lines

    def fetch(self) -> GitResult:
        return self._run("fetch", "--all", "--prune")

    def pull(self) -> GitResult:
        res = self._run("pull", "--rebase")
        if not res.ok:
            # plain merge fallback
            res = self._run("pull")
        return res

    def push(self, branch: str | None = None) -> GitResult:
        if branch:
            return self._run("push", "-u", "origin", branch)
        return self._run("push")

    def snapshot(self) -> dict:
        """Serialize the remote state so `remote info` can show a cache."""
        urls = self.remote_urls()
        platform = platform_for_url(urls[0][1]) if urls else "other"
        branch = self.branch()
        ab = self.ahead_behind()
        return {
            "urls": urls,
            "platform": platform,
            "branch": branch,
            "ahead_behind": [ab[0], ab[1]] if ab is not None else None,
            "unsent": self.unsent_commits(branch) if branch else [],
        }

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


def platform_for_url(url: str) -> str:
    """Detect hosting platform from a remote url.

    Returns "github", "gitlab" or "other".  Self-hosted instances count as
    gitlab when the host contains "gitlab", otherwise "other".
    """
    if not url:
        return "other"
    low = url.lower()
    if "gitlab" in low or "gl.example" in low:
        return "gitlab"
    if "github" in low or "gh.example" in low:
        return "github"
    m = re.search(r"@([^:/\s]+)[:/]", url)
    host = m.group(1) if m else ""
    if "gitlab" in host:
        return "gitlab"
    if "github" in host:
        return "github"
    return "other"


class RemoteCli:
    """Adapter over the hosting CLI (gh / glab).  Both produce a
    feature-identical *list* of open PRs/MRs and can open a new one."""

    BINS = {"github": "gh", "gitlab": "glab"}

    def __init__(self, root, platform: str) -> None:
        self.root = root
        self.platform = platform
        self.bin = self.BINS.get(platform)

    def available(self) -> bool:
        return bool(self.bin) and shutil.which(self.bin) is not None

    def _run(self, *args: str) -> GitResult:
        if not self.bin:
            return GitResult(ok=False, stderr="no cli")
        try:
            p = subprocess.run([self.bin, *args],
                               cwd=str(self.root),
                               capture_output=True, text=True, timeout=15)
            return GitResult(ok=(p.returncode == 0),
                             stdout=p.stdout, stderr=p.stderr)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return GitResult(ok=False, stderr=str(exc))

    def open_prs(self) -> GitResult:
        if self.platform == "github":
            return self._run("pr", "list", "--state", "open",
                             "--limit", "20")
        return self._run("mr", "list", "--state", "opened",
                         "--limit", "20")

    def open_pr(self, title: str) -> GitResult:
        if self.platform == "github":
            return self._run("pr", "create", "--title", title,
                             "--body", "Created by NIX")
        return self._run("mr", "create", "--title", title,
                         "--yes")