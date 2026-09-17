from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .i18n import DEFAULT_LANGUAGE, LANGUAGES

VALID_MODES = ("local", "safe", "git")


@dataclass
class Config:
    theme: str = "green"
    mode: str = "local"
    language: str = DEFAULT_LANGUAGE
    attempts: int = 0
    max_attempts: int = 100
    mutation_budget: int = 10
    tamagotchi_enabled: bool = True
    animations_enabled: bool = True
    sounds_enabled: bool = False
    avatar_enabled: bool = True
    auto_scan: bool = True
    checkpoint_on_mutate: bool = True
    git_auto_commit: bool = False
    protected_paths: list[str] | None = None

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            self.mode = "local"
        if self.language not in LANGUAGES:
            self.language = DEFAULT_LANGUAGE
        if self.protected_paths is None:
            self.protected_paths = ["pyproject.toml", "setup.cfg", "Cargo.toml",
                                     "package.json", ".env"]
        self.attempts = max(0, min(self.attempts, self.max_attempts))
        self.mutation_budget = max(0, self.mutation_budget)

    def t(self, key: str, **kwargs) -> str:
        from .i18n import t as translate
        return translate(self.language, key, **kwargs)


class ConfigStore:
    def __init__(self, nix_dir: Path) -> None:
        self.path = nix_dir / "config.json"

    def load(self) -> Config:
        if not self.path.exists():
            return Config()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            known = {f.name for f in fields(Config)}
            filtered = {k: v for k, v in raw.items() if k in known}
            return Config(**filtered)
        except (OSError, json.JSONDecodeError, TypeError, KeyError, ValueError):
            return Config()

    def save(self, config: Config) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(config)
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
