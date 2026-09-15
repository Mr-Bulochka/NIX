from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button, Footer, Header, Input, Label, RichLog, Select, Static, Switch,
)

from .avatar import render as render_avatar
from .i18n import LANGUAGES, t as _t

MODES = ("local", "safe", "git")

if TYPE_CHECKING:
    from .app import NixApp
    from .config import Config
    from .scanner import ProjectInfo

BG = "#050505"
BLACK = "#000000"
PANEL = "#0b0b0d"
RAISED = "#121214"
BORDER = "#26262b"
FG = "#c7ccd4"
DIM = "#6b7280"
BLUE = "#69a9e8"
CYAN = "#85d3f5"
GREEN = "#7fb572"
RED = "#e06c75"
YELLOW = "#d4a35c"
PURPLE = "#a78bd6"
PINK = "#ee8fa8"

SPINNER = ["\u25d0", "\u25d3", "\u25d1", "\u25d2"]


MOOD_STYLES = {
    "curious": YELLOW,
    "happy": GREEN,
    "content": GREEN,
    "focused": BLUE,
    "alert": YELLOW,
    "determined": PURPLE,
    "thoughtful": CYAN,
    "cautious": YELLOW,
    "worried": RED,
    "relieved": GREEN,
    "tired": DIM,
    "anxious": RED,
}

KIND_COLORS = {
    "SYSTEM": DIM,
    "SCAN": CYAN,
    "PET": PURPLE,
    "ERROR": RED,
    "WARN": YELLOW,
    "MUTATION": YELLOW,
    "TEST": YELLOW,
    "LEARN": GREEN,
    "CHECKPOINT": BLUE,
}

APP_CSS = f"""
Screen {{
    align: center middle;
    background: {BLACK};
}}

#app {{
    width: 100%;
    max-width: 150;
    height: 100%;
    background: {BG};
}}

#top {{
    height: auto;
    margin: 1 2 0 2;
    align: center middle;
    background: {BG};
}}

#pet-wrap {{
    width: auto;
    height: auto;
    align: center middle;
    padding: 0 1;
}}

#pet-box {{
    width: auto;
    height: auto;
}}

#pet-name-label {{
    content-align: center middle;
    color: {FG};
    text-style: bold;
    margin-top: 0;
}}

#pet-stats {{
    width: auto;
    height: auto;
    padding: 1 1;
    margin-left: 2;
    border: round {BORDER};
    background: {PANEL};
}}

#pet-stats .stat {{
    height: 1;
    width: auto;
}}

#logwrap {{
    height: 1fr;
    margin: 1 2 0 2;
}}

#log {{
    background: {BLACK};
    border: round {BORDER};
    padding: 0 1;
}}

#toolbar {{
    height: 1;
    margin: 1 2 0 2;
    align: center middle;
    background: {BLACK};
}}

#toolbar Button {{
    background: {BLACK};
    color: {DIM};
    border: none;
    padding: 0 1;
    min-width: 0;
    min-height: 1;
    height: 1;
    margin: 0;
}}

#toolbar Button:hover {{
    color: {BLUE};
    text-style: bold;
}}

#toolbar Button:focus {{
    color: {BLUE};
    background: {RAISED};
}}

#cmd {{
    dock: bottom;
    height: 3;
    margin: 0 2 1 2;
    padding: 0 1;
    border: round {BORDER};
    background: {PANEL};
    color: {FG};
}}

#cmd:focus {{
    border: round {BLUE};
}}

Footer {{
    background: {BLACK};
    color: {DIM};
}}

Footer > .footer--key {{
    color: {BLUE};
}}

Header {{
    background: {BLACK};
    color: {FG};
}}

Header .header--title {{
    color: {FG};
}}

Header .header--clock {{
    color: {DIM};
}}

Scrollbar {{
    background: {BLACK};
    color: {BORDER};
}}

Scrollbar:hover {{
    background: {BLACK};
    color: {BLUE};
}}

.Selection {{
    background: {RAISED};
    color: {BLUE};
}}

#top-scrollbar-hack {{ }}
"""


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


