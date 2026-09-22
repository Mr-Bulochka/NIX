from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .state import utc_now_iso

if TYPE_CHECKING:
    from .app import NixApp

LAW_PROTECTED = "protected_paths"
LAW_BUDGET = "mutation_budget"
MUTATION_FILE = "experiments/mutations.json"


class MutationEngine:
    """Tracks file-writing mutations against the configured world laws.

    Two laws are enforced:

    * ``protected_paths`` -- a filename or path whose writes are refused;
    * ``mutation_budget`` -- the number of recorded mutations allowed
      before a checkpoint resets the counter.

    History is persisted to ``experiments/mutations.json`` inside the NIX
    state directory.
    """

    def __init__(self, app: NixApp) -> None:
        self.app = app

    def _load(self) -> dict:
        data = self.app.state.read_json(
            MUTATION_FILE, default={"count": 0, "items": []})
        if not isinstance(data, dict):
            data = {"count": 0, "items": []}
        data.setdefault("count", 0)
        data.setdefault("items", [])
        return data

    def _save(self, data: dict) -> None:
        self.app.state.write_json(MUTATION_FILE, data)

    @property
    def count(self) -> int:
        return self._load()["count"]

    @property
    def records(self) -> list[dict]:
        return self._load()["items"]

    def remaining(self) -> int:
        return max(0, self.app.config.mutation_budget - self.count)

    def check_laws(self, path) -> str | None:
        """Return the id of the law that blocks *path*, or None.

        ``protected_paths`` is matched against the basename or the full,
        slash-normalised path. ``mutation_budget`` blocks once the recorded
        mutation count reaches the budget and no checkpoint has reset it.
        """
        raw = str(path).replace("\\", "/")
        name = os.path.basename(raw)
        for target in (self.app.config.protected_paths or []):
            t = str(target).replace("\\", "/")
            if name == t or raw == t or raw.endswith("/" + t):
                return LAW_PROTECTED
        if self.remaining() <= 0:
            return LAW_BUDGET
        return None

    def record(self, kind: str, target, backup) -> None:
        """Persist one mutation and bump the pet's witness counter."""
        data = self._load()
        data["count"] += 1
        data["items"].append({
            "ts": utc_now_iso(),
            "kind": kind,
            "target": str(target),
            "backup": str(backup),
            "status": "ok",
        })
        self._save(data)
        self.app.journal.write(
            "MUTATION", "{kind} recorded for {target}".format(
                kind=kind, target=target))
        pet = self.app.pet
        if pet is not None:
            pet["mutations_witnessed"] = pet.get("mutations_witnessed", 0) + 1
            self.app.pet_store.save(pet)

    def reset_budget(self) -> None:
        data = self._load()
        data["count"] = 0
        self._save(data)