from __future__ import annotations

from pathlib import Path

from . import __version__
from .config import ConfigStore
from .journal import Journal
from .logger import SessionLogger
from .pet import Pet
from .state import State
from .ui import NixUI


class NixApp:
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

        self.ui = NixUI()

    def run(self) -> None:
        from .commands import get_command

        if self.pet is None:
            name = self.ui.show_first_launch()
            self.pet = self.pet_store.create(name)
            self.journal.write("SYSTEM", f"pet created: {name}")
            self.session_logger.write("SYSTEM", f"pet created: {name}")

        self.session_logger.write("SYSTEM",
                                   f"session started root={self.root}")
        self.journal.write("SYSTEM", f"session started root={self.root}")

        self._draw()

        while True:
            try:
                raw = self.ui.get_input()
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if not raw:
                continue

            if not raw.startswith("/"):
                self.ui.show_message("SYSTEM",
                                      "Commands must start with '/'. Type /help.")
                continue

            parts = raw[1:].split()
            if not parts:
                continue

            cmd_name = parts[0].lower()
            args = parts[1:]

            if cmd_name in ("quit", "exit"):
                self.journal.write("SYSTEM", "session ended by user")
                self.session_logger.write("SYSTEM", "session ended by user")
                break

            cmd = get_command(cmd_name)
            if cmd is None:
                self.ui.show_message("ERROR",
                                      f"Unknown command: /{cmd_name}. Type /help.")
                continue

            result = cmd.handler(self, args)

            self.session_logger.write("COMMAND", raw)

            if result.clear_screen:
                self._draw()
            elif result.message:
                self.ui.show_message("SYSTEM", result.message)

            if not result.continue_session:
                break

    def _draw(self) -> None:
        project_name = self.root.name or str(self.root)
        events = self.session_logger.read_last(15)
        self.ui.draw_full(
            project_name=project_name,
            pet=self.pet,
            config=self.config,
            events=events,
        )
