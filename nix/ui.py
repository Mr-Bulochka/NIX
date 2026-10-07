from __future__ import annotations

import copy
import time
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from rich.cells import cell_len, set_cell_size
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.css.query import NoMatches, TooManyMatches, WrongType
from textual.timer import Timer
from textual.screen import ModalScreen
from textual.widgets import (
    Button, Footer, Header, Input, Label, RichLog, Select, Static, Switch,
)
from textual.widgets._header import (
    HeaderClock, HeaderClockSpace, HeaderIcon, HeaderTitle,
)

from .avatar import (genes_for as avatar_genes_for, render as render_avatar,
                       idle_look)
from .avatar import VARIANT_KINDS
from .commands import _usage, get_all_commands
from .config import DEFAULT_PROTECTED_PATHS, parse_path_list
from .scanner import scan_project
from .i18n import LANGUAGES, t as _t
from .modules import all_modules

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


def _clip(text: str, limit: int = 400) -> str:
    text = " ".join(str(text).split())
    if cell_len(text) <= limit:
        return text
    return set_cell_size(text, limit - 1).rstrip() + "\u2026"


def _ljust(text: str, width: int) -> str:
    """Left-justify by *visible cell width*, not by character count.

    Cyrillic and CJK glyphs occupy a different number of terminal cells than
    Python counts characters, so ``str.ljust`` misaligns any localized column.
    Overlong values are truncated with an ellipsis instead of pushing the next
    column off the edge.
    """
    text = str(text)
    text_w = cell_len(text)
    if text_w <= width:
        return text + " " * (width - text_w)
    return set_cell_size(text, width - 1).rstrip() + "\u2026"


def _head(text: str) -> str:
    """Uppercase a heading without widening non-ASCII text.

    ``str.upper()`` expands some Cyrillic sequences (e.g. ``'ß' -> 'SS'``), which
    silently breaks the fixed-width header columns. Fall back to the original
    string when uppercasing grows the text.
    """
    text = str(text)
    upper = text.upper()
    return upper if cell_len(upper) <= cell_len(text) else text


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
    "ECHO": BLUE,
    "ERROR": RED,
    "WARN": YELLOW,
    "MUTATION": YELLOW,
    "TEST": YELLOW,
    "LEARN": GREEN,
    "CHECKPOINT": BLUE,
    "SCAFFOLD": CYAN,
    "TESTGEN": PURPLE,
    "RECIPE": BLUE,
    "STEP": DIM,
    "OK": GREEN,
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
    width: 12;
    height: 8;
    content-align: center middle;
    color: {FG};
}}

#top-pet-name {{
    content-align: center middle;
    text-style: bold;
    color: {CYAN};
    margin-top: 0;
    width: auto;
}}

#pet-stats {{
    width: auto;
    height: auto;
    padding: 1 2;
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
    min-height: 3;
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

#btn-scan {{ color: {CYAN}; }}
#btn-status {{ color: {GREEN}; }}
#btn-pet {{ color: {PURPLE}; }}
#btn-settings {{ color: {YELLOW}; }}
#btn-quit {{ color: {RED}; }}

#cmdwrap {{
    dock: bottom;
    height: auto;
    max-height: 50%;
    margin: 0 2 1 2;
    background: {BG};
}}

#cmd {{
    height: 3;
    margin: 0;
    padding: 0 1;
    border: round {BORDER};
    background: {PANEL};
    color: {FG};
}}

#cmd:focus {{
    border: round {BLUE};
}}

#suggest {{
    display: none;
    height: auto;
    max-height: 100%;
    overflow-y: auto;
    margin: 0;
    padding: 0;
    border: round {BORDER};
    border-bottom: none;
    background: {PANEL};
    color: {DIM};
}}

#suggest.visible {{
    display: block;
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
    text-style: bold;
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
"""

# Responsive tuning applied dynamically from on_resize:
#  * #app.resp-narrow => hide side panel on small widths
#  * #app.resp-compact => drop the pet stage header on short heights
#  * #app.resp-tiny   => focus purely on the log on very small windows

RESP_CSS = f"""
#app.resp-narrow #pet-stats {{
    display: none;
}}

#app.resp-narrow #pet-wrap {{
    padding: 0;
}}

#app.resp-narrow #top-pet-name {{
    max-width: 100%;
}}

#app.resp-compact #top {{
    display: none;
}}

#app.resp-compact #toolbar {{
    display: none;
}}

#app.resp-tiny #top {{
    display: none;
}}

#app.resp-tiny #toolbar {{
    display: none;
}}
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


@dataclass(frozen=True)
class SettingSpec:
    """Declarative description of a single toggle/numeric settings control.

    ``kind`` drives both the widget that gets mounted and how the value is
    parsed on Apply: ``switch`` -> ``Switch``, ``int``/``float`` -> ``Input``
    parsed and clamped to ``low``/``high``, ``paths`` -> ``Input`` parsed by
    :func:`nix.config.parse_path_list`.
    """
    widget_id: str
    key: str
    kind: str
    section: str
    low: float | None = None
    high: float | None = None
    label_key: str | None = None

    @property
    def label(self) -> str:
        return self.label_key or f"set.{self.key}"


