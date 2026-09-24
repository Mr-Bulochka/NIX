from __future__ import annotations

import hashlib
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from .checkpoints import SKIP_DIRS
from .runner import DEFAULT_TIMEOUT, TestRun, run_tests

if TYPE_CHECKING:
    from .app import NixApp

_EQ_RE = re.compile(r"(?<![=<>!])==(?!=)")
_NE_RE = re.compile(r"(?<![=<>!])!=(?!=)")
_TRUE_RE = re.compile(r"\bTrue\b")
_FALSE_RE = re.compile(r"\bFalse\b")
_DEF_RE = re.compile(r"^def\s+([A-Za-z_]\w*)\s*\(", re.M)
_CLASS_RE = re.compile(r"^class\s+([A-Za-z_]\w*)\s*([:(])", re.M)


@dataclass
class DestructReport:
    candidates: list[dict] = field(default_factory=list)
    baseline: TestRun | None = None
    checkpoint: str = ""
    items: list[str] = field(default_factory=list)
    kept: bool = False
    restored: bool = False


def _is_test_path(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    name = parts[-1]
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    return any(p in ("tests", "test") for p in parts)


def _collect_candidates(root) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            full = Path(dirpath) / fn
            rel = str(full.relative_to(root)).replace("\\", "/")
            if _is_test_path(rel):
                continue
            found.append(full)
    found.sort(key=lambda p: str(p))
    return found


def _mutate(text: str) -> tuple[str, str] | None:
    m = _EQ_RE.search(text)
    if m is not None:
        return text[:m.start()] + "!=" + text[m.end():], "==->!="
    m = _NE_RE.search(text)
    if m is not None:
        return text[:m.start()] + "==" + text[m.end():], "!=-=>=="
    m = _TRUE_RE.search(text)
    if m is not None:
        return text[:m.start()] + "False" + text[m.end():], "True->False"
    m = _FALSE_RE.search(text)
    if m is not None:
        return text[:m.start()] + "True" + text[m.end():], "False->True"
    m = _DEF_RE.search(text)
    if m is not None:
        return text[:m.start()] + "def _m(" + text[m.end():], "def->_m"
    m = _CLASS_RE.search(text)
    if m is not None:
        return text[:m.start()] + "class _m" + m.group(2) + text[m.end():], "class->_m"
    return None


def plan_mutations(root, max_mutations: int | None = None) -> list[dict]:
    plan: list[dict] = []
    for path in _collect_candidates(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        mutated = _mutate(text)
        if mutated is None:
            continue
        modified, operator = mutated
        rel = str(path.relative_to(root)).replace("\\", "/")
        plan.append({
            "path": str(path),
            "rel": rel,
            "operator": operator,
            "original": text,
            "modified": modified,
        })
        if max_mutations is not None and len(plan) >= max_mutations:
            break
    return plan


def _backup_file(path: Path, backups_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    digest = hashlib.sha1(
        str(path).replace("\\", "/").encode("utf-8")).hexdigest()[:10]
    backups_dir.mkdir(parents=True, exist_ok=True)
    backup = backups_dir / f"{stamp}-destruct-{digest}-{path.name}"
    shutil.copy2(path, backup)
    return backup


def _restore_from_backups(items: list[dict]) -> list[str]:
    restored: list[str] = []
    for item in items:
        backup = item.get("backup")
        if not backup:
            continue
        bpath = Path(backup)
        target = Path(item["path"])
        if not bpath.is_file() or not target.is_file():
            continue
        try:
            shutil.copy2(bpath, target)
        except OSError:
            continue
        restored.append(item["rel"])
    return restored


def run_destruct(app: NixApp, timeout: float = DEFAULT_TIMEOUT,
                 max_mutations: int | None = None,
                 keep: bool = False) -> DestructReport:
    plan = plan_mutations(app.root, max_mutations)
    report = DestructReport(candidates=plan)
    if not plan:
        return report
    report.baseline = run_tests(app.root, timeout=timeout)
    if report.baseline.no_tests or report.baseline.killed:
        return report
    cp_name = "destruct-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    app.checkpoints.create(cp_name, silent=True)
    report.checkpoint = cp_name
    backups_dir = app.state.nix / "brain" / "backups"
    for item in plan:
        path = Path(item["path"])
        law = app.mutations.check_laws(item["rel"])
        if law is not None:
            item["status"] = "blocked"
            item["detail"] = app.t(
                "fb.law_blocked", path=item["rel"], law=law)
            continue
        backup = _backup_file(path, backups_dir)
        item["backup"] = str(backup)
        try:
            path.write_text(item["modified"], encoding="utf-8")
        except OSError as exc:
            item["status"] = "error"
            item["detail"] = str(exc)
            continue
        app.mutations.record("destruct", item["rel"], backup)
        result = run_tests(app.root, timeout=timeout)
        item["result"] = result
        if result.killed:
            item["status"] = "killed"
            item["detail"] = app.t(
                "fb.destruct_killed",
                file=item["rel"],
                passed=result.passed,
                failed=result.failed,
            )
            try:
                path.write_text(item["original"], encoding="utf-8")
            except OSError:
                pass
        else:
            item["status"] = "survived"
            item["detail"] = app.t(
                "fb.destruct_survived",
                file=item["rel"],
                passed=result.passed,
                failed=result.failed,
            )
    if keep:
        report.kept = True
    else:
        info = app.checkpoints.info(cp_name)
        if info is not None:
            report.restored = True
            report.items.append(app.checkpoints.restore(cp_name, force=True))
        else:
            recovered = _restore_from_backups(plan)
            report.restored = True
            report.items.extend(
                app.t("destruct.restored", name=rel) for rel in recovered)
    app.add_pet_xp(20, "destruct")
    return report