from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Select, Static

from .i18n import t as _t

if TYPE_CHECKING:
    from .app import NixApp
    from .config import Config
    from .scanner import ProjectInfo

BG = "#1a1b26"
SURFACE = "#16161e"
FG = "#c0caf5"
BLUE = "#7aa2f7"
CYAN = "#7dcfff"
PURPLE = "#bb9af7"
GREEN = "#9ece6a"
RED = "#f7768e"
YELLOW = "#e0af68"
DIM = "#565f89"
ORANGE = "#ff9e64"

SPINNER = ["\u25d0", "\u25d3", "\u25d1", "\u25d2"]

PET_FRAMES = {
    "seed": (
        "   \u256d\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u256e\n"
        "   \u2502  .  .  \u2502\n"
        "   \u2502   \u25aa    \u2502\n"
        "   \u2570\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u256f\n"
        "      \u2502  \u2502"
    ),
    "sprout": (
        "   \u256d\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u256e\n"
        "   \u2502  \u25c9  \u25c9  \u2502\n"
        "   \u2502   \u25a3    \u2502\n"
        "   \u2570\u2550\u2550\u2550\u252c\u252c\u2550\u2550\u2550\u256f\n"
        "       \u2502\u2502\n"
        "      \u2571  \u2572"
    ),
    "bloom": (
        "   \u256d\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u256e\n"
        "   \u2502 \u25c9  \u25c9  \u2502\n"
        "   \u2502   \u25c6    \u2502\n"
        "   \u2570\u2550\u2550\u2550\u252c\u252c\u2550\u2550\u2550\u256f\n"
        "     \u2571\u2571\u2502\u2502\u2572\u2572\n"
        "    \u2571   \u2572   \u2572"
    ),
}

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
    "SYSTEM": BLUE,
    "SCAN": CYAN,
    "PET": PURPLE,
    "ERROR": RED,
    "WARN": YELLOW,
    "MUTATION": ORANGE,
    "TEST": YELLOW,
    "LEARN": GREEN,
    "CHECKPOINT": BLUE,
}

APP_CSS = f"""
Screen {{
    align: center middle;
    background: {BG};
}}

#app {{
    width: 100%;
    max-width: 120;
    height: 100%;
    border: round {DIM};
    background: {BG};
}}

#pet-box {{
    height: auto;
    max-height: 12;
    margin: 1 2 0 2;
}}

#actions {{
    height: auto;
    padding: 1 2 0 2;
    align: center middle;
}}

#actions Button {{
    margin: 0 1;
}}

#log {{
    margin: 1 2 0 2;
    padding: 0 1;
    background: {SURFACE};
    border: round {DIM};
}}

#cmd {{
    dock: bottom;
    height: 3;
    margin: 0 2 1 2;
    padding: 0 1;
    border: round {BLUE};
    background: {BG};
    color: {FG};
}}

#cmd:focus {{
    border: round {CYAN};
}}

Footer {{
    background: {SURFACE};
    color: {FG};
}}

Header {{
    background: {SURFACE};
    color: {FG};
}}

#btn-scan {{ background: {CYAN}; color: #16161e; }}
#btn-status {{ background: {BLUE}; color: #16161e; }}
#btn-pet {{ background: {PURPLE}; color: #16161e; }}
#btn-settings {{ background: {GREEN}; color: #16161e; }}
#btn-help {{ background: {YELLOW}; color: #16161e; }}
#btn-clear {{ background: {ORANGE}; color: #16161e; }}
#btn-quit {{ background: {RED}; color: #16161e; }}
"""


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


class FirstLaunchScreen(ModalScreen[dict]):
    CSS = f"""
    #first-launch {{
        width: 66;
        height: auto;
        max-height: 20;
        padding: 2 3;
        align: center middle;
        border: round {PURPLE};
        background: {SURFACE};
    }}

    #first-launch .title {{
        content-align: center middle;
        text-style: bold;
        color: {GREEN};
        text-align: center;
    }}

    #first-launch .hint {{
        content-align: center middle;
        color: {DIM};
        text-align: center;
    }}

    #fl-select {{
        margin: 1 0;
        border: round {PURPLE};
        background: {BG};
        color: {FG};
    }}

    #pet-name {{
        margin: 1 0;
        border: round {BLUE};
        background: {BG};
        color: {FG};
    }}

    #ok-btn {{
        margin: 1 0;
    }}
    """

    def __init__(self, initial_lang: str = "en") -> None:
        super().__init__()
        self._lang = initial_lang

    def compose(self) -> ComposeResult:
        with Vertical(id="first-launch"):
            yield Label("", id="fl-title", classes="title")
            yield Label("", id="fl-hint1", classes="hint")
            yield Label("", id="fl-hint2", classes="hint")
            yield Label("", id="fl-lang-label", classes="hint")
            yield Select(
                [("English", "en"), ("Русский", "ru")],
                value=self._lang,
                allow_blank=False,
                id="fl-select",
            )
            yield Label("", id="fl-name-label", classes="hint")
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


