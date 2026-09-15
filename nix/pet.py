from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PET = {
    "name": "",
    "stage": 1,
    "body_pattern": "seed",
    "mood": "curious",
    "energy": 100,
    "age": 0,
    "evolution_level": 0,
    "mutations_witnessed": 0,
    "failures_survived": 0,
    "projects_seen": 0,
    "scans": 0,
}

STAGES = {
    "seed": 0,
    "sprout": 1,
    "bloom": 2,
    "mystic": 3,
}

STAGE_AGE_LIMITS = [("mystic", 35), ("bloom", 15), ("sprout", 5)]


class Pet:
    def __init__(self, nix_dir: Path) -> None:
        self.path = nix_dir / "pet" / "identity.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for key, default in DEFAULT_PET.items():
                data.setdefault(key, default)
            return data
        except (OSError, json.JSONDecodeError):
            return None

    def create(self, name: str) -> dict:
        data = dict(DEFAULT_PET)
        data["name"] = name
        self._save(data)
        return data

    def save(self, pet: dict) -> None:
        self._save(pet)

    def _save(self, data: dict) -> None:
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def update_mood(self, pet: dict, event: str) -> dict:
        mood_transitions = {
            "success": {"curious": "happy", "tired": "content", "anxious": "relieved"},
            "failure": {"happy": "determined", "curious": "thoughtful", "content": "alert"},
            "error": {"happy": "worried", "curious": "cautious"},
            "scan": {"curious": "focused"},
            "idle": {"focused": "curious", "alert": "curious"},
        }
        transitions = mood_transitions.get(event, {})
        current = pet.get("mood", "curious")
        pet["mood"] = transitions.get(current, current)

        if event == "success":
            pet["energy"] = min(100, pet.get("energy", 100) + 5)
        elif event in ("failure", "error"):
            pet["energy"] = max(0, pet.get("energy", 100) - 3)
        if event == "scan":
            pet["scans"] = pet.get("scans", 0) + 1

        pet["age"] = pet.get("age", 0) + 1
        pet["projects_seen"] = pet.get("projects_seen", 0)
        return self._evolve(pet)

    def _evolve(self, pet: dict) -> dict:
        age = pet.get("age", 0)
        stage = "seed"
        for name, limit in STAGE_AGE_LIMITS:
            if age >= limit:
                stage = name
                break
        if pet.get("body_pattern") != stage:
            pet["body_pattern"] = stage
            level = STAGES.get(stage, 0)
            if level > pet.get("evolution_level", 0):
                pet["evolution_level"] = level
            pet["mutations_witnessed"] = min(
                level + pet.get("scans", 0) // 8,
                level * 2 + 1,
            )
        return pet
