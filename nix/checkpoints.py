from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from .state import utc_now_iso

if TYPE_CHECKING:
    from .app import NixApp

KIND_TEMP = "temporary"
KIND_PERM = "permanent"

SKIP_DIRS = {
    ".nix", ".git", "__pycache__", ".pytest_cache", "venv", ".venv",
    "node_modules", ".mypy_cache", ".ruff_cache", "dist", "build",
    ".eggs", ".tox", ".nox", ".cache", "htmlcov",
}
SKIP_FILES = {".coverage"}
SKIP_SUFFIXES = (".pyc", ".pyo", ".egg-info")


def _slugify(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9\-_]", "-", name).strip("-") or "manual"


def _safe_rel(rel: str) -> bool:
    if not rel:
        return False
    p = Path(rel)
    return not p.is_absolute() and ".." not in p.parts


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.endswith(SKIP_SUFFIXES)


def _should_skip_file(name: str) -> bool:
    return name in SKIP_FILES or name.endswith(SKIP_SUFFIXES)


def _collect_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
        parent = Path(dirpath)
        for fname in filenames:
            if not _should_skip_file(fname):
                found.append(parent / fname)
    return found


def _file_size(path: Path) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


class CheckpointManager:
    """Snapshots the project tree into the NIX state directory.

    Checkpoints live under ``checkpoints/<temporary|permanent>/<name>/`` and
    hold a copy of every non-excluded project file plus a ``manifest.json``.
    The manifest carries friendly metadata (``name``, ``created_at``,
    ``origin``, ``files``, ``size``) alongside legacy fields (``created``,
    ``root``, ``mode``, ``stage``, ``skin``) so older checkpoints remain
    readable.
    """

    def __init__(self, app: NixApp) -> None:
        self.app = app

    def _dir(self, kind: str) -> Path:
        return self.app.state.nix / "checkpoints" / kind

    def _resolve(self, name: str) -> Path | None:
        for kind in (KIND_TEMP, KIND_PERM):
            candidate = self._dir(kind) / name
            if candidate.exists() and candidate.is_dir():
                return candidate
        return None

    def _read_manifest(self, src: Path) -> dict:
        manifest: dict = {}
        manifest_path = src / "manifest.json"
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    manifest = data
            except (OSError, json.JSONDecodeError):
                manifest = {}
        manifest.setdefault("name", src.name)
        if "created_at" not in manifest:
            manifest["created_at"] = manifest.get("created")
        manifest.setdefault("created_at", "")
        if "origin" not in manifest:
            manifest["origin"] = manifest.get("root", "")
        manifest.setdefault("origin", "")
        files = manifest.get("files")
        if not isinstance(files, list):
            files = []
            manifest["files"] = files
        if not isinstance(manifest.get("size"), int):
            manifest["size"] = sum(
                _file_size(src / rel) for rel in files if _safe_rel(rel))
        return manifest

    def create(self, name: str, silent: bool = False) -> None:
        root = self.app.root
        dest = self._dir(KIND_TEMP) / _slugify(name)
        if dest.exists():
            try:
                shutil.rmtree(dest)
            except OSError as exc:
                if not silent and getattr(self.app, "ui", None):
                    self.app.ui.show_message(
                        "ERROR",
                        self.app.t("fb.failed", name="checkpoint", exc=exc))
                return
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            if not silent and getattr(self.app, "ui", None):
                self.app.ui.show_message(
                    "ERROR",
                    self.app.t("fb.failed", name="checkpoint", exc=exc))
            return

        rel_files: list[str] = []
        total = 0
        for path in _collect_files(Path(root)):
            rel = path.relative_to(root)
            rel_files.append(str(rel).replace("\\", "/"))
            total += _file_size(path)
            try:
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
            except OSError as exc:
                if not silent and getattr(self.app, "ui", None):
                    self.app.ui.show_message(
                        "ERROR",
                        self.app.t("fb.failed", name="checkpoint", exc=exc))
                return

        pet = self.app.pet or {}
        now = utc_now_iso()
        manifest = {
            "name": dest.name,
            "created": now,
            "created_at": now,
            "origin": str(root),
            "root": str(root),
            "mode": self.app.config.mode,
            "stage": pet.get("body_pattern", "seed"),
            "skin": pet.get("skin"),
            "files": rel_files,
            "size": total,
        }
        (dest / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.app.journal.write("CHECKPOINT", f"created {dest.name}")
        if not silent and getattr(self.app, "ui", None):
            self.app.ui.show_message(
                "SYSTEM", self.app.t("fb.checkpoint_created", name=dest.name))
        try:
            add = getattr(self.app, "add_pet_xp", None)
            if callable(add):
                add(10, "checkpoint", save=True)
        except Exception:
            pass

    def list(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        for kind in (KIND_TEMP, KIND_PERM):
            kind_dir = self._dir(kind)
            if not kind_dir.is_dir():
                continue
            for child in sorted(kind_dir.iterdir()):
                if child.is_dir():
                    rows.append((child.name, kind))
        return rows

    def info(self, name: str) -> dict | None:
        src = self._resolve(name)
        if src is None:
            return None
        manifest = self._read_manifest(src)
        manifest["kind"] = src.parent.name
        return manifest

    def promote(self, name: str) -> str:
        src = self._resolve(name)
        if src is None:
            return self.app.t("fb.no_such_checkpoint", name=name)
        if src.parent.name == KIND_PERM:
            return self.app.t("fb.checkpoint_promoted", name=name)
        dest = self._dir(KIND_PERM) / name
        try:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(src), str(dest))
        except OSError as exc:
            return self.app.t("fb.failed", name="checkpoint", exc=exc)
        self.app.journal.write("CHECKPOINT", f"promoted {name}")
        return self.app.t("fb.checkpoint_promoted", name=name)

    def delete(self, name: str) -> str:
        src = self._resolve(name)
        if src is None:
            return self.app.t("fb.no_such_checkpoint", name=name)
        try:
            shutil.rmtree(src)
        except OSError as exc:
            return self.app.t("fb.failed", name="checkpoint", exc=exc)
        self.app.journal.write("CHECKPOINT", f"deleted {name}")
        return self.app.t("fb.checkpoint_deleted", name=name)

    def restore(self, name: str, force: bool = False, dry: bool = False) -> str:
        src = self._resolve(name)
        if src is None:
            return self.app.t("fb.no_such_checkpoint", name=name)
        manifest = self._read_manifest(src)
        targets = [rel for rel in manifest.get("files", []) if _safe_rel(rel)]
        if not targets:
            return self.app.t("fb.checkpoint_restored", name=name)

        protected = [str(p).replace("\\", "/")
                     for p in (self.app.config.protected_paths or [])]
        if not force:
            for rel in targets:
                raw = str(Path(self.app.root) / rel).replace("\\", "/")
                base = os.path.basename(raw)
                if any(base == t or raw == t or raw.endswith("/" + t)
                       for t in protected):
                    return self.app.t(
                        "fb.restore_blocked_protected", name=name, path=rel)

        if dry:
            return self.app.t(
                "fb.restore_dry_run", name=name, count=len(targets))

        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup = self._dir(KIND_PERM) / f"{src.name}_pre-restore_{ts}"
        backup.mkdir(parents=True, exist_ok=True)
        existing: list[str] = []
        for rel in targets:
            current = Path(self.app.root) / rel
            if current.is_file():
                existing.append(rel)
                shutil.copy2(current, backup / rel)
        if existing:
            (backup / "manifest.json").write_text(
                json.dumps({
                    "name": src.name,
                    "created": utc_now_iso(),
                    "restored_from": name,
                    "files": existing,
                }, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self.app.journal.write("CHECKPOINT", f"backup {backup.name}")

        copied = 0
        for rel in targets:
            source = src / rel
            target = Path(self.app.root) / rel
            if source.is_file() and not target.is_dir():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                copied += 1
        self.app.journal.write("CHECKPOINT", f"restored {name}")
        msg = self.app.t("fb.checkpoint_restored", name=name)
        if existing:
            msg = f"{msg} " + self.app.t(
                "fb.safety_backup_created", name=backup.name)
        return msg