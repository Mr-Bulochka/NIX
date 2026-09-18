from __future__ import annotations

from pathlib import Path

from . import __version__
from .brain import Brain
from .config import ConfigStore
from .modules.loader import all_modules, set_enabled_modules
from .journal import Journal
from .logger import SessionLogger
from .pet import Pet
from .state import State, utc_now_ts

PILL_COOLDOWN = 30 * 60


def _tokenize_nix(text: str) -> list[tuple[str, str]]:
    """Split a command line into args and chain separators.

    Whitespace separates arguments; a matching pair of single or double
    quotes groups a value (the quotes themselves are dropped); outside
    quotes, ``;`` or ``&&`` splits the line into separate commands.
    Returns ``("arg", value)`` and ``("sep", ";")`` / ``("sep", "&&")``
    items in order.
    """
    items: list[tuple[str, str]] = []
    buf: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in ("'", '"'):
            if buf:
                items.append(("arg", "".join(buf)))
                buf = []
            quote = c
            i += 1
            value: list[str] = []
            while i < n and text[i] != quote:
                value.append(text[i])
                i += 1
            i += 1
            items.append(("arg", "".join(value)))
            continue
        if c == ";":
            if buf:
                items.append(("arg", "".join(buf)))
                buf = []
            items.append(("sep", ";"))
            i += 1
            continue
        if c == "&" and i + 1 < n and text[i + 1] == "&":
            if buf:
                items.append(("arg", "".join(buf)))
                buf = []
            items.append(("sep", "&&"))
            i += 2
            continue
        if c.isspace():
            if buf:
                items.append(("arg", "".join(buf)))
                buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    if buf:
        items.append(("arg", "".join(buf)))
    return items


class NixApp:
    version = __version__

    def __init__(self) -> None:
        self.root = Path.cwd().resolve()
        self.state = State(self.root)
        self.state.initialize()

        self.config_store = ConfigStore(self.state.nix)
        self.config = self.config_store.load()
        set_enabled_modules(self.config.enabled_modules)

        self.session_logger = SessionLogger(self.state.nix)
        self.journal = Journal(self.state.nix)

        self.pet_store = Pet(self.state.nix)
        self.pet = self.pet_store.load()

        self.brain = Brain(self.state.nix, self.root)

    def run(self) -> None:
        from .ui import NixUI
        self.ui = NixUI(self)
        self.ui.run()

    def apply_module_settings(self) -> None:
        """Re-apply the enabled-modules set from config and refresh the
        brain's module map (settings may have changed at runtime)."""
        set_enabled_modules(self.config.enabled_modules)
        self.brain.modules = {m.id: m for m in all_modules()}

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
        chunks: list[list[str]] = []
        cur: list[str] = []
        for kind, value in _tokenize_nix(text):
            if kind == "arg":
                cur.append(value)
            elif cur:
                chunks.append(cur)
                cur = []
        if cur:
            chunks.append(cur)
        continue_session = True
        for chunk in chunks:
            if not chunk:
                continue
            if not self._handle_command_args(chunk):
                continue_session = False
                break
        return continue_session

    def _handle_command_args(self, args: list[str]) -> bool:
        if not args:
            return True

        name = args[0].lower()
        rest = args[1:]

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
            result = cmd.handler(self, rest)
        except Exception as exc:
            self.ui.show_message("ERROR", self.t("fb.failed", name=name, exc=exc))
            self.session_logger.write("ERROR", f"/{name} failed: {exc}")
            return True

        if result.message:
            self.ui.show_message("SYSTEM", result.message)
        return result.continue_session