SETTING_SPECS: tuple[SettingSpec, ...] = (
    # -- appearance ------------------------------------------------------
    SettingSpec("set-tamagotchi", "tamagotchi_enabled", "switch",
                "appearance", label_key="set.tamagotchi"),
    SettingSpec("set-animations", "animations_enabled", "switch",
                "appearance", label_key="set.animations"),
    SettingSpec("set-avatar", "avatar_enabled", "switch",
                "appearance", label_key="set.avatar"),
    SettingSpec("set-sounds", "sounds_enabled", "switch",
                "appearance", label_key="set.sounds"),
    SettingSpec("set-clock", "show_clock", "switch", "appearance",
                label_key="set.clock"),
    SettingSpec("set-log-max-lines", "log_max_lines", "int",
                "appearance", 50, 5000),
    SettingSpec("set-animation-interval", "animation_interval", "float",
                "appearance", 0.1, 10.0),
    # -- input & history -------------------------------------------------
    SettingSpec("set-ac-enabled", "autocomplete_enabled", "switch", "input",
                label_key="set.ac_enabled"),
    SettingSpec("set-ac-case-insensitive", "autocomplete_case_insensitive",
                "switch", "input", label_key="set.ac_case_insensitive"),
    SettingSpec("set-ac-descriptions", "autocomplete_show_descriptions",
                "switch", "input", label_key="set.ac_descriptions"),
    SettingSpec("set-ac-min-chars", "autocomplete_min_chars", "int",
                "input", 0, 10, label_key="set.ac_min_chars"),
    SettingSpec("set-ac-max-items", "autocomplete_max_items", "int",
                "input", 1, 50, label_key="set.ac_max_items"),
    SettingSpec("set-history-size", "command_history_size", "int",
                "input", 0, 500, label_key="set.history_size"),
    # -- behaviour -------------------------------------------------------
    SettingSpec("set-auto-scan", "auto_scan", "switch", "behavior",
                label_key="set.auto_scan"),
    SettingSpec("set-checkpoint", "checkpoint_on_mutate", "switch",
                "behavior", label_key="set.checkpoint"),
    SettingSpec("set-git", "git_auto_commit", "switch", "behavior",
                label_key="set.git"),
    SettingSpec("set-pill-cooldown", "pill_cooldown_minutes", "int",
                "behavior", 0, 1440, label_key="set.pill_cooldown"),
    SettingSpec("set-timeout", "default_command_timeout", "int",
                "behavior", 5, 3600, label_key="set.default_timeout"),
    SettingSpec("set-protected-paths", "protected_paths", "paths",
                "behavior", label_key="set.protected_paths"),
)

SECTION_ORDER = ("appearance", "input", "behavior")
SECTION_KEYS = {
    "appearance": "set.section_appearance",
    "input": "set.section_input",
    "behavior": "set.section_behavior",
}

AC_SPEC_IDS = (
    "set-ac-enabled",
    "set-ac-case-insensitive",
    "set-ac-descriptions",
    "set-ac-min-chars",
    "set-ac-max-items",
)

# Derived views over the declarative registry. Kept as module-level dicts so
# they can be consumed by the modal, by tests and by external tooling.
TOGGLE_KEYS = {
    spec.widget_id: spec.key
    for spec in SETTING_SPECS
    if spec.kind == "switch"
}

INT_KEYS = {
    spec.widget_id: (spec.key, int(spec.low or 0), int(spec.high or 0))
    for spec in SETTING_SPECS
    if spec.kind == "int"
}

FLOAT_KEYS = {
    spec.widget_id: (spec.key, float(spec.low or 0.0),
                     float(spec.high or 0.0))
    for spec in SETTING_SPECS
    if spec.kind == "float"
}

PATHS_KEYS = {
    spec.widget_id: spec.key
    for spec in SETTING_SPECS
    if spec.kind == "paths"
}

# Backwards compatible autocomplete-only subsets.
AUTOCOMPLETE_SWITCH_KEYS = {
    wid: TOGGLE_KEYS[wid] for wid in AC_SPEC_IDS if wid in TOGGLE_KEYS
}

AUTOCOMPLETE_INT_KEYS = {
    wid: INT_KEYS[wid] for wid in AC_SPEC_IDS if wid in INT_KEYS
}


def _specs_for(section: str) -> tuple[SettingSpec, ...]:
    return tuple(s for s in SETTING_SPECS if s.section == section)


def _spec_by_id(widget_id: str) -> SettingSpec | None:
    for spec in SETTING_SPECS:
        if spec.widget_id == widget_id:
            return spec
    return None