class FirstLaunchScreen(ModalScreen[dict]):
    CSS = f"""
    #first-launch {{
        width: 78;
        max-width: 100%;
        height: auto;
        max-height: 95%;
        padding: 1 2;
        align: center middle;
        border: round {BORDER};
        background: {PANEL};
        scrollbar-size-vertical: 1;
        scrollbar-color: {DIM} {BLACK};
    }}

    #first-launch .title {{
        content-align: center middle;
        text-style: bold;
        color: {FG};
        text-align: center;
        margin: 0 0 1 0;
    }}

    #first-launch .hint {{
        content-align: center middle;
        color: {DIM};
        text-align: center;
    }}

    #first-launch .flabel {{
        height: 1;
        margin: 1 0 0 0;
        content-align: left middle;
        color: {CYAN};
    }}

    #fl-select {{
        margin: 0 0 1 0;
        border: round {BORDER};
        background: {BLACK};
        color: {FG};
    }}

    #fl-select:focus {{
        border: round {BLUE};
    }}

    #pet-name {{
        margin: 0 0 1 0;
        border: round {BORDER};
        background: {BLACK};
        color: {FG};
    }}

    #pet-name:focus {{
        border: round {BLUE};
    }}

    #ok-btn {{
        margin: 1 0 0 0;
        background: {RAISED};
        color: {FG};
        border: round {BORDER};
    }}

    #ok-btn:focus {{
        border: round {BLUE};
    }}
    """

    def __init__(self, initial_lang: str = "en") -> None:
        super().__init__()
        self._lang = initial_lang

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="first-launch"):
            yield Label("", id="fl-title", classes="title")
            yield Label("", id="fl-hint1", classes="hint")
            yield Label("", id="fl-hint2", classes="hint")
            yield Label("", id="fl-lang-label", classes="flabel")
            yield Select(
                [("English", "en"), ("Русский", "ru")],
                value=self._lang,
                allow_blank=False,
                id="fl-select",
            )
            yield Label("", id="fl-name-label", classes="flabel")
            yield Input(placeholder="", id="pet-name")
            yield Button("", id="ok-btn", variant="primary")

    def on_mount(self) -> None:
        self._apply_lang()
        self.query_one("#pet-name", Input).focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        self._lang = event.value
        self._apply_lang()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            self._submit(self.query_one("#pet-name", Input).value)

    def _apply_lang(self) -> None:
        self.query_one("#fl-title", Label).update(_t(self._lang, "fl.title"))
        self.query_one("#fl-hint1", Label).update(_t(self._lang, "fl.hint1"))
        self.query_one("#fl-hint2", Label).update(_t(self._lang, "fl.hint2"))
        self.query_one("#fl-lang-label", Label).update(_t(self._lang, "fl.language"))
        self.query_one("#fl-name-label", Label).update(_t(self._lang, "fl.choose_name"))
        self.query_one("#pet-name", Input).placeholder = _t(
            self._lang, "fl.name_placeholder"
        )
        self.query_one("#ok-btn", Button).label = _t(self._lang, "fl.create")

    def _submit(self, raw: str) -> None:
        name = raw.strip()
        if not name:
            self.notify(_t(self._lang, "fl.empty_name"), severity="error")
            return
        self.dismiss({"name": name, "language": self._lang})


