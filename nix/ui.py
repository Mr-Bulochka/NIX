from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Select, Static

from .i18n import t as _t

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


def _lerp(a: str, b: str, t: float) -> str:
    al = [int(a[i : i + 2], 16) for i in (1, 3, 5)]
    bl = [int(b[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(
        f"{round(al[k] + (bl[k] - al[k]) * t) & 255:02x}" for k in range(3)
    )


def _grad3(a: str, m: str, b: str, t: float) -> str:
    return _lerp(a, m, t * 2) if t < 0.5 else _lerp(m, b, t * 2 - 1)


_STAGE_PALETTES = {
    "seed": {
        "body_a": "#e8edf5", "body_b": "#aab3c7",
        "outline": "#5d6675", "eye": "#39414f",
        "glint": "#ffffff", "cheek": "#f2b0b0", "mouth": "#5d6675",
        "leaf": None, "flower": None,
    },
    "sprout": {
        "body_a": "#8fe3b1", "body_b": "#42b37f",
        "outline": "#176a49", "eye": "#203a31",
        "glint": "#eafff4", "cheek": "#f2b0b0", "mouth": "#176a49",
        "leaf": "#4ade80", "flower": None,
    },
    "bloom": {
        "body_a": "#f9a8d4", "body_m": "#b39df0", "body_b": "#83c6f0",
        "outline": "#3a2f6d", "eye": "#33424f",
        "glint": "#ffffff", "cheek": "#ff9db4", "mouth": "#3a2f6d",
        "leaf": "#4ade80", "flower": "#ffd166",
    },
}

_PET_GRIDS = {
    "compact": {
        "open": [
            "..oooooooo..",
            ".oBBBBBBBBo.",
            ".oBwwBBwwBo.",
            ".oBkkBBkkBo.",
            ".oBpBMMBpBo.",
            ".oBBBBBBBBo.",
            "..oooooooo..",
        ],
        "blink": [
            "..oooooooo..",
            ".oBBBBBBBBo.",
            ".oBkkBBkkBo.",
            ".oBkkBBkkBo.",
            ".oBpBMMBpBo.",
            ".oBBBBBBBBo.",
            "..oooooooo..",
        ],
    },
    "full": {
        "open": [
            "..oooooooooo..",
            ".oBBBBBBBBBBBo.",
            ".obbbbbbbbbbbo.",
            ".obbwkbbwkbbo.",
            ".obbkkbbkkbbo.",
            ".obbpbmmbpbbo.",
            ".obbbbbbbbbbbo.",
            ".oobbbbbbbbboo.",
            "...oooooooo...",
        ],
        "blink": [
            "..oooooooooo..",
            ".oBBBBBBBBBBBo.",
            ".obbbbbbbbbbbo.",
            ".obbkkbbkkbbo.",
            ".obbkkbbkkbbo.",
            ".obbpbmmbpbbo.",
            ".obbbbbbbbbbbo.",
            ".oobbbbbbbbboo.",
            "...oooooooo...",
        ],
    },
}

_OVERLAY = {
    "sprout": "..ooLLoooo..",
    "bloom": "..ooFFoooo..",
}


def _paint(grid: list[str], palette: dict) -> Text:
    rows = len(grid)
    text = Text()
    for y, row in enumerate(grid):
        i = 0
        while i < len(row):
            ch = row[i]
            j = i
            while j < len(row) and row[j] == ch:
                j += 1
            run = row[i:j]
            if ch == ".":
                color = BG
            elif ch == "o":
                color = palette["outline"]
            elif ch in "bB":
                t = y / max(1, rows - 1)
                if "body_m" in palette:
                    color = _grad3(palette["body_a"], palette["body_m"],
                                   palette["body_b"], t)
                else:
                    color = _lerp(palette["body_a"], palette["body_b"], t)
                if ch == "B":
                    color = _lerp(color, "#ffffff", 0.18)
            elif ch == "w":
                color = palette["glint"]
            elif ch == "k":
                color = palette["eye"]
            elif ch == "p":
                color = palette["cheek"]
            elif ch == "M" or ch == "m":
                color = palette["mouth"]
            elif ch == "L":
                color = palette.get("leaf") or palette["outline"]
            elif ch == "F":
                color = palette.get("flower") or palette["cheek"]
            else:
                color = FG
            text.append(run, style=color)
            i = j
        text.append("\n")
    return text


def pet_art(stage: str, size: str = "compact", blink: bool = False) -> Text:
    stage = stage if stage in _STAGE_PALETTES else "seed"
    size = size if size in _PET_GRIDS else "compact"
    grid = list(_PET_GRIDS[size]["blink" if blink else "open"])
    overlay = _OVERLAY.get(stage)
    if overlay:
        grid[0] = overlay
    return _paint(grid, _STAGE_PALETTES[stage])


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


class DetailModal(ModalScreen[None]):
    BINDINGS = [
        Binding("escape", "close", "Close", priority=True),
        Binding("ctrl+q", "close", "", priority=True),
    ]

    CSS = f"""
    DetailModal {{
        align: center middle;
    }}

    #dm-frame {{
        width: 84%;
        max-width: 100;
        height: 84%;
        max-height: 42;
        border: round {BORDER};
        background: {PANEL};
        padding: 0 1;
    }}

    #dm-title {{
        height: 1;
        margin: 1 0 0 0;
        color: {BLUE};
        text-style: bold;
        content-align: left middle;
    }}

    #dm-body {{
        height: 1fr;
        overflow-y: auto;
        scrollbar-size-vertical: 1;
        scrollbar-color: {DIM} {BLACK};
    }}

    #dm-content {{
        padding: 1 0;
    }}

    #dm-close {{
        dock: bottom;
        width: 100%;
        margin: 1 0 1 0;
        background: {RAISED};
        border: round {BORDER};
        color: {FG};
    }}

    #dm-close:hover {{
        border: round {BLUE};
        color: {BLUE};
    }}

    Scrollbar {{
        background: {BLACK};
        color: {BORDER};
    }}

    Scrollbar:hover {{
        background: {BLACK};
        color: {BLUE};
    }}
    """

    def __init__(self, title: str, renderable, close: str) -> None:
        super().__init__()
        self._title = title
        self._renderable = renderable
        self._close = close

    def compose(self) -> ComposeResult:
        with Vertical(id="dm-frame"):
            yield Label(self._title, id="dm-title")
            with VerticalScroll(id="dm-body"):
                yield Static(self._renderable, id="dm-content")
            yield Button(self._close, id="dm-close")

    def action_close(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dm-close":
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
        art = pet_art(pattern, "compact", blink=blink)
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
        table = Table(
            box=None,
            expand=True,
            pad_edge=False,
        )
        for line in lines:
            parts = line.strip().split(None, 1)
            left = parts[0] if parts else line.strip()
            right = parts[1] if len(parts) == 2 else ""
            table.add_row(
                Text(left, style=GREEN),
                Text(right, style=FG),
            )
        self._open_modal(self._t("tbl.commands"), table)

    def _open_modal(self, title: str, renderable) -> None:
        self.push_screen(
            DetailModal(title, renderable, self._t("modal.close"))
        )

    def show_status(self, *, root: str, mode: str, attempts: int,
                    max_attempts: int, files: int, dirs: int,
                    functions: int, classes: int,
                    source_files: int, total_lines: int) -> None:
        t = self._t
        table = Table(
            title=t("tbl.project_status"),
            header_style=f"bold {BLUE}",
            border_style=BORDER,
            expand=True,
            pad_edge=False,
        )
        table.add_column(t("tbl.key"), style=GREEN, no_wrap=True)
        table.add_column(t("tbl.value"), style=FG)
        table.add_row(t("st.root"), root)
        table.add_row(t("st.mode"), mode.upper())
        table.add_row(t("st.attempts"), str(attempts))
        table.add_row(t("st.files"), str(files))
        table.add_row(t("st.dirs"), str(dirs))
        table.add_row(t("st.source"), str(source_files))
        table.add_row(t("st.functions"), str(functions))
        table.add_row(t("st.classes"), str(classes))
        table.add_row(t("st.lines"), f"{total_lines:,}")
        self._open_modal(t("tbl.project_status"), table)

    def show_scan(self, info: "ProjectInfo") -> None:
        t = self._t
        header = Text()
        header.append(f"{info.files} {t('scan.files')}  ", style=CYAN)
        header.append(f"{info.directories} {t('scan.dirs')}  ", style=CYAN)
        header.append(f"{info.functions} {t('scan.functions')}  ", style=CYAN)
        header.append(f"{info.classes} {t('scan.classes')}  ", style=CYAN)
        header.append(f"{info.total_lines:,} {t('scan.lines')}", style=CYAN)
        header.append("\n")

        if info.extensions:
            table = Table(
                title=t("tbl.extensions"),
                header_style=f"bold {PURPLE}",
                border_style=BORDER,
                expand=True,
                pad_edge=False,
            )
            table.add_column(t("tbl.extension"), style=FG)
            table.add_column(t("tbl.count"), justify="right", style=GREEN)
            for ext, count in info.top_extensions:
                table.add_row(ext, str(count))
            self._open_modal(t("tbl.scan"), Group(header, table))
        else:
            self._open_modal(t("tbl.scan"), header)

    def show_pet(self, pet: dict) -> None:
        mood = pet.get("mood", "curious")
        mood_label = self._t(f"mood.{mood}")
        art = pet_art(pet.get("body_pattern", "seed"), "full",
                      blink=self._blink == 1)
        stat = Table(
            title=self._t("tbl.pet", name=pet.get("name", "???")),
            header_style=f"bold {PURPLE}",
            border_style=BORDER,
            expand=True,
            pad_edge=False,
        )
        stat.add_column(self._t("tbl.attribute"), style=CYAN, no_wrap=True)
        stat.add_column(self._t("tbl.value"), style=FG)
        stat.add_row(self._t("pet.name"), str(pet.get("name", "???")))
        stat.add_row(self._t("pet.mood"),
                     f"[{MOOD_STYLES.get(mood, FG)}]{mood_label}[/]")
        stat.add_row(self._t("pet.energy"), str(pet.get("energy", 100)))
        stat.add_row(self._t("pet.age"), str(pet.get("age", 0)))
        stat.add_row(self._t("pet.body"),
                     self._t(f"pet.pattern.{pet.get('body_pattern', 'seed')}"))
        stat.add_row(self._t("pet.stage"), str(pet.get("stage", 1)))
        stat.add_row(self._t("pet.mutations"),
                     str(pet.get("mutations_witnessed", 0)))
        stat.add_row(self._t("pet.failures"),
                     str(pet.get("failures_survived", 0)))
        self._open_modal(self._t("tbl.pet", name=pet.get("name", "???")),
                         Group(art, stat))

    def show_settings(self, config: "Config") -> None:
        t = self._t
        on, off = t("on"), t("off")
        table = Table(
            title=t("tbl.settings"),
            header_style=f"bold {GREEN}",
            border_style=BORDER,
            expand=True,
            pad_edge=False,
        )
        table.add_column(t("tbl.setting"), style=GREEN, no_wrap=True)
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
        self._open_modal(t("tbl.settings"), table)

    def show_logs(self, path: object, lines: list[str]) -> None:
        if not lines:
            self._log().write(Text(self._t("fb.no_logs"), style=DIM))
            return
        log_text = Text()
        for line in lines:
            log_text.append(line + "\n", style=DIM)
        self._open_modal(
            self._t("tbl.session_log"),
            Panel(log_text, border_style=BORDER),
        )

    def show_history(self, entries: list[dict]) -> None:
        if not entries:
            self._log().write(Text(self._t("fb.no_history"), style=DIM))
            return
        table = Table(
            title=self._t("tbl.journal"),
            header_style=f"bold {BLUE}",
            border_style=BORDER,
            expand=True,
            pad_edge=False,
        )
        table.add_column(self._t("tbl.time"), style=DIM)
        table.add_column(self._t("tbl.kind"), style=GREEN)
        table.add_column(self._t("tbl.message"), style=FG)
        for entry in entries:
            table.add_row(entry.get("ts", ""), entry.get("kind", ""),
                          entry.get("message", ""))
        self._open_modal(self._t("tbl.journal"), table)

    def show_error(self, text: str) -> None:
        self.show_message("ERROR", text)

    def clear_log(self) -> None:
        self._log().clear()