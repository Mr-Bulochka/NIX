from __future__ import annotations

import re
from pathlib import Path

from . import __version__
from .config import ConfigStore
from .journal import Journal
from .logger import SessionLogger
from .pet import Pet
from .state import State, utc_now_ts

PILL_COOLDOWN = 30 * 60


class NixApp:
    version = __version__

    def __init__(self) -> None:
        self.root = Path.cwd().resolve()
        self.state = State(self.root)
        self.state.initialize()

        self.config_store = ConfigStore(self.state.nix)
        self.config = self.config_store.load()

        self.session_logger = SessionLogger(self.state.nix)
        self.journal = Journal(self.state.nix)

        self.pet_store = Pet(self.state.nix)
        self.pet = self.pet_store.load()

    def run(self) -> None:
        from .ui import NixUI
        self.ui = NixUI(self)
        self.ui.run()

    def t(self, key: str, **kwargs) -> str:
        return self.config.t(key, **kwargs)

    def pill_remaining(self) -> float | None:
        pet = self.pet
        if pet is None:
            return None
        last = pet.get("last_pill_at") or 0
        return max(0.0, PILL_COOLDOWN - (utc_now_ts() - last))

    def give_pill(self) -> tuple[bool, str]:
        pet = self.pet
        if pet is None:
            return False, self.t("pet.no_pet")
        remaining = self.pill_remaining()
        if remaining and remaining > 0:
            minutes = int(remaining // 60) + (1 if remaining % 60 else 0)
            return False, self.t("fb.pill_cooldown", min=minutes)
        from .avatar import choose_skin
        new_skin = choose_skin(not_kind=pet.get("skin"))
        pet["skin"] = new_skin
        pet["last_pill_at"] = utc_now_ts()
        self.pet_store.save(pet)
        self.journal.write("PET", f"pill given: skin={new_skin}")
        try:
            if getattr(self, "ui", None):
                self.ui._refresh_pet()
        except Exception:
            pass
        return True, self.t("fb.pill_given", skin=self.t(f"skin.{new_skin}"))

    def handle_command(self, raw: str) -> bool:
        raw = raw.strip()
        if not raw:
            return True

        self.session_logger.write("COMMAND", raw)

        text = raw[1:] if raw.startswith("/") else raw
        parts_seq = [p for p in re.split(r"\s*(?:;|&&)\s*", text)]
        continue_session = True
        for expr in parts_seq:
            if not expr.strip():
                continue
            if not self._handle_command_single(expr.strip()):
                continue_session = False
                break
        return continue_session

    def _handle_command_single(self, raw: str) -> bool:
        parts = raw.split()
        if not parts:
            return True

        name = parts[0].lower()
        args = parts[1:]

        if name in ("quit", "exit"):
            self.session_logger.write("SYSTEM", "session ended by user")
            self.journal.write("SYSTEM", "session ended by user")
            return False

        from .commands import get_command

        cmd = get_command(name)
        if cmd is None:
            self.ui.show_message("ERROR", self.t("fb.unknown", name=name))
            return True

        try:
            result = cmd.handler(self, args)
        except Exception as exc:
            self.ui.show_message("ERROR", self.t("fb.failed", name=name, exc=exc))
            self.session_logger.write("ERROR", f"/{name} failed: {exc}")
            return True

        if result.message:
            self.ui.show_message("SYSTEM", result.message)
        return result.continue_session