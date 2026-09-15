from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich import box

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

if TYPE_CHECKING:
    from .config import Config
    from .scanner import ProjectInfo

VERSION = "0.2.0"

ACCENT = "bold green"
ACCENT_DIM = "dim green"
HEADER_STYLE = "bold green"
PET_STYLE = "bold cyan"
ERROR_STYLE = "bold red"
WARN_STYLE = "bold yellow"
INFO_STYLE = "bold white"
DIM_STYLE = "dim white"

PET_FRAMES = {
    "seed": (
        "  ╭──────╮\n"
        "  │ .  . │\n"
        "  │  ▪   │\n"
        "  ╰──────╯\n"
        "    │  │"
    ),
    "sprout": (
        "  ╭──────╮\n"
        "  │ ◉  ◉ │\n"
        "  │  ▣   │\n"
        "  ╰──┬┬──╯\n"
        "     ││\n"
        "    ╱  ╲"
    ),
    "bloom": (
        "  ╭──────╮\n"
        "  │ ◉‿◉ │\n"
        "  │  ◆   │\n"
        "  ╰──┬┬──╯\n"
        "   ╱╱││╲╲\n"
        "  ╱  ╲╱  ╲"
    ),
}

MOOD_LABELS = {
    "curious": ("curious", "bold yellow"),
    "happy": ("happy", "bold green"),
    "content": ("content", "green"),
    "focused": ("focused", "bold cyan"),
    "alert": ("alert", "bold yellow"),
    "determined": ("determined", "bold magenta"),
    "thoughtful": ("thoughtful", "cyan"),
    "cautious": ("cautious", "yellow"),
    "worried": ("worried", "bold red"),
    "relieved": ("relieved", "green"),
    "tired": ("tired", "dim"),
    "anxious": ("anxious", "red"),
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _make_prompt_style() -> Style:
    return Style.from_dict({
        "prompt": "bold green",
        "input": "",
    })


class NixUI:
    def __init__(self) -> None:
        self.console = Console(
            file=sys.stdout,
            force_terminal=True,
            color_system="truecolor",
            no_color=False,
        )
        self.session = PromptSession(
            history=InMemoryHistory(),
            style=_make_prompt_style(),
            complete_while_typing=False,
            enable_open_in_editor=False,
            enable_history_search=True,
        )
        self._events: list[str] = []

    def clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _banner(self) -> Panel:
        banner_text = Text()
        banner_text.append(
            " ███╗   ██╗██╗██╗  ██╗\n"
            " ████╗  ██║██║╚██╗██╔╝\n"
            " ██╔██╗ ██║██║ ╚███╔╝ \n"
            " ██║╚██╗██║██║ ██╔██╗ \n"
            " ██║ ╚████║██║██╔╝ ██╗\n"
            " ╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝\n",
            style=HEADER_STYLE,
        )
        return Panel(
            Align.center(banner_text),
            box=box.DOUBLE,
            style=HEADER_STYLE,
            padding=(0, 1),
        )

    def _header_bar(self, project_name: str, mode: str) -> Table:
        table = Table(
            box=None, show_header=False, show_edge=False,
            padding=(0, 1), expand=True,
        )
        table.add_column(ratio=3)
        table.add_column(ratio=1, justify="right")

        left = Text()
        left.append("NIX", style="bold green")
        left.append("  ·  ", style="dim")
        left.append("LOCAL PROJECT AGENT", style="dim green")

        right = Text()
        right.append(project_name, style="bold white")
        right.append("   ", style="dim")
        right.append(mode.upper(), style="bold green")

        table.add_row(left, right)
        return table

    def _pet_panel(self, pet: dict, config: Config) -> Panel | None:
        if not config.tamagotchi_enabled or not config.avatar_enabled:
            return None

        pattern = pet.get("body_pattern", "seed")
        art = PET_FRAMES.get(pattern, PET_FRAMES["seed"])

        mood_str = pet.get("mood", "curious")
        mood_label, mood_style = MOOD_LABELS.get(mood_str, (mood_str, "white"))
        energy = pet.get("energy", 100)
        name = pet.get("name", "???")
        age = pet.get("age", 0)

        pet_info = Text()
        pet_info.append(f"{name}", style="bold cyan")
        pet_info.append(f"  ·  {mood_label}", style=mood_style)
        pet_info.append(f"  ·  energy {energy}", style="dim")
        pet_info.append(f"  ·  age {age}", style="dim")

        body = Text()
        for line in art.split("\n"):
            body.append(line + "\n", style=PET_STYLE)

        layout = Table(box=None, show_header=False, show_edge=False, padding=(0, 2))
        layout.add_column(ratio=1)
        layout.add_column(ratio=2)
        layout.add_row(Align.center(body), pet_info)

        return Panel(
            layout,
            title="[bold cyan]Pet[/]",
            box=box.ROUNDED,
            style="cyan",
            padding=(0, 1),
        )

    def draw_full(self, project_name: str, pet: dict, config: Config,
                   events: list[str] | None = None) -> None:
        self.clear_screen()

        self.console.print(self._banner())
        self.console.print()
        self.console.print(self._header_bar(project_name, config.mode))
        self.console.print()

        pet_panel = self._pet_panel(pet, config)
        if pet_panel:
            self.console.print(pet_panel)
            self.console.print()

        if events:
            log_table = Table(
                box=None, show_header=False, show_edge=False,
                padding=(0, 1), expand=True,
            )
            log_table.add_column(style="dim white", width=12)
            log_table.add_column(style="bold white", width=12)
            log_table.add_column()
            for ev in events[-15:]:
                parts = ev.split(" ", 2) if ev.startswith("[") else ["", "", ev]
                log_table.add_row(*parts)
            self.console.print(Panel(
                log_table,
                title="[dim]Events[/]",
                box=box.ROUNDED,
                style="dim",
                padding=(0, 1),
            ))
            self.console.print()

        self.console.print(
            Panel(
                Text("  Type /help for commands.", style="dim green"),
                box=box.ROUNDED,
                style=ACCENT_DIM,
                padding=(0, 1),
            )
        )
        self.console.print()

    def get_input(self) -> str:
        try:
            return self.session.prompt(HTML("<prompt>nix&gt; </prompt>")).strip()
        except (KeyboardInterrupt, EOFError):
            return "/quit"

    def show_message(self, kind: str, text: str) -> None:
        style_map = {
            "SYSTEM": INFO_STYLE,
            "SCAN": "bold cyan",
            "PET": PET_STYLE,
            "ERROR": ERROR_STYLE,
            "WARN": WARN_STYLE,
            "MUTATION": "bold magenta",
            "TEST": "bold yellow",
            "LEARN": "bold green",
            "CHECKPOINT": "bold blue",
        }
        style = style_map.get(kind.upper(), INFO_STYLE)
        stamp = _timestamp()

        line = Text()
        line.append(f"[{stamp}] ", style="dim")
        line.append(f"[{kind.upper():>10}] ", style=style)
        line.append(text, style="white" if kind.upper() != "ERROR" else ERROR_STYLE)

        self.console.print(line)
        self._events.append(f"[{stamp}] [{kind.upper():>10}] {text}")

    def show_help(self, lines: list[str]) -> None:
        table = Table(
            title="Commands",
            box=box.ROUNDED,
            style=ACCENT,
            show_header=False,
            padding=(0, 2),
        )
        table.add_column(style="bold green", min_width=28)
        table.add_column(style="white")
        for line in lines:
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                table.add_row(parts[0], parts[1])
            else:
                table.add_row(line, "")
        self.console.print(table)

    def show_status(self, *, root: str, mode: str, attempts: int,
                    max_attempts: int, files: int, dirs: int,
                    functions: int, classes: int,
                    source_files: int, total_lines: int) -> None:
        table = Table(
            title="Project Status",
            box=box.ROUNDED,
            style=ACCENT,
            expand=True,
        )
        table.add_column("Key", style="bold green", ratio=1)
        table.add_column("Value", style="white", ratio=2)

        table.add_row("Root", root)
        table.add_row("Mode", mode.upper())
        table.add_row("Attempts", f"{attempts} / {max_attempts}")
        table.add_row("Files", str(files))
        table.add_row("Directories", str(dirs))
        table.add_row("Source Files", str(source_files))
        table.add_row("Functions", str(functions))
        table.add_row("Classes", str(classes))
        table.add_row("Total Lines", f"{total_lines:,}")

        self.console.print(table)

    def show_scan(self, info: "ProjectInfo") -> None:
        self.console.print()
        self.console.print(
            Panel(
                f"[bold cyan]{info.files}[/] files  ·  "
                f"[bold cyan]{info.directories}[/] directories  ·  "
                f"[bold cyan]{info.source_files}[/] source  ·  "
                f"[bold cyan]{info.functions}[/] functions  ·  "
                f"[bold cyan]{info.classes}[/] classes  ·  "
                f"[bold cyan]{info.total_lines:,}[/] lines",
                title="[bold cyan]Scan Results[/]",
                box=box.ROUNDED,
                style="cyan",
                padding=(0, 2),
            )
        )

        if info.extensions:
            ext_table = Table(
                box=None, show_header=True, show_edge=False,
                padding=(0, 2),
            )
            ext_table.add_column("Extension", style="bold white")
            ext_table.add_column("Count", justify="right", style="bold green")
            for ext, count in info.top_extensions:
                ext_table.add_row(ext, str(count))
            self.console.print(ext_table)
        self.console.print()

    def show_pet(self, pet: dict) -> None:
        mood_str = pet.get("mood", "curious")
        mood_label, mood_style = MOOD_LABELS.get(mood_str, (mood_str, "white"))

        table = Table(
            title=f"Pet: {pet.get('name', '???')}",
            box=box.ROUNDED,
            style=PET_STYLE,
        )
        table.add_column("Attribute", style="bold cyan")
        table.add_column("Value", style="white")

        table.add_row("Name", pet.get("name", "???"))
        table.add_row("Mood", Text(mood_label, style=mood_style))
        table.add_row("Energy", str(pet.get("energy", 100)))
        table.add_row("Age", str(pet.get("age", 0)))
        table.add_row("Body", pet.get("body_pattern", "seed"))
        table.add_row("Stage", str(pet.get("stage", 1)))
        table.add_row("Evolution", str(pet.get("evolution_level", 0)))
        table.add_row("Mutations witnessed", str(pet.get("mutations_witnessed", 0)))
        table.add_row("Failures survived", str(pet.get("failures_survived", 0)))

        self.console.print(table)

    def show_settings(self, config: "Config") -> None:
        table = Table(
            title="Settings",
            box=box.ROUNDED,
            style=ACCENT,
        )
        table.add_column("Setting", style="bold green")
        table.add_column("Value", style="white")

        table.add_row("Theme", config.theme)
        table.add_row("Mode", config.mode)
        table.add_row("Attempts", f"{config.attempts}/{config.max_attempts}")
        table.add_row("Mutation budget", str(config.mutation_budget))
        table.add_row("Tamagotchi", "on" if config.tamagotchi_enabled else "off")
        table.add_row("Animations", "on" if config.animations_enabled else "off")
        table.add_row("Avatar", "on" if config.avatar_enabled else "off")
        table.add_row("Sounds", "on" if config.sounds_enabled else "off")
        table.add_row("Auto scan", "on" if config.auto_scan else "off")
        table.add_row("Checkpoint on mutate", "on" if config.checkpoint_on_mutate else "off")
        table.add_row("Git auto commit", "on" if config.git_auto_commit else "off")
        table.add_row("Protected paths",
                       ", ".join(config.protected_paths or []))

        self.console.print(table)

    def show_logs(self, path: object, lines: list[str]) -> None:
        if not lines:
            self.console.print(
                Panel("[dim]No log entries yet.[/]",
                      title="Session Log", box=box.ROUNDED, style="dim")
            )
            return

        log_text = Text()
        for line in lines:
            log_text.append(line + "\n", style="dim")

        self.console.print(
            Panel(log_text,
                  title=f"[dim]{path}[/]",
                  box=box.ROUNDED, style="dim")
        )

    def show_history(self, entries: list[dict]) -> None:
        if not entries:
            self.console.print(
                Panel("[dim]No journal entries today.[/]",
                      title="Journal", box=box.ROUNDED, style="dim")
            )
            return

        table = Table(
            title="Journal (today)",
            box=box.ROUNDED,
            style=ACCENT,
            show_header=True,
        )
        table.add_column("Time", style="dim", width=20)
        table.add_column("Kind", style="bold green", width=10)
        table.add_column("Message", style="white")

        for entry in entries:
            ts = entry.get("ts", "")
            kind = entry.get("kind", "")
            msg = entry.get("message", "")
            table.add_row(ts, kind, msg)

        self.console.print(table)

    def show_first_launch(self) -> str:
        self.console.print()
        self.console.print(Panel(
            "[bold green]Welcome to NIX![/]\n\n"
            "This is your first launch in this directory.\n"
            "NIX will create a [bold].nix/[/] directory for state.\n"
            "Stage 1 is [bold]read-only[/]: source files will NOT be mutated.\n",
            title="[bold green]First Launch[/]",
            box=box.DOUBLE,
            style="green",
            padding=(1, 2),
        ))
        self.console.print()
        while True:
            name = self.session.prompt(
                HTML("<prompt>Choose your pet's name: </prompt>")
            ).strip()
            if name:
                return name
            self.console.print("[red]Name cannot be empty.[/]")

    def show_error(self, text: str) -> None:
        self.console.print(f"[{ERROR_STYLE}]Error: {text}[/]")

    def show_welcome_back(self, pet_name: str, project: str) -> None:
        self.console.print()
        self.console.print(Panel(
            f"[bold green]Welcome back![/]\n"
            f"Pet: [bold cyan]{pet_name}[/]\n"
            f"Project: [bold white]{project}[/]",
            box=box.ROUNDED,
            style="green",
            padding=(0, 2),
        ))