class SettingsModal(ModalScreen[None]):
    BINDINGS = [
        Binding("escape", "save_and_close", "Close", priority=True),
        Binding("ctrl+q", "save_and_close", "", priority=True),
    ]

    TOGGLE_KEYS = {
        "set-tamagotchi": "tamagotchi_enabled",
        "set-animations": "animations_enabled",
        "set-avatar": "avatar_enabled",
        "set-sounds": "sounds_enabled",
        "set-auto-scan": "auto_scan",
        "set-checkpoint": "checkpoint_on_mutate",
        "set-git": "git_auto_commit",
    }

    CSS = f"""
    SettingsModal {{
        align: center middle;
    }}

    #set-frame {{
        width: 88%;
        max-width: 84;
        height: 88%;
        max-height: 46;
        border: round {BORDER};
        background: {PANEL};
        padding: 0 1;
    }}

    #set-title {{
        height: 1;
        margin: 1 0 0 0;
        color: {BLUE};
        text-style: bold;
    }}

    #set-body {{
        height: 1fr;
        overflow-y: auto;
        scrollbar-size-vertical: 1;
        scrollbar-color: {DIM} {BLACK};
    }}

    #set-body .set-row {{
        height: auto;
        margin: 1 0 0 0;
        align: center middle;
    }}

    #set-body .set-label {{
        width: 32;
        color: {FG};
        content-align: left middle;
        padding: 0 1 0 0;
    }}

    #set-body .set-field {{
        width: 1fr;
    }}

    #set-body .set-hint {{
        color: {DIM};
        height: 1;
    }}

    #set-close {{
        dock: bottom;
        width: 100%;
        margin: 1 0 1 0;
        background: {RAISED};
        border: round {BORDER};
        color: {FG};
    }}

    #set-close:hover {{
        border: round {BLUE};
        color: {BLUE};
    }}

    Select {{
        background: {BLACK};
        border: round {BORDER};
    }}

    Select:focus {{
        border: round {BLUE};
    }}

    Input {{
        background: {BLACK};
        border: round {BORDER};
    }}

    Input:focus {{
        border: round {BLUE};
    }}

    Switch {{
        background: {BLACK};
    }}

    Scrollbar {{
        background: {BLACK};
        color: {BORDER};
    }}
    """

    def __init__(self, ui: "NixUI", config: "Config", save) -> None:
        super().__init__()
        self._ui = ui
        self._cfg = config
        self._save = save

    def _t(self, key: str, **kw) -> str:
        return self._ui._t(key, **kw)

    def _row(self, label: str, field) -> Horizontal:
        return Horizontal(
            Label(label, classes="set-label"),
            field,
            classes="set-row",
        )

    def compose(self) -> ComposeResult:
        t = self._t
        cfg = self._cfg
        with Vertical(id="set-frame"):
            yield Label(t("tbl.settings"), id="set-title")
            with VerticalScroll(id="set-body"):
                yield self._row(
                    t("set.language"),
                    Select(
                        [(LANGUAGES[k], k) for k in LANGUAGES],
                        value=cfg.language,
                        id="set-lang",
                    ),
                )
                yield self._row(
                    t("st.mode"),
                    Select(
                        [(t(f"cmd.mode.{m}"), m) for m in MODES],
                        value=cfg.mode,
                        id="set-mode",
                    ),
                )
                yield self._row(
                    t("set.attempts"),
                    Input(str(cfg.attempts), id="set-attempts"),
                )
                yield self._row(
                    t("set.mutation_budget"),
                    Input(str(cfg.mutation_budget), id="set-budget"),
                )
                for wid, key in self.TOGGLE_KEYS.items():
                    yield self._row(
                        t(self._toggle_label(wid)),
                        Switch(getattr(cfg, key), id=wid),
                    )
            yield Button("", id="set-close")

    def _toggle_label(self, wid: str) -> str:
        return self._t({
            "set-tamagotchi": "set.tamagotchi",
            "set-animations": "set.animations",
            "set-avatar": "set.avatar",
            "set-sounds": "set.sounds",
            "set-auto-scan": "set.auto_scan",
            "set-checkpoint": "set.checkpoint",
            "set-git": "set.git",
        }[wid])

    def on_mount(self) -> None:
        self.query_one("#set-close", Button).label = self._t("modal.close")

    def _persist(self, message: str) -> None:
        self._save(self._cfg)
        self._ui._refresh_pet()
        if message:
            self.notify(message, severity="information", timeout=2)

    def on_select_changed(self, event) -> None:
        wid = getattr(event.select, "id", "")
        if wid == "set-lang":
            self._cfg.language = event.value
            self._persist(self._t("set.saved"))
        elif wid == "set-mode":
            self._cfg.mode = event.value
            self._persist(self._t("set.saved"))
        self._ui._refresh_header()

    def on_input_submitted(self, event) -> None:
        wid = getattr(event.input, "id", "")
        raw = event.value.strip()
        try:
            val = int(raw)
        except ValueError:
            self.notify(self._t("fb.attempts_invalid"), severity="error")
            return
        if wid == "set-attempts":
            self._cfg.attempts = max(0, min(val, self._cfg.max_attempts))
        elif wid == "set-budget":
            self._cfg.mutation_budget = max(0, val)
        self._persist(self._t("set.saved"))

    def on_switch_changed(self, event) -> None:
        key = self.TOGGLE_KEYS.get(getattr(event.switch, "id", ""))
        if key:
            setattr(self._cfg, key, event.value)
            self._persist(self._t("set.saved"))

    def action_save_and_close(self) -> None:
        self._save(self._cfg)
        self._ui._refresh_pet()
        self._ui._refresh_header()
        self.dismiss(None)


