from __future__ import annotations

from pathlib import Path

from . import __version__
from .config import ConfigStore
from .journal import Journal
from .logger import SessionLogger
from .pet import Pet
from .state import State


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

    def handle_command(self, raw: str) -> bool:
        raw = raw.strip()
        if not raw:
            return True

        self.session_logger.write("COMMAND", raw)

        text = raw[1:] if raw.startswith("/") else raw
        parts = text.split()
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