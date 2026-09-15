from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .app import NixApp


@dataclass
class CommandResult:
    continue_session: bool = True
    clear_screen: bool = False
    message: str = ""


@dataclass
class Command:
    name: str
    description: str
    usage: str = ""
    handler: Callable[["NixApp", list[str]], CommandResult] = field(
        default_factory=lambda: lambda app, args: CommandResult()
    )


COMMANDS: dict[str, Command] = {}


def register(name: str, description: str, usage: str = "") -> Callable:
    def decorator(fn: Callable[["NixApp", list[str]], CommandResult]) -> Callable:
        COMMANDS[name] = Command(
            name=name,
            description=description,
            usage=usage,
            handler=fn,
        )
        return fn
    return decorator


def get_command(name: str) -> Command | None:
    return COMMANDS.get(name)


def get_all_commands() -> dict[str, Command]:
    return dict(COMMANDS)


@register("help", "show help", "/help")
def cmd_help(app: "NixApp", args: list[str]) -> CommandResult:
    lines = []
    for name, cmd in sorted(COMMANDS.items()):
        usage = cmd.usage or f"/{name}"
        desc = app.t(f"cmd.{name}.desc")
        lines.append(f"  {usage:<28} {desc}")
    app.ui.show_help(lines)
    return CommandResult()


@register("status", "current project and NIX state", "/status")
def cmd_status(app: "NixApp", args: list[str]) -> CommandResult:
    from .scanner import scan_project
    info = scan_project(app.root)
    app.ui.show_status(
        root=str(app.root),
        mode=app.config.mode,
        attempts=app.config.attempts,
        max_attempts=app.config.max_attempts,
        files=info.files,
        dirs=info.directories,
        functions=info.functions,
        classes=info.classes,
        source_files=info.source_files,
        total_lines=info.total_lines,
    )
    return CommandResult()


@register("scan", "read-only project inventory", "/scan")
def cmd_scan(app: "NixApp", args: list[str]) -> CommandResult:
    from .scanner import scan_project
    info = scan_project(app.root)
    app.ui.show_scan(info)
    app.journal.write("SCAN",
                       f"files={info.files} dirs={info.directories} "
                       f"functions={info.functions}")
    app.pet = app.pet_store.update_mood(app.pet, "scan")
    app.pet_store.save(app.pet)
    return CommandResult()


@register("attempts", "show/set attempt budget", "/attempts [N|+N|-N]")
def cmd_attempts(app: "NixApp", args: list[str]) -> CommandResult:
    if not args:
        app.ui.show_message("SYSTEM", app.t(
            "fb.attempts", cur=app.config.attempts, max=app.config.max_attempts))
        return CommandResult()
    token = args[0]
    try:
        if token.startswith(("+", "-")):
            value = app.config.attempts + int(token)
        else:
            value = int(token)
        app.config.attempts = max(0, min(value, app.config.max_attempts))
        app.config_store.save(app.config)
        app.ui.show_message("SYSTEM", app.t(
            "fb.attempts_set", cur=app.config.attempts, max=app.config.max_attempts))
    except ValueError:
        app.ui.show_message("ERROR", app.t("fb.attempts_invalid"))
    return CommandResult()


@register("pet", "show pet status", "/pet")
def cmd_pet(app: "NixApp", args: list[str]) -> CommandResult:
    app.ui.show_pet(app.pet)
    return CommandResult()


@register("mode", "show safety mode", "/mode [local|safe|git]")
def cmd_mode(app: "NixApp", args: list[str]) -> CommandResult:
    if not args:
        app.ui.show_message("SYSTEM", app.t("fb.mode", mode=app.config.mode))
        return CommandResult()
    new_mode = args[0].lower()
    from .config import VALID_MODES
    if new_mode not in VALID_MODES:
        app.ui.show_message("ERROR",
                            app.t("cmd.mode.valid", modes=", ".join(VALID_MODES)))
        return CommandResult()
    app.config.mode = new_mode
    app.config_store.save(app.config)
    app.ui.show_message("SYSTEM", app.t("fb.mode_set", mode=new_mode))
    app.journal.write("SYSTEM", f"mode changed to {new_mode}")
    return CommandResult()


@register("settings", "show current settings", "/settings")
def cmd_settings(app: "NixApp", args: list[str]) -> CommandResult:
    app.ui.show_settings(app.config)
    return CommandResult()


@register("logs", "show session log path or recent entries", "/logs [N]")
def cmd_logs(app: "NixApp", args: list[str]) -> CommandResult:
    if args:
        try:
            n = int(args[0])
        except ValueError:
            n = 20
    else:
        n = 20
    lines = app.session_logger.read_last(n)
    app.ui.show_logs(app.session_logger.path, lines)
    return CommandResult()


@register("history", "show journal history", "/history [N]")
def cmd_history(app: "NixApp", args: list[str]) -> CommandResult:
    n = 30
    if args:
        try:
            n = int(args[0])
        except ValueError:
            pass
    entries = app.journal.read_today()[-n:]
    app.ui.show_history(entries)
    return CommandResult()


@register("clear", "clear the event log", "/clear")
def cmd_clear(app: "NixApp", args: list[str]) -> CommandResult:
    app.ui.clear_log()
    return CommandResult()


@register("quit", "exit NIX", "/quit")
def cmd_quit(app: "NixApp", args: list[str]) -> CommandResult:
    app.journal.write("SYSTEM", "session ended by user")
    app.session_logger.write("SYSTEM", "session ended by user")
    return CommandResult(continue_session=False)


@register("version", "show NIX version", "/version")
def cmd_version(app: "NixApp", args: list[str]) -> CommandResult:
    from . import __version__
    app.ui.show_message("SYSTEM", app.t("fb.version", version=__version__))
    return CommandResult()


@register("pwd", "show current working directory", "/pwd")
def cmd_pwd(app: "NixApp", args: list[str]) -> CommandResult:
    app.ui.show_message("SYSTEM", str(app.root))
    app.journal.write("SYSTEM", f"pwd queried: {app.root}")
    return CommandResult()