class NixUI(App):
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear_log", "Clear", priority=True),
        Binding("ctrl+s", "run_scan", "Scan", priority=True),
        Binding("ctrl+p", "run_pet", "Pet", priority=True),
        Binding("pageup", "page_up", "Page up", priority=True),
        Binding("pagedown", "page_down", "Page down", priority=True),
    ]

    CSS = APP_CSS

    def __init__(self, nix: "NixApp") -> None:
        super().__init__()
        self.nix = nix
        self._spin = 0
        self._blink = 0

    # ----- lifecycle -------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="app"):
            yield Header(show_clock=True)
            with Horizontal(id="top"):
                with Vertical(id="pet-wrap"):
                    yield Static("", id="pet-box")
                    yield Label("", id="top-pet-name")
                with Vertical(id="pet-stats"):
                    yield Label("", id="st-mood", classes="stat")
                    yield Label("", id="st-energy", classes="stat")
                    yield Label("", id="st-stage", classes="stat")
            with VerticalScroll(id="logwrap"):
                yield RichLog(id="log", wrap=True, markup=True,
                              highlight=True, auto_scroll=True)
            with Horizontal(id="toolbar"):
                yield Button("", id="btn-help")
                yield Button("", id="btn-pet")
                yield Button("", id="btn-scan")
                yield Button("", id="btn-status")
                yield Button("", id="btn-settings")
                yield Button("", id="btn-quit")
            yield Input(id="cmd", placeholder="")
            yield Footer()

    def on_mount(self) -> None:
        self._apply_language()
        if self.nix.pet is None:
            self.push_screen(
                FirstLaunchScreen(self.nix.config.language),
                callback=self._on_pet_ready,
            )
        else:
            self._refresh_pet()
            self._write_session_start()
            self.query_one("#cmd", Input).focus()
        self.set_interval(1.0, self._tick)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        if not raw:
            return
        if not self.nix.handle_command(raw):
            self.exit(0)
        self._refresh_header()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {
            "btn-scan": "/scan",
            "btn-status": "/status",
            "btn-pet": "/pet",
            "btn-settings": "/settings",
            "btn-help": "/help",
            "btn-quit": "/quit",
        }
        action = mapping.get(event.button.id)
        if not action:
            return
        if not self.nix.handle_command(action):
            self.exit(0)
        self._refresh_header()

    # ----- actions ---------------------------------------------------

    def action_quit(self) -> None:
        self.exit(0)

    def action_clear_log(self) -> None:
        self._log().clear()

    def action_run_scan(self) -> None:
        self.nix.handle_command("/scan")
        self._refresh_header()

    def action_run_pet(self) -> None:
        self.nix.handle_command("/pet")

    # ----- internal --------------------------------------------------

    def _log(self) -> RichLog:
        return self.query_one("#log", RichLog)

    def _t(self, key: str, **kw) -> str:
        return self.nix.config.t(key, **kw)

    def _apply_language(self) -> None:
        cfg = self.nix.config
        self.query_one("#btn-scan", Button).label = self._t("btn.scan")
        self.query_one("#btn-status", Button).label = self._t("btn.status")
        self.query_one("#btn-pet", Button).label = self._t("btn.pet")
        self.query_one("#btn-settings", Button).label = self._t("btn.settings")
        self.query_one("#btn-help", Button).label = self._t("btn.help")
        self.query_one("#btn-quit", Button).label = self._t("btn.quit")
        self.query_one("#cmd", Input).placeholder = self._t("cmd.placeholder")
        self._refresh_header()

    def _refresh_header(self) -> None:
        cfg = self.nix.config
        name = self.nix.root.name or str(self.nix.root)
        mode = cfg.t(f"cmd.mode.{cfg.mode}")
        self.title = "NIX"
        self.sub_title = f"{name}  ·  {mode.upper()}  ·  v{self.nix.version}"

    def _write_session_start(self) -> None:
        l = self._t
        self._log().write(
            Text()
            .append(f"{_timestamp()} ", style=DIM)
            .append("SYSTEM ", style=BLUE)
            .append(l("session.started", root=self.nix.root), style=FG)
        )
        self._log().write(
            Text()
            .append(f"{_timestamp()} ", style=DIM)
            .append("SYSTEM ", style=BLUE)
            .append(l("session.foundation"), style=FG)
        )
        self._log().write(
            Text()
            .append(f"{_timestamp()} ", style=DIM)
            .append("SYSTEM ", style=BLUE)
            .append(l("session.hint"), style=FG)
        )

    def _on_pet_ready(self, result: dict) -> None:
        self.nix.config.language = result["language"]
        self.nix.config_store.save(self.nix.config)
        self._apply_language()
        self.nix.pet = self.nix.pet_store.create(result["name"])
        lang = self.nix.config.language
        self.nix.journal.write("SYSTEM", f"pet created: {result['name']}")
        self.nix.session_logger.write("SYSTEM", f"pet created: {result['name']}")
        self.notify(_t(lang, "welcome_back", name=result["name"]),
                    severity="information")
        self._write_session_start()
        self._refresh_pet()
        self.query_one("#cmd", Input).focus()

    def _tick(self) -> None:
        self._spin = (self._spin + 1) % len(SPINNER)
        if self.nix.config.animations_enabled:
            self._blink = (self._blink + 1) % 4
            self._refresh_pet(animate=True)

    def _refresh_pet(self, animate: bool = False) -> None:
        pet = self.nix.pet or {}
        box = self.query_one("#pet-box", Static)
        name_label = self.query_one("#top-pet-name", Label)
        if not pet:
            box.update(Text(self._t("pet.no_pet"), style=DIM))
            name_label.update("")
            self._set_stat("#st-mood", "", DIM)
            self._set_stat("#st-energy", "", DIM)
            self._set_stat("#st-stage", "", DIM)
            return

        pattern = pet.get("body_pattern", "seed")
        pattern_label = self._t(f"pet.pattern.{pattern}")
        blink = animate and self._blink == 1
        art = render_avatar(pet, self.nix.root, scale=1, blink=blink)
        name = pet.get("name", "???")
        mood = pet.get("mood", "curious")
        mood_style = MOOD_STYLES.get(mood, FG)
        mood_label = self._t(f"mood.{mood}")
        energy = int(pet.get("energy", 100))
        age = int(pet.get("age", 0))

        name_label.update(name)

        self._set_stat("#st-mood",
                       f"{self._t('pet.mood')}: [{mood_style}]{mood_label}[/]",
                       mood_style)
        bar = self._energy_bar(energy)
        self._set_stat(
            "#st-energy",
            f"{self._t('pet.energy')}: {bar} {energy}%",
            FG,
        )
        self._set_stat(
            "#st-stage",
            f"{self._t('pet.stage')}: {pattern_label}  \u00b7  "
            f"{self._t('pet.age')} {age}",
            DIM,
        )
        box.update(art)

    def _energy_bar(self, energy: int) -> str:
        filled = round(energy / 100 * 10)
        color = GREEN if energy >= 50 else (YELLOW if energy >= 25 else RED)
        return ("\u2588" * filled + "\u2591" * (10 - filled)).replace(
            "\u2588", f"[{color}]\u2588[/]"
        )

    def _set_stat(self, query: str, text: str, color: str) -> None:
        try:
            label = self.query_one(query, Label)
            label.update(Text.from_markup(text, style=color))
        except Exception:
            pass

    # ----- public API (used by commands) -----------------------------

    def show_message(self, kind: str, text: str) -> None:
        color = KIND_COLORS.get(kind.upper(), FG)
        self._log().write(
            Text()
            .append(f"{_timestamp()} ", style=DIM)
            .append(f"{kind.upper():>10} ", style=color)
            .append(text, style=FG)
        )

    def show_help(self, lines: list[str]) -> None:
        t = self._t
        log = self._log()
        log.write(Text(f"  {t('tbl.commands').upper()}", style=f"bold {BLUE}"))
        body = Text()
        for line in lines:
            parts = line.strip().split(None, 1)
            name = parts[0] if parts else line.strip()
            desc = parts[1] if len(parts) == 2 else ""
            body.append(f"    {name:<18}", style=GREEN)
            body.append(desc + "\n", style=FG)
        log.write(body)

    def show_status(self, *, root: str, mode: str, attempts: int,
                    max_attempts: int, files: int, dirs: int,
                    functions: int, classes: int,
                    source_files: int, total_lines: int) -> None:
        t = self._t
        text = Text(f"  {t('tbl.project_status').upper()}\n",
                    style=f"bold {BLUE}")
        fields = [
            (t("st.root"), root, FG),
            (t("st.mode"), mode.upper(), BLUE),
            (t("st.attempts"), f"{attempts}/{max_attempts}", FG),
            (t("st.files"), str(files), GREEN),
            (t("st.dirs"), str(dirs), GREEN),
            (t("st.source"), str(source_files), GREEN),
            (t("st.functions"), str(functions), GREEN),
            (t("st.classes"), str(classes), GREEN),
            (t("st.lines"), f"{total_lines:,}", GREEN),
        ]
        for label, value, color in fields:
            text.append(f"    {label:<20}", style=CYAN)
            text.append(value + "\n", style=color)
        self._log().write(text)

    def show_scan(self, info: "ProjectInfo") -> None:
        t = self._t
        log = self._log()
        head = Text()
        head.append(f"{info.files} {t('scan.files')}  ", style=CYAN)
        head.append(f"{info.directories} {t('scan.dirs')}  ", style=CYAN)
        head.append(f"{info.functions} {t('scan.functions')}  ", style=CYAN)
        head.append(f"{info.classes} {t('scan.classes')}  ", style=CYAN)
        head.append(f"{info.total_lines:,} {t('scan.lines')}", style=CYAN)
        log.write(head)
        if info.extensions:
            log.write(Text(f"  {t('tbl.extensions').upper()}",
                           style=f"bold {PURPLE}"))
            body = Text()
            for ext, count in info.top_extensions:
                body.append(f"    {ext:<14}", style=FG)
                body.append(str(count) + "\n", style=GREEN)
            log.write(body)

    def show_pet(self, pet: dict) -> None:
        t = self._t
        mood = pet.get("mood", "curious")
        mood_label = t(f"mood.{mood}")
        mood_style = MOOD_STYLES.get(mood, FG)
        pattern = pet.get("body_pattern", "seed")
        art = render_avatar(pet, self.nix.root, scale=2,
                            blink=self._blink == 1)
        text = Text()
        rows = [
            (t("pet.name"), pet.get("name", "???"), FG),
            (t("pet.mood"), mood_label, mood_style),
            (t("pet.energy"), str(pet.get("energy", 100)), GREEN),
            (t("pet.age"), str(pet.get("age", 0)), FG),
            (t("pet.body"), t(f"pet.pattern.{pattern}"), PURPLE),
            (t("pet.stage"), str(pet.get("stage", 1)), FG),
            (t("pet.mutations"), str(pet.get("mutations_witnessed", 0)), YELLOW),
            (t("pet.failures"), str(pet.get("failures_survived", 0)), RED),
            (t("pet.scans"), str(pet.get("scans", 0)), CYAN),
        ]
        for label, value, color in rows:
            text.append(f"    {label:<20}", style=CYAN)
            text.append(value + "\n", style=color)
        log = self._log()
        log.write(art)
        log.write(text)

    def show_settings(self, config: "Config") -> None:
        self.push_screen(
            SettingsModal(self, config, self.nix.config_store.save)
        )

    def show_logs(self, path: object, lines: list[str]) -> None:
        t = self._t
        log = self._log()
        if not lines:
            log.write(Text(self._t("fb.no_logs"), style=DIM))
            return
        log.write(Text(f"  {t('tbl.session_log').upper()}  {path}",
                       style=f"bold {DIM}"))
        body = Text()
        for line in lines[-40:]:
            body.append("    " + line + "\n", style=DIM)
        log.write(body)

    def show_history(self, entries: list[dict]) -> None:
        t = self._t
        log = self._log()
        if not entries:
            log.write(Text(self._t("fb.no_history"), style=DIM))
            return
        log.write(Text(f"  {t('tbl.journal').upper()}",
                       style=f"bold {BLUE}"))
        kind_colors = {
            "SYSTEM": DIM, "SCAN": CYAN, "PET": PURPLE, "ERROR": RED,
        }
        body = Text()
        for entry in entries[-40:]:
            kind = entry.get("kind", "")
            body.append("    ", style=DIM)
            body.append(f"{entry.get('ts', ''):<12} ", style=DIM)
            body.append(f"{kind:<8}", style=kind_colors.get(kind, FG))
            body.append(entry.get("message", "") + "\n", style=FG)
        log.write(body)

    def show_error(self, text: str) -> None:
        self.show_message("ERROR", text)

    def clear_log(self) -> None:
        self._log().clear()