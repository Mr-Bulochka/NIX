from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .i18n import DEFAULT_LANGUAGE, LANGUAGES

VALID_MODES = ("local", "safe", "git")


def _as_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
    return default


def _as_int(value: object, default: int, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        try:
            value = int(str(value).strip())
        except (TypeError, ValueError):
            return default
    return max(low, min(int(value), high))


def _as_float(value: object, default: float, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        try:
            value = float(str(value).strip())
        except (TypeError, ValueError):
            return default
    return max(low, min(float(value), high))


_PATH_SPLIT = re.compile(r"[,;\n]+")


def parse_path_list(value: object) -> list[str] | None:
    """Normalise a user supplied path list.

    Accepts a list, a single string or ``None``. Strings are split on comma,
    semicolon and newline separators. Entries are trimmed, empty values are
    dropped and duplicates are removed while preserving order.
    """
    if value is None:
        return None
    if isinstance(value, str):
        raw: list[object] = _PATH_SPLIT.split(value)
    elif isinstance(value, (list, tuple)):
        raw = list(value)
    else:
        raw = [value]
    seen: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        cleaned = item.strip().strip("\"'").replace("\\", "/").rstrip("/")
        if not cleaned or cleaned == ".":
            continue
        while cleaned.startswith("./"):
            cleaned = cleaned[2:]
        if not cleaned:
            continue
        if cleaned not in seen:
            seen.append(cleaned)
    return seen


DEFAULT_PROTECTED_PATHS = [
    "pyproject.toml",
    "setup.cfg",
    "Cargo.toml",
    "package.json",
    ".env",
]


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
    enabled_modules: list[str] | None = None
    priority_lang: str = ""
    show_clock: bool = True
    log_max_lines: int = 500
    animation_interval: float = 1.0
    command_history_size: int = 50
    pill_cooldown_minutes: int = 30
    default_command_timeout: int = 120
    autocomplete_enabled: bool = True
    autocomplete_max_items: int = 8
    autocomplete_case_insensitive: bool = True
    autocomplete_min_chars: int = 1
    autocomplete_show_descriptions: bool = True

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            self.mode = "local"
        if self.language not in LANGUAGES:
            self.language = DEFAULT_LANGUAGE
        normalized_paths = parse_path_list(self.protected_paths)
        if normalized_paths is None:
            normalized_paths = list(DEFAULT_PROTECTED_PATHS)
        self.protected_paths = normalized_paths
        if self.enabled_modules is not None:
            if not isinstance(self.enabled_modules, list):
                self.enabled_modules = None
            else:
                seen: list[str] = []
                for item in self.enabled_modules:
                    if (isinstance(item, str)
                            and re.fullmatch(r"[A-Za-z0-9_\-]+", item)
                            and item not in seen):
                        seen.append(item)
                self.enabled_modules = seen
        if not isinstance(self.priority_lang, str) or not re.fullmatch(
                r"[A-Za-z0-9_\-]+", self.priority_lang):
            self.priority_lang = ""
        self.attempts = max(0, min(self.attempts, self.max_attempts))
        self.mutation_budget = max(0, self.mutation_budget)
        self.tamagotchi_enabled = _as_bool(self.tamagotchi_enabled, True)
        self.animations_enabled = _as_bool(self.animations_enabled, True)
        self.sounds_enabled = _as_bool(self.sounds_enabled, False)
        self.avatar_enabled = _as_bool(self.avatar_enabled, True)
        self.auto_scan = _as_bool(self.auto_scan, True)
        self.checkpoint_on_mutate = _as_bool(self.checkpoint_on_mutate, True)
        self.git_auto_commit = _as_bool(self.git_auto_commit, False)
        self.show_clock = _as_bool(self.show_clock, True)
        self.log_max_lines = _as_int(self.log_max_lines, 500, 50, 5000)
        self.animation_interval = _as_float(
            self.animation_interval, 1.0, 0.1, 10.0)
        self.command_history_size = _as_int(
            self.command_history_size, 50, 0, 500)
        self.pill_cooldown_minutes = _as_int(
            self.pill_cooldown_minutes, 30, 0, 1440)
        self.default_command_timeout = _as_int(
            self.default_command_timeout, 120, 5, 3600)
        self.autocomplete_enabled = _as_bool(self.autocomplete_enabled, True)
        self.autocomplete_case_insensitive = _as_bool(
            self.autocomplete_case_insensitive, True)
        self.autocomplete_show_descriptions = _as_bool(
            self.autocomplete_show_descriptions, True)
        self.autocomplete_max_items = _as_int(
            self.autocomplete_max_items, 8, 1, 50)
        self.autocomplete_min_chars = _as_int(
            self.autocomplete_min_chars, 1, 0, 10)

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
        from .state import atomic_write_text
        atomic_write_text(
            self.path,
            json.dumps(asdict(config), indent=2, ensure_ascii=False),
        )