class NixUI(App):
    BINDINGS = [
        Binding("ctrl+q", "quit", ""),
        Binding("ctrl+l", "clear_log", ""),
        Binding("ctrl+s", "run_scan", ""),
        Binding("ctrl+p", "run_pet", ""),
    ]

    CSS = APP_CSS

    def __init__(self, nix: "NixApp") -> None:
        super().__init__()
        self.nix = nix
        self._spin = 0

    # ----- lifecycle -------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="app"):
            yield Header(show_clock=True)
            yield Static("", id="pet-box")
            with Horizontal(id="actions"):
                yield Button("", id="btn-scan")
                yield Button("", id="btn-status")
                yield Button("", id="btn-pet")
                yield Button("", id="btn-settings")
                yield Button("", id="btn-help")
                yield Button("", id="btn-clear")
                yield Button("", id="btn-quit")
            yield RichLog(id="log", wrap=True, markup=True, highlight=True,
                          auto_scroll=True)
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
            "btn-clear": "/clear",
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
        self.query_one("#btn-clear", Button).label = self._t("btn.clear")
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
        self._refresh_pet(animate=True)

    def _refresh_pet(self, animate: bool = False) -> None:
        pet = self.nix.pet or {}
        box = self.query_one("#pet-box", Static)
        if not pet:
            box.update(Text(self._t("pet.no_pet"), style=DIM))
            return

        pattern = pet.get("body_pattern", "seed")
        art = PET_FRAMES.get(pattern, PET_FRAMES["seed"])
        mood = pet.get("mood", "curious")
        mood_style = MOOD_STYLES.get(mood, FG)
        mood_label = self._t(f"mood.{mood}")
        energy = pet.get("energy", 100)
        age = pet.get("age", 0)
        name = pet.get("name", "???")
        spinner = SPINNER[self._spin] if animate else "\u25cf"

        body = Text()
        for i, line in enumerate(art.split("\n")):
            body.append(line + "  ", style=CYAN)
            if i == 0:
                body.append(spinner, style=YELLOW)
            body.append("\n")

        panel = Panel(
            body,
            title=f"[bold {PURPLE}]{name}[/]",
            subtitle=f"{mood_label}  ·  {energy}%  ·  {self._t('pet.age')} {age}",
            border_style=PURPLE,
        )
        box.update(panel)

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
        table = Table(
            title=self._t("tbl.commands"),
            box=None,
            header_style=f"bold {CYAN}",
            expand=True,
        )
        table.add_column(self._t("tbl.command"), style=GREEN, no_wrap=True)
        table.add_column(self._t("tbl.description"), style=FG)
        for line in lines:
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                table.add_row(parts[0], parts[1])
            else:
                table.add_row(line, "")
        self._log().write(table)

    def show_status(self, *, root: str, mode: str, attempts: int,
                    max_attempts: int, files: int, dirs: int,
                    functions: int, classes: int,
                    source_files: int, total_lines: int) -> None:
        t = self._t
        table = Table(
            title=t("tbl.project_status"),
            header_style=f"bold {BLUE}",
            border_style=DIM,
            expand=True,
        )
        table.add_column(t("tbl.key"), style=GREEN)
        table.add_column(t("tbl.value"), style=FG)
        table.add_row(t("st.root"), root)
        table.add_row(t("st.mode"), f"[{BLUE}]{mode.upper()}[/]")
        table.add_row(t("st.attempts"), str(attempts))
        table.add_row(t("st.files"), str(files))
        table.add_row(t("st.dirs"), str(dirs))
        table.add_row(t("st.source"), str(source_files))
        table.add_row(t("st.functions"), str(functions))
        table.add_row(t("st.classes"), str(classes))
        table.add_row(t("st.lines"), f"{total_lines:,}")
        self._log().write(table)

    def show_scan(self, info: "ProjectInfo") -> None:
        t = self._t
        header = Text()
        header.append(f"{info.files} {t('scan.files')}  ", style=CYAN)
        header.append(f"{info.directories} {t('scan.dirs')}  ", style=CYAN)
        header.append(f"{info.functions} {t('scan.functions')}  ", style=CYAN)
        header.append(f"{info.classes} {t('scan.classes')}  ", style=CYAN)
        header.append(f"{info.total_lines:,} {t('scan.lines')}", style=CYAN)
        self._log().write(header)

        if info.extensions:
            table = Table(
                title=t("tbl.extensions"),
                header_style=f"bold {PURPLE}",
                border_style=DIM,
                expand=True,
            )
            table.add_column(t("tbl.extension"), style=FG)
            table.add_column(t("tbl.count"), justify="right", style=GREEN)
            for ext, count in info.top_extensions:
                table.add_row(ext, str(count))
            self._log().write(table)

    def show_pet(self, pet: dict) -> None:
        mood = pet.get("mood", "curious")
        mood_style = MOOD_STYLES.get(mood, FG)
        mood_label = self._t(f"mood.{mood}")
        table = Table(
            title=self._t("tbl.pet", name=pet.get("name", "???")),
            header_style=f"bold {PURPLE}",
            border_style=DIM,
            expand=True,
        )
        table.add_column(self._t("tbl.attribute"), style=CYAN)
        table.add_column(self._t("tbl.value"), style=FG)
        table.add_row(self._t("pet.name"), str(pet.get("name", "???")))
        table.add_row(self._t("pet.mood"), f"[{mood_style}]{mood_label}[/]")
        table.add_row(self._t("pet.energy"), str(pet.get("energy", 100)))
        table.add_row(self._t("pet.age"), str(pet.get("age", 0)))
        table.add_row(self._t("pet.body"), pet.get("body_pattern", "seed"))
        table.add_row(self._t("pet.stage"), str(pet.get("stage", 1)))
        table.add_row(self._t("pet.mutations"),
                      str(pet.get("mutations_witnessed", 0)))
        table.add_row(self._t("pet.failures"),
                      str(pet.get("failures_survived", 0)))
        self._log().write(table)

    def show_settings(self, config: "Config") -> None:
        t = self._t
        on, off = t("on"), t("off")
        table = Table(
            title=t("tbl.settings"),
            header_style=f"bold {GREEN}",
            border_style=DIM,
            expand=True,
        )
        table.add_column(t("tbl.setting"), style=GREEN)
        table.add_column(t("tbl.value"), style=FG)
        table.add_row(t("set.language"), config.language)
        table.add_row(t("set.theme"), config.theme)
        table.add_row(t("st.mode"), config.mode)
        table.add_row(t("set.attempts"),
                      f"{config.attempts}/{config.max_attempts}")
        table.add_row(t("set.mutation_budget"), str(config.mutation_budget))
        table.add_row(t("set.tamagotchi"), on if config.tamagotchi_enabled else off)
        table.add_row(t("set.animations"), on if config.animations_enabled else off)
        table.add_row(t("set.avatar"), on if config.avatar_enabled else off)
        table.add_row(t("set.sounds"), on if config.sounds_enabled else off)
        table.add_row(t("set.auto_scan"), on if config.auto_scan else off)
        table.add_row(t("set.checkpoint"),
                      on if config.checkpoint_on_mutate else off)
        table.add_row(t("set.git"), on if config.git_auto_commit else off)
        table.add_row(t("set.protected"),
                      ", ".join(config.protected_paths or []))
        self._log().write(table)

    def show_logs(self, path: object, lines: list[str]) -> None:
        if not lines:
            self._log().write(Text(self._t("fb.no_logs"), style=DIM))
            return
        log_text = Text()
        for line in lines:
            log_text.append(line + "\n", style=DIM)
        self._log().write(
            Panel(log_text,
                  title=f"{self._t('tbl.session_log')} \u00b7 {path}",
                  border_style=DIM)
        )

    def show_history(self, entries: list[dict]) -> None:
        if not entries:
            self._log().write(Text(self._t("fb.no_history"), style=DIM))
            return
        table = Table(
            title=self._t("tbl.journal"),
            header_style=f"bold {BLUE}",
            border_style=DIM,
            expand=True,
        )
        table.add_column(self._t("tbl.time"), style=DIM)
        table.add_column(self._t("tbl.kind"), style=GREEN)
        table.add_column(self._t("tbl.message"), style=FG)
        for entry in entries:
            table.add_row(entry.get("ts", ""), entry.get("kind", ""),
                          entry.get("message", ""))
        self._log().write(table)

    def show_error(self, text: str) -> None:
        self.show_message("ERROR", text)

    def clear_log(self) -> None:
        self._log().clear()