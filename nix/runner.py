from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TIMEOUT = 120

_COUNT_RE = re.compile(
    r"(\d+)\s+(passed|failed|errors?|skipped)\b")
_RAN_RE = re.compile(r"Ran\s+(\d+)\s+tests?")
_UT_FAIL_RE = re.compile(r"FAILED\s*\(([^)]*)\)")


def has_pytest() -> bool:
    try:
        return importlib.util.find_spec("pytest") is not None
    except (ImportError, ValueError):
        return False


def runner_name() -> str:
    return "pytest" if has_pytest() else "unittest"


@dataclass
class TestRun:
    """One parsed test-suite execution."""

    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    ran_tests: int = 0
    duration: float = 0.0
    returncode: int | None = None
    timed_out: bool = False
    no_tests: bool = False
    tail: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (not self.timed_out and not self.no_tests
                and self.returncode == 0 and self.ran_tests > 0
                and self.failed == 0 and self.errors == 0)

    @property
    def killed(self) -> bool:
        return not self.ok


def _as_text(value) -> str:
    if not value:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def _tail_lines(text: str, n: int = 15) -> list[str]:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return lines[-n:]


def _parse_text(text: str, run: TestRun) -> None:
    passed = failed = errors = skipped = 0
    for m in _COUNT_RE.finditer(text):
        n = int(m.group(1))
        kind = m.group(2)
        if kind.startswith("pass"):
            passed = n
        elif kind.startswith("fail"):
            failed = n
        elif kind.startswith("error"):
            errors = n
        elif kind.startswith("skip"):
            skipped = n
    m = _UT_FAIL_RE.search(text)
    if m:
        for part in m.group(1).split(","):
            if "=" not in part:
                continue
            key, raw = part.split("=", 1)
            key = key.strip()
            try:
                n = int(raw.strip())
            except ValueError:
                continue
            if key == "failures":
                failed = n
            elif key == "errors":
                errors = n
            elif key == "skipped":
                skipped = n
    run.passed = passed
    run.failed = failed
    run.errors = errors
    run.skipped = skipped
    m = _RAN_RE.search(text)
    if m:
        run.ran_tests = int(m.group(1))
    if run.ran_tests <= 0:
        run.ran_tests = passed + failed + errors + skipped
    if run.ran_tests > 0 and run.passed == 0:
        run.passed = max(
            0, run.ran_tests - run.failed - run.errors - run.skipped)


def run_tests(root, timeout: float = DEFAULT_TIMEOUT) -> TestRun:
    """Run the project's test suite once and return the parsed result.

    Prefers pytest when it is importable, otherwise falls back to
    ``python -m unittest discover`` (scoped to ``tests/`` when present).
    Exit code 5 or zero collected tests marks the run as ``no_tests``;
    any failure, error, timeout or non-zero exit counts as killed."""
    run = TestRun()
    use_pytest = has_pytest()
    if use_pytest:
        cmd = [sys.executable, "-m", "pytest", "-q", "--tb=no"]
    else:
        cmd = [sys.executable, "-m", "unittest", "discover"]
        if (Path(root) / "tests").is_dir():
            cmd += ["-s", "tests"]
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        run.duration = time.monotonic() - start
        run.timed_out = True
        text = _as_text(exc.stdout) + "\n" + _as_text(exc.stderr)
        _parse_text(text, run)
        run.tail = _tail_lines(text)
        return run
    except OSError as exc:
        run.duration = time.monotonic() - start
        run.returncode = -1
        run.errors = 1
        run.tail = [str(exc)]
        return run
    run.duration = time.monotonic() - start
    run.returncode = proc.returncode
    text = f"{_as_text(proc.stdout)}\n{_as_text(proc.stderr)}"
    _parse_text(text, run)
    run.tail = _tail_lines(text)
    if run.ran_tests <= 0:
        if use_pytest and proc.returncode == 5:
            run.no_tests = True
        elif proc.returncode == 0:
            run.no_tests = True
        else:
            run.errors = max(run.errors, 1)
    return run