class SettingsModal(ModalScreen[None]):
    BINDINGS = [
        Binding("escape", "close_settings", "Close", priority=True),
        Binding("ctrl+q", "close_settings", "", priority=True),
    ]

    TOGGLE_KEYS = TOGGLE_KEYS
    INT_KEYS = INT_KEYS
    FLOAT_KEYS = FLOAT_KEYS
    PATHS_KEYS = PATHS_KEYS
    AUTOCOMPLETE_SWITCH_KEYS = AUTOCOMPLETE_SWITCH_KEYS
    AUTOCOMPLETE_INT_KEYS = AUTOCOMPLETE_INT_KEYS

    CSS = f"""
    SettingsModal {{
        align: center middle;
    }}

    #set-frame {{
        width: 88%;
        max-width: 84;
        height: 88%;
        max-height: 50;
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

    #set-body #set-skin-label {{
        color: {PURPLE};
    }}

    #set-body #set-pill {{
        width: 100%;
        background: {RAISED};
        border: round {BORDER};
        color: {FG};
    }}

    #set-body #set-pill:hover {{
        border: round {BLUE};
        color: {BLUE};
    }}

    #set-body #set-pill:disabled {{
        color: {DIM};
    }}

    #set-footer {{
        dock: bottom;
        height: auto;
        margin: 1 0 1 0;
        align-horizontal: right;
    }}

    #set-footer .set-btn {{
        min-width: 12;
        margin-left: 1;
        background: {RAISED};
        border: round {BORDER};
        color: {FG};
    }}

    #set-footer .set-btn:hover {{
        border: round {BLUE};
        color: {BLUE};
    }}

    #set-apply {{
        background: {BLUE};
        border: round {BLUE};
        color: {BLACK};
        text-style: bold;
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
        self._draft = copy.copy(config)
        self._save = save
        self._input_ready = False

    def _t(self, key: str, **kw) -> str:
        return self._ui._t(key, **kw)

    def _mods(self) -> list:
        return sorted(all_modules(), key=lambda m: m.id)

    def _row(self, label: str, field) -> Horizontal:
        return Horizontal(
            Label(label, classes="set-label"),
            field,
            classes="set-row",
        )

    def compose(self) -> ComposeResult:
        t = self._t
        draft = self._draft
        with Vertical(id="set-frame"):
            yield Label(t("tbl.settings"), id="set-title")
            with VerticalScroll(id="set-body"):
                yield self._row(
                    t("set.language"),
                    Select(
                        [(LANGUAGES[k], k) for k in LANGUAGES],
                        value=draft.language,
                        id="set-lang",
                    ),
                )
                yield self._row(
                    t("st.mode"),
                    Select(
                        [(t(f"cmd.mode.{m}"), m) for m in MODES],
                        value=draft.mode,
                        id="set-mode",
                    ),
                )
                yield self._row(
                    t("set.priority_lang"),
                    Select(
                        [(t("set.auto"), "")] + [
                            (m.name, m.id) for m in self._mods()
                        ],
                        value=draft.priority_lang
                        if any(m.id == draft.priority_lang
                               for m in self._mods())
                        else "",
                        id="set-priority-lang",
                    ),
                )
                yield self._row(
                    t("set.skin"),
                    Label("", id="set-skin-label", classes="set-field"),
                )
                yield self._row(
                    t("set.pill"),
                    Button("", id="set-pill"),
                )
                yield self._row(
                    t("set.attempts"),
                    Input(str(draft.attempts), id="set-attempts"),
                )
                yield self._row(
                    t("set.mutation_budget"),
                    Input(str(draft.mutation_budget), id="set-budget"),
                )
                for section in SECTION_ORDER:
                    yield Label(t(SECTION_KEYS[section]),
                                 classes="set-hint set-section")
                    for spec in _specs_for(section):
                        yield self._spec_row(spec, draft)
                yield Label(t("set.modules"), classes="set-hint set-section")
                for m in self._mods():
                    yield self._row(
                        m.name,
                        Switch(
                            draft.enabled_modules is None
                            or m.id in draft.enabled_modules,
                            id=f"set-mod-{m.id}",
                        ),
                    )
            with Horizontal(id="set-footer"):
                yield Button("", id="set-close", classes="set-btn")
                yield Button("", id="set-apply")

    def _spec_row(self, spec: SettingSpec, draft) -> Horizontal:
        """Build the row for one registry entry from its declared kind."""
        if spec.kind == "switch":
            field = Switch(getattr(draft, spec.key), id=spec.widget_id)
        elif spec.kind == "paths":
            joined = ", ".join(getattr(draft, spec.key) or [])
            field = Input(joined, id=spec.widget_id)
        else:
            field = Input(str(getattr(draft, spec.key)), id=spec.widget_id)
        return self._row(self._t(spec.label), field)

    def _toggle_label(self, wid: str) -> str:
        spec = _spec_by_id(wid)
        return self._t(spec.label) if spec else wid

    def _ac_switch_label(self, wid: str) -> str:
        return self._toggle_label(wid)

    def _ac_field_label(self, wid: str) -> str:
        return self._toggle_label(wid)

    def on_mount(self) -> None:
        self.query_one("#set-close", Button).label = self._t("modal.close")
        self.query_one("#set-apply", Button).label = self._t("set.apply")
        self._update_pill()
        self.set_interval(1.0, self._tick_pill)
        self._input_ready = True

    def _tick_pill(self) -> None:
        try:
            self._update_pill()
        except Exception:
            pass

    def on_key(self, event) -> None:
        if event.key != "enter":
            return
        focused = self.focused
        if isinstance(focused, (Input, Button)):
            return
        self.action_apply_settings()

    def _update_pill(self) -> None:
        t = self._t
        pet = self._ui.nix.pet or {}
        self.query_one("#set-skin-label", Label).update(
            self._ui._skin_name(pet)
        )
        remaining = self._ui.nix.pill_remaining()
        btn = self.query_one("#set-pill", Button)
        if remaining is None:
            btn.label = t("set.pill_ready")
            btn.disabled = True
            return
        if remaining > 0:
            minutes = int(remaining // 60) + (1 if remaining % 60 else 0)
            btn.label = f"{t('set.pill_give')} \u00b7 {t('set.pill_cd', min=minutes)}"
            btn.disabled = True
        else:
            btn.label = t("set.pill_give")
            btn.disabled = False

    def on_select_changed(self, event) -> None:
        if not self._input_ready:
            return
        wid = getattr(event.select, "id", "")
        if wid == "set-lang":
            self._draft.language = event.value
        elif wid == "set-mode":
            self._draft.mode = event.value
        elif wid == "set-priority-lang":
            self._draft.priority_lang = event.value or ""

    def on_input_submitted(self, event) -> None:
        if not self._input_ready:
            return
        wid = getattr(event.input, "id", "")
        raw = event.value.strip()
        if wid == "set-attempts":
            val = self._parse_int_input(event.input, raw)
            if val is None:
                return
            self._draft.attempts = max(0, min(val, self._cfg.max_attempts))
            event.input.value = str(self._draft.attempts)
            return
        if wid == "set-budget":
            val = self._parse_int_input(event.input, raw)
            if val is None:
                return
            self._draft.mutation_budget = max(0, val)
            event.input.value = str(self._draft.mutation_budget)
            return
        spec = _spec_by_id(wid)
        if spec is None:
            return
        if not self._apply_spec_input(spec, event.input, raw):
            return
        value = getattr(self._draft, spec.key)
        event.input.value = (
            ", ".join(value) if spec.kind == "paths" else str(value)
        )

    def _parse_int_input(self, widget, raw: str) -> int | None:
        try:
            return int(raw)
        except ValueError:
            self.notify(self._t("fb.int_invalid"), severity="error")
            widget.focus()
            return None

    def _apply_spec_input(self, spec: SettingSpec, widget, raw: str) -> bool:
        """Parse, clamp and store one registry field. False means invalid."""
        if spec.kind == "int":
            try:
                value: object = int(raw)
            except ValueError:
                self.notify(self._t("fb.int_invalid"), severity="error")
                widget.focus()
                return False
            lo, hi = int(spec.low or 0), int(spec.high or 0)
            setattr(self._draft, spec.key, max(lo, min(value, hi)))
            return True
        if spec.kind == "float":
            try:
                value = float(raw)
            except ValueError:
                self.notify(self._t("fb.num_invalid"), severity="error")
                widget.focus()
                return False
            lo, hi = float(spec.low or 0.0), float(spec.high or 0.0)
            setattr(self._draft, spec.key, max(lo, min(value, hi)))
            return True
        if spec.kind == "paths":
            setattr(self._draft, spec.key, parse_path_list(raw))
            return True
        return False

    def on_switch_changed(self, event) -> None:
        if not self._input_ready:
            return
        wid = getattr(event.switch, "id", "")
        key = self.TOGGLE_KEYS.get(wid)
        if key:
            setattr(self._draft, key, event.value)
        elif wid.startswith("set-mod-"):
            self._draft.enabled_modules = self._enabled_from_switches()

    def _enabled_from_switches(self) -> list[str] | None:
        mods = self._mods()
        enabled = [
            m.id for m in mods
            if self.query_one(f"#set-mod-{m.id}", Switch).value
        ]
        return None if len(enabled) == len(mods) else enabled

    def on_button_pressed(self, event: Button.Pressed) -> None:
        wid = getattr(event.button, "id", "")
        if wid == "set-apply":
            self.action_apply_settings()
            return
        if wid == "set-close":
            self.action_close_settings()
            return
        if wid != "set-pill":
            return
        ok, message = self._ui.nix.give_pill()
        if ok:
            self._ui._celebrate()
        self._ui._refresh_pet()
        self.notify(message, severity="information" if ok else "warning",
                    timeout=4)
        self._update_pill()

    def action_apply_settings(self) -> None:
        if not self._apply():
            return
        self._ui._refresh_pet()
        self._ui._refresh_header()
        self.dismiss(None)

    def action_close_settings(self) -> None:
        self.dismiss(None)

    def _read_spec_inputs(self) -> bool:
        """Re-read every registry ``Input`` on Apply.

        Values typed but never submitted still have to land, so Apply parses
        the widgets directly instead of relying on ``Input.Submitted``. The
        modal stays open when any field is invalid.
        """
        for spec in SETTING_SPECS:
            if spec.kind == "switch":
                continue
            try:
                widget = self.query_one(f"#{spec.widget_id}", Input)
            except Exception:
                continue
            if not self._apply_spec_input(spec, widget, widget.value.strip()):
                return False
        return True

    def _apply(self) -> bool:
        if not self._read_spec_inputs():
            return False
        self._draft.enabled_modules = self._enabled_from_switches()
        # setattr on an existing Config skips __post_init__, so re-normalise
        # the list field explicitly.
        self._draft.protected_paths = (
            parse_path_list(self._draft.protected_paths)
            or list(DEFAULT_PROTECTED_PATHS)
        )
        for f in fields(self._cfg):
            setattr(self._cfg, f.name, getattr(self._draft, f.name))
        self._save(self._cfg)
        self._ui._apply_language()
        self._ui.nix.apply_module_settings()
        self._ui._apply_pet_visibility()
        self._ui._apply_runtime_settings()
        self._ui._refresh_pet()
        self._ui._refresh_header()
        return True

    def on_unmount(self) -> None:
        self._input_ready = False


class NixHeader(Header):
    MODE_COLORS = {"safe": GREEN, "git": BLUE}

    def __init__(self, ui: "NixUI", show_clock: bool = True) -> None:
        super().__init__(show_clock=show_clock)
        self._ui = ui

    def compose(self) -> ComposeResult:
        """Always mount both clock widgets so the clock can be toggled live.

        ``Header`` picks one variant at construction time, which Textual 8.x
        does not support at runtime. Rendering both and switching ``display``
        lets the ``show_clock`` setting apply without remounting the header.
        """
        yield HeaderIcon().data_bind(NixHeader.icon)
        yield HeaderTitle()
        yield HeaderClock(id="hdr-clock").data_bind(NixHeader.time_format)
        yield HeaderClockSpace(id="hdr-noclock")

    def on_mount(self) -> None:
        self.set_clock_visible(bool(self._ui.nix.config.show_clock))

    def set_clock_visible(self, visible: bool) -> None:
        """Show or hide the header clock without remounting the widget."""
        try:
            self.query_one("#hdr-clock").display = visible
            self.query_one("#hdr-noclock").display = not visible
        except Exception:
            pass

    def format_title(self) -> Content:
        ui = self._ui
        name = _clip(ui.nix.root.name or str(ui.nix.root), 40)
        cfg = ui.nix.config
        mode = cfg.t(f"cmd.mode.{cfg.mode}")
        color = self.MODE_COLORS.get(cfg.mode, CYAN)
        return Content.assemble(
            Text(f" {name} ", style=f"bold {PURPLE}"),
            Text("\u00b7", style=DIM),
            Text(f" {mode.upper()} ", style=f"bold {color}"),
            Text(f"\u00b7 v{ui.nix.version}", style=DIM),
        )


class NixUI(App):
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear_log", "Clear", priority=True),
        Binding("ctrl+s", "run_scan", "Scan", priority=True),
        Binding("ctrl+p", "run_pet", "Pet", priority=True),
        Binding("ctrl+1", "run_pet", "Pet", priority=True, show=False),
        Binding("ctrl+3", "run_status", "Status", priority=True, show=False),
        Binding("ctrl+4", "run_settings", "Settings", priority=True,
                show=False),
        Binding("ctrl+6", "run_help", "Help", priority=True, show=False),
        Binding("pageup", "page_up", "Page up", priority=True, show=False),
        Binding("pagedown", "page_down", "Page down", priority=True,
                show=False),
    ]

    CSS = APP_CSS + RESP_CSS

    def __init__(self, nix: "NixApp") -> None:
        super().__init__()
        self.nix = nix
        self._spin = 0
        self._blink = 0
        self._cmd_history: list[str] = []
        self._cmd_hist_idx: int | None = None
        self._suggest_items: list[tuple[str, str, str]] = []
        self._suggest_idx: int = 0
        self._suggest_applied: str | None = None
        self._celebrate_until = 0.0
        self._auto_scan_done = False
        self._anim_timer: Timer | None = None

    def on_resize(self, event) -> None:
        w, h = event.size.width, event.size.height
        try:
            root = self.query_one("#app")
        except Exception:
            return
        root.set_class(w < 70, "resp-narrow")
        root.set_class(h < 22, "resp-compact")
        root.set_class(h < 14, "resp-tiny")

    # ----- lifecycle -------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="app"):
            yield NixHeader(self, show_clock=self.nix.config.show_clock)
            with Horizontal(id="top"):
                with Vertical(id="pet-wrap"):
                    yield Static("", id="pet-box")
                    yield Label("", id="top-pet-name")
                with Vertical(id="pet-stats"):
                    yield Label("", id="st-mood", classes="stat")
                    yield Label("", id="st-energy", classes="stat")
                    yield Label("", id="st-stage", classes="stat")
                    yield Label("", id="st-xp", classes="stat")
            with VerticalScroll(id="logwrap"):
                yield RichLog(id="log", wrap=True, markup=True,
                              highlight=True, auto_scroll=True)
            with Horizontal(id="toolbar"):
                yield Button("", id="btn-pet")
                yield Button("", id="btn-scan")
                yield Button("", id="btn-status")
                yield Button("", id="btn-settings")
                yield Button("", id="btn-quit")
            with Vertical(id="cmdwrap"):
                yield Label("", id="suggest", classes="suggest")
                yield Input(id="cmd", placeholder="")
            yield Footer()

    def on_mount(self) -> None:
        self._apply_language()
        self._apply_pet_visibility()
        if self.nix.pet is None:
            self.push_screen(
                FirstLaunchScreen(self.nix.config.language),
                callback=self._on_pet_ready,
            )
        else:
            self._refresh_pet()
            self._write_session_start()
            self.query_one("#cmd", Input).focus()
            self._auto_scan_if_enabled()
        self._apply_timer()
        self._apply_log_limits()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if getattr(event.input, "id", "") != "cmd":
            return
        raw = event.value.strip()
        self._clear_suggestions()
        if not raw:
            return
        if not self._cmd_history or self._cmd_history[-1] != raw:
            self._cmd_history.append(raw)
        self._apply_history_limit()
        self._cmd_hist_idx = None
        cmd_input = self.query_one("#cmd", Input)
        cmd_input.value = ""
        if not self.nix.handle_command(raw):
            self.exit(0)
        self._refresh_header()
        self._focus_cmd()

    def on_input_changed(self, event: Input.Changed) -> None:
        if getattr(event.input, "id", "") != "cmd":
            return
        if self._suggest_applied is not None:
            if event.value == self._suggest_applied:
                return
            self._suggest_applied = None
        self._update_suggestions(event.value)

    def on_input_blur(self, event: Input.Blur) -> None:
        if getattr(event.input, "id", "") != "cmd":
            return
        self._clear_suggestions()

    def on_click(self, event) -> None:
        if getattr(event.widget, "id", "") != "suggest":
            return
        if not self._suggest_items:
            return
        # The box has a round border, so content line 0 sits at offset y == 1.
        idx = getattr(event, "offset", None)
        idx = 0 if idx is None else idx.y - 1
        if idx < 0 or idx >= len(self._suggest_items):
            return
        self._suggest_idx = idx
        self._render_suggestions()
        event.stop()

    def on_key(self, event) -> None:
        if getattr(self.focused, "id", None) != "cmd":
            return
        cmd = self.query_one("#cmd", Input)
        if event.key == "escape":
            if self._suggest_items:
                self._clear_suggestions()
                event.stop()
                return
            self._cmd_hist_idx = None
            self._set_cmd_value("")
            event.stop()
            return
        if event.key == "tab":
            if self._suggest_items:
                self._apply_suggestion()
                event.stop()
                return
        if event.key == "up":
            if self._suggest_items:
                self._move_suggestion(-1)
                event.stop()
                return
            if self._cmd_history:
                if self._cmd_hist_idx is None:
                    self._cmd_hist_idx = len(self._cmd_history) - 1
                else:
                    self._cmd_hist_idx = max(0, self._cmd_hist_idx - 1)
                self._set_cmd_value(self._cmd_history[self._cmd_hist_idx])
            event.stop()
            return
        if event.key == "down":
            if self._suggest_items:
                self._move_suggestion(1)
                event.stop()
                return
            if self._cmd_hist_idx is not None:
                self._cmd_hist_idx += 1
                if self._cmd_hist_idx < len(self._cmd_history):
                    self._set_cmd_value(self._cmd_history[self._cmd_hist_idx])
                else:
                    self._cmd_hist_idx = None
                    self._set_cmd_value("")
            event.stop()
            return

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {
            "btn-scan": "scan",
            "btn-status": "status",
            "btn-pet": "pet",
            "btn-settings": "settings",
            "btn-quit": "quit",
        }
        action = mapping.get(event.button.id)
        if not action:
            return
        if not self.nix.handle_command(action):
            self.exit(0)
        self._refresh_header()
        if action != "settings":
            self._focus_cmd()

    # ----- actions ---------------------------------------------------

    def action_quit(self) -> None:
        self.exit(0)

    def action_clear_log(self) -> None:
        self._log().clear()
        self._focus_cmd()

    def action_run_scan(self) -> None:
        self.nix.handle_command("scan")
        self._refresh_header()
        self._focus_cmd()

    def action_run_pet(self) -> None:
        self.nix.handle_command("pet")
        self._focus_cmd()

    def action_run_status(self) -> None:
        self.nix.handle_command("status")
        self._refresh_header()
        self._focus_cmd()

    def action_run_settings(self) -> None:
        self.nix.handle_command("settings")
        self._focus_cmd()

    def action_run_help(self) -> None:
        self.nix.handle_command("help")
        self._focus_cmd()

    # ----- internal --------------------------------------------------

    def _log(self) -> RichLog:
        return self.query_one("#log", RichLog)

    def _suggest_box(self) -> Label:
        return self.query_one("#suggest", Label)

    def _suggest_query(self, value: str) -> str:
        return value.strip().split()[0] if value.strip() else ""

    def _suggest_matches(self, value: str) -> list[tuple[str, str, str]]:
        cfg = self.nix.config
        if not cfg.autocomplete_enabled:
            return []
        query = self._suggest_query(value)
        if len(query) < cfg.autocomplete_min_chars:
            return []
        fold = cfg.autocomplete_case_insensitive
        needle = query.casefold() if fold else query
        scored: list[tuple[tuple[int, int], str, str, str]] = []
        for name, cmd in get_all_commands().items():
            hay = name.casefold() if fold else name
            # `_usage` already resolves the localized usage line and falls back
            # to the registry text; going through `self._t` here would echo a
            # raw `cmd.<name>.usage` key for the commands that have no override.
            usage = _usage(self.nix, cmd)
            detail = self._t(f"cmd.{name}.desc") or cmd.description or cmd.usage
            if not cfg.autocomplete_show_descriptions:
                detail = usage if usage != name else ""
            detail_hay = detail.casefold() if fold else detail
            # Rank: name prefix beats name substring, which beats a match in the
            # usage or the localized description.
            if hay.startswith(needle):
                rank = (0, 0)
            elif needle in hay:
                rank = (1, hay.find(needle))
            elif needle in usage.casefold():
                rank = (2, 0)
            elif needle in detail_hay:
                rank = (3, detail_hay.find(needle))
            else:
                continue
            scored.append((rank, name, usage, detail))
        scored.sort(key=lambda item: item[0])
        return [(n, u, d) for _rank, n, u, d in scored[: cfg.autocomplete_max_items]]

    def _update_suggestions(self, value: str) -> None:
        self._suggest_items = self._suggest_matches(value)
        self._suggest_idx = 0
        self._render_suggestions()

    def _render_suggestions(self) -> None:
        try:
            box = self._suggest_box()
        except Exception:
            return
        if not self._suggest_items:
            box.remove_class("visible")
            box.update(Text())
            return
        width = max(24, (self.size.width or 80) - 8)
        usage_room = max(12, min(40, width // 2))
        detail_room = max(16, width - usage_room - 10)
        rendered = Text()
        for idx, (name, usage, detail) in enumerate(self._suggest_items):
            selected = idx == self._suggest_idx
            head = "\u25b8 " if selected else "  "
            line = Text()
            line.append(head, style=f"bold {BLUE}" if selected else DIM)
            line.append(name, style=f"bold {CYAN}" if selected else FG)
            # Give the remaining cells to the description, so a long localized
            # usage string never squeezes it out entirely.
            if usage and usage != name:
                room = max(12, detail_room - 6)
                line.append("  ", style=DIM)
                line.append(_clip(usage, room), style=DIM)
            if detail:
                line.append("  \u00b7 ", style=DIM)
                line.append(_clip(detail, detail_room), style=DIM)
            if selected:
                line.stylize(f"on {RAISED}")
            line.truncate(width, overflow="ellipsis")
            rendered.append(line)
            rendered.append("\n")
        rendered.rstrip()
        box.add_class("visible")
        box.update(rendered)

    def _set_cmd_value(self, value: str) -> None:
        """Assign the input value without letting it trigger suggestions."""
        self._suggest_applied = value or None
        self._clear_suggestions()
        cmd = self.query_one("#cmd", Input)
        cmd.value = value
        cmd.cursor_position = len(value)

    def _move_suggestion(self, delta: int) -> None:
        if not self._suggest_items:
            return
        count = len(self._suggest_items)
        self._suggest_idx = max(0, min(self._suggest_idx + delta, count - 1))
        self._render_suggestions()

    def _apply_suggestion(self) -> None:
        if not self._suggest_items:
            return
        name = self._suggest_items[self._suggest_idx][0]
        self._set_cmd_value(name)
        self._clear_suggestions()
        self._suggest_applied = name
        self.query_one("#cmd", Input).focus()

    def _clear_suggestions(self) -> None:
        self._suggest_items = []
        self._suggest_idx = 0
        try:
            box = self._suggest_box()
        except Exception:
            return
        box.remove_class("visible")
        box.update(Text())

    def _focus_cmd(self) -> None:
        try:
            self.query_one("#cmd", Input).focus()
        except Exception:
            pass

    def _t(self, key: str, **kw) -> str:
        return self.nix.config.t(key, **kw)

    def _apply_language(self) -> None:
        self.query_one("#btn-scan", Button).label = f"2 {self._t('btn.scan')}"
        self.query_one("#btn-status", Button).label = f"3 {self._t('btn.status')}"
        self.query_one("#btn-pet", Button).label = f"1 {self._t('btn.pet')}"
        self.query_one("#btn-settings", Button).label = f"4 {self._t('btn.settings')}"
        self.query_one("#btn-quit", Button).label = f"7 {self._t('btn.quit')}"
        self.query_one("#cmd", Input).placeholder = self._t("cmd.placeholder")
        # The pet panel, the suggest box and the header are built from
        # translations too, so they have to be rebuilt when the language
        # changes -- otherwise they keep rendering the previous language until
        # the next restart.
        self._refresh_pet()
        self._render_suggestions()
        self._refresh_header()

    def _refresh_header(self) -> None:
        cfg = self.nix.config
        name = self.nix.root.name or str(self.nix.root)
        mode = cfg.t(f"cmd.mode.{cfg.mode}")
        self.title = "NIX"
        self.sub_title = f"{name}  ·  {_head(mode.upper())}  ·  v{self.nix.version}"

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
        self._apply_pet_visibility()
        self._refresh_pet()
        self.query_one("#cmd", Input).focus()
        self._auto_scan_if_enabled()

    def _celebrate(self) -> None:
        self._celebrate_until = time.monotonic() + 2.0
        self._refresh_pet(animate=True)

    @property
    def _celebrating(self) -> bool:
        return time.monotonic() < self._celebrate_until

    def _tick(self) -> None:
        if not self.is_running:
            return
        self._spin = (self._spin + 1) % len(SPINNER)
        if self.nix.config.animations_enabled or self._celebrating:
            self._blink = (self._blink + 1) % 4
            self._refresh_pet(animate=True)

    def _refresh_pet(self, animate: bool = False) -> None:
        try:
            box = self.query_one("#pet-box", Static)
            name_label = self.query_one("#top-pet-name", Label)
        except (NoMatches, TooManyMatches, WrongType):
            return
        pet = self.nix.pet or {}
        if not pet:
            box.update(Text(self._t("pet.no_pet"), style=DIM))
            name_label.update(Text())
            self._set_stat("#st-mood", "", DIM)
            self._set_stat("#st-energy", "", DIM)
            self._set_stat("#st-stage", "", DIM)
            self._set_stat("#st-xp", "", DIM)
            return

        pattern = pet.get("body_pattern", "seed")
        pattern_label = self._t(f"pet.pattern.{pattern}")
        blink = animate and self._blink == 1
        look = idle_look(f"{self.nix.root}:{pet.get('name', 'pet')}")
        if getattr(self.nix.config, "avatar_enabled", True):
            art = render_avatar(pet, self.nix.root, scale=1, blink=blink,
                                look=look)
        else:
            art = Text(self._t("pet.avatar_off"), style=DIM)
        name = pet.get("name", "???")
        mood = pet.get("mood", "curious")
        mood_style = MOOD_STYLES.get(mood, FG)
        mood_label = self._t(f"mood.{mood}")
        energy = int(pet.get("energy", 100))
        age = int(pet.get("age", 0))

        decorated = Text()
        if self._celebrating:
            decorated.append(SPINNER[self._spin], style=YELLOW)
        else:
            decorated.append("  \u2726  ", style=DIM)
        decorated.append(name, style=f"bold {BLUE}")
        decorated.append("  \u2726  ", style=DIM)
        name_label.update(decorated)

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
        xp = int(pet.get("xp", 0))
        level = int(pet.get("level", 1))
        self._set_stat(
            "#st-xp",
            f"{self._t('pet.xp')}: {xp}/{50 * level}  \u00b7  "
            f"{self._t('pet.level')} {level}",
            DIM,
        )
        box.update(art)

    def _apply_pet_visibility(self) -> None:
        """Show or hide the pet panels, honouring ``tamagotchi_enabled``."""
        visible = bool(getattr(self.nix.config, "tamagotchi_enabled", True))
        for query in ("#pet-wrap", "#pet-stats", "#top-pet-name"):
            try:
                self.query_one(query).display = visible
            except Exception:
                pass

    def _apply_runtime_settings(self) -> None:
        """Push every live-applicable config field into the running widgets."""
        self._apply_clock()
        self._apply_log_limits()
        self._apply_timer()
        self._apply_history_limit()

    def _apply_clock(self) -> None:
        try:
            self.query_one(NixHeader).set_clock_visible(
                bool(self.nix.config.show_clock))
        except Exception:
            pass

    def _apply_log_limits(self) -> None:
        try:
            self._log().max_lines = int(self.nix.config.log_max_lines)
        except Exception:
            pass

    def _apply_timer(self) -> None:
        """Restart the animation timer with the configured interval."""
        interval = float(self.nix.config.animation_interval)
        if self._anim_timer is not None:
            try:
                self._anim_timer.stop()
            except Exception:
                pass
            self._anim_timer = None
        self._anim_timer = self.set_interval(interval, self._tick)

    def _apply_history_limit(self) -> None:
        """Trim the command history to ``command_history_size`` (0 clears)."""
        limit = int(self.nix.config.command_history_size)
        if limit <= 0:
            self._cmd_history.clear()
        elif len(self._cmd_history) > limit:
            del self._cmd_history[:-limit]
        self._cmd_hist_idx = None

    def _auto_scan_if_enabled(self) -> None:
        """Run one silent project scan per session when enabled."""
        if self._auto_scan_done:
            return
        if not getattr(self.nix.config, "auto_scan", True):
            return
        self._auto_scan_done = True
        try:
            info = scan_project(Path(self.nix.root))
        except Exception:
            return
        self._log().write(
            Text()
            .append(_timestamp() + " ", style=DIM)
            .append("SYSTEM ", style=BLUE)
            .append(
                self._t("sys.auto_scan", files=info.source_files,
                        lines=info.total_lines),
                style=FG,
            )
        )

    def _energy_bar(self, energy: int) -> str:
        filled = round(energy / 100 * 10)
        color = GREEN if energy >= 50 else (YELLOW if energy >= 25 else RED)
        return ("\u2588" * filled + "\u2591" * (10 - filled)).replace(
            "\u2588", f"[{color}]\u2588[/]"
        )

    def _skin_name(self, pet: dict | None) -> str:
        pet = pet or self.nix.pet or {}
        kind = pet.get("skin")
        if kind not in VARIANT_KINDS:
            try:
                kind = avatar_genes_for(self.nix.root, pet)["variant"]
            except Exception:
                kind = ""
        return self._t(f"skin.{kind}") if kind in VARIANT_KINDS else self._t("skin.random")

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
            .append(_clip(text), style=FG)
        )

    def show_help(self, groups: list[tuple[str, list[tuple[str, str]]]]) -> None:
        t = self._t
        log = self._log()
        log.write(Text("  " + _head(t("tbl.commands")), style=f"bold {BLUE}"))
        # Size the usage column to the widest entry so localized (longer) usage
        # strings get their own room instead of being clipped at a fixed 22.
        width = 22
        for _title, items in groups:
            for usage, _desc in items:
                width = max(width, min(cell_len(usage) + 2, 46))
        for title, items in groups:
            log.write(Text("    " + _head(title), style=f"bold {PURPLE}"))
            for usage, desc in items:
                log.write(
                    Text()
                    .append("      " + _ljust(usage, width), style=GREEN)
                    .append(_clip(desc), style=FG)
                )

    def show_block(self, title: str,
                   rows: list[tuple[str, str, str]]) -> None:
        self._log_write_header(self._log(), title)
        width = 24
        for label, _value, _color in rows:
            width = max(width, min(cell_len(str(label)) + 2, 40))
        for label, value, color in rows:
            self._log().write(
                Text()
                .append("    " + _ljust(label, width), style=CYAN)
                .append(_clip(str(value)), style=color)
            )

    def _log_write_header(self, log, title: str) -> None:
        log.write(Text("  " + _head(title), style=f"bold {BLUE}"))

    def show_tree(self, title: str, lines: list[str]) -> None:
        self._log_write_header(self._log(), title)
        for line in lines:
            self._log().write(Text("    " + line, style=FG))

    def show_code(self, title: str, snippet: list[str]) -> None:
        self._log_write_header(self._log(), title)
        for line in snippet:
            self._log().write(
                Text().append("    " + line, style=GREEN)
                if line.lstrip().startswith(("#", "//", "*"))
                else Text().append("    " + line, style=FG)
            )

    def show_status(self, *, root: str, mode: str, attempts: int,
                    max_attempts: int, files: int, dirs: int,
                    functions: int, classes: int,
                    source_files: int, total_lines: int) -> None:
        t = self._t
        log = self._log()
        log.write(Text("  " + _head(t("tbl.project_status")),
                       style=f"bold {BLUE}"))
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
        width = max(20, max(cell_len(f[0]) for f in fields) + 2)
        for label, value, color in fields:
            log.write(
                Text()
                .append("    " + _ljust(label, width), style=CYAN)
                .append(value, style=color)
            )

    def show_scan(self, info: "ProjectInfo") -> None:
        t = self._t
        log = self._log()
        log.write(
            Text()
            .append(f"{info.files} {t('scan.files')}  ", style=CYAN)
            .append(f"{info.directories} {t('scan.dirs')}  ", style=CYAN)
            .append(f"{info.functions} {t('scan.functions')}  ", style=CYAN)
            .append(f"{info.classes} {t('scan.classes')}  ", style=CYAN)
            .append(f"{info.total_lines:,} {t('scan.lines')}", style=CYAN)
        )
        if info.extensions:
            log.write(Text("  " + _head(t("tbl.extensions")),
                           style=f"bold {PURPLE}"))
            ext_width = max(14, max(cell_len(e) for e, _c in info.top_extensions) + 2)
            for ext, count in info.top_extensions:
                log.write(
                    Text()
                    .append("    " + _ljust(ext, ext_width), style=FG)
                    .append(str(count), style=GREEN)
                )

    def show_pet(self, pet: dict | None) -> None:
        t = self._t
        if pet is None:
            self._log().write(Text(self._t("pet.no_pet"), style=DIM))
            return
        mood = pet.get("mood", "curious")
        mood_label = t(f"mood.{mood}")
        mood_style = MOOD_STYLES.get(mood, FG)
        pattern = pet.get("body_pattern", "seed")
        look = idle_look(f"{self.nix.root}:{pet.get('name', 'pet')}")
        if getattr(self.nix.config, "avatar_enabled", True):
            art = render_avatar(pet, self.nix.root, scale=2,
                                blink=self._blink == 1, look=look)
        else:
            art = Text(t("pet.avatar_off"), style=DIM)
        rows = [
            (t("pet.name"), pet.get("name", "???"), FG),
            (t("pet.skin"), self._skin_name(pet), PURPLE),
            (t("pet.mood"), mood_label, mood_style),
            (t("pet.energy"), str(pet.get("energy", 100)), GREEN),
            (t("pet.age"), str(pet.get("age", 0)), FG),
            (t("pet.body"), t(f"pet.pattern.{pattern}"), PURPLE),
            (t("pet.stage"), str(pet.get("stage", 1)), FG),
            (t("pet.xp"), f"{pet.get('xp', 0)}/{50 * int(pet.get('level', 1))}", FG),
            (t("pet.level"), str(pet.get("level", 1)), FG),
            (t("pet.mutations"), str(pet.get("mutations_witnessed", 0)), YELLOW),
            (t("pet.failures"), str(pet.get("failures_survived", 0)), RED),
            (t("pet.scans"), str(pet.get("scans", 0)), CYAN),
            (t("pet.tags"), ", ".join(pet.get("tags", [])) or "—", CYAN),
        ]
        log = self._log()
        log.write(art)
        width = max(20, max(cell_len(r[0]) for r in rows) + 2)
        for label, value, color in rows:
            log.write(
                Text()
                .append("    " + _ljust(label, width), style=CYAN)
                .append(value, style=color)
            )

    def show_settings(self, config: "Config") -> None:
        self.push_screen(
            SettingsModal(self, config, self.nix.config_store.save),
            callback=lambda _: self._focus_cmd(),
        )

    def show_logs(self, path: object, lines: list[str]) -> None:
        t = self._t
        log = self._log()
        if not lines:
            log.write(Text(self._t("fb.no_logs"), style=DIM))
            return
        log.write(Text(f"  {_head(t('tbl.session_log'))}  {path}",
                       style=f"bold {DIM}"))
        for line in lines[-40:]:
            log.write(Text("    " + line, style=DIM))

    def show_history(self, entries: list[dict]) -> None:
        t = self._t
        log = self._log()
        if not entries:
            log.write(Text(self._t("fb.no_history"), style=DIM))
            return
        log.write(Text("  " + _head(t("tbl.journal")),
                       style=f"bold {BLUE}"))
        kind_colors = {
            "SYSTEM": DIM, "SCAN": CYAN, "PET": PURPLE, "ERROR": RED,
        }
        for entry in entries[-40:]:
            kind = entry.get("kind", "")
            log.write(
                Text()
                .append("    ", style=DIM)
                .append(f"{entry.get('ts', '')}", style=DIM)
                .append("  ", style=DIM)
                .append(f"{kind}", style=kind_colors.get(kind, FG))
                .append("  ", style=FG)
                .append(entry.get("message", ""), style=FG)
            )

    def show_error(self, text: str) -> None:
        self.show_message("ERROR", text)

    def clear_log(self) -> None:
        self._log().clear()