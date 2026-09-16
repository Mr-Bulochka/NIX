from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from .state import utc_now_iso

if TYPE_CHECKING:
    from .app import NixApp

from .scanner import IGNORED_DIRS
from .avatar import VARIANT_KINDS

FG = "#c7ccd4"
CYAN = "#85d3f5"
GREEN = "#7fb572"
YELLOW = "#d4a35c"


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


# ---- constructor helpers -------------------------------------------
# Every command is a constructor: positional words + --flag value,
# -flag switches and k=v pairs, combinable into one long mega-command.
# Separate several commands on one line with ';' or '&&'.


def parse_flags(args: list[str]) -> tuple[dict[str, str | bool], list[str]]:
    flags: dict[str, str | bool] = {}
    rest: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            body = a[2:]
            if "=" in body:
                k, v = body.split("=", 1)
                flags[k] = v
            else:
                if i + 1 < len(args) and not args[i + 1].startswith("-"):
                    flags[body] = args[i + 1]
                    i += 1
                else:
                    flags[body] = True
        elif a.startswith("-") and len(a) > 1 and not a[1:].lstrip("+-").isdigit():
            flags[a[1:]] = True
        else:
            rest.append(a)
        i += 1
    return flags, rest


def _num(value, default: int) -> int:
    if value is None:
        return default
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


LANG_NAMES = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JSX", ".tsx": "TSX", ".rs": "Rust", ".go": "Go",
    ".java": "Java", ".c": "C", ".h": "C", ".cpp": "C++",
    ".php": "PHP", ".rb": "Ruby", ".cs": "C#", ".swift": "Swift",
    ".kt": "Kotlin", ".html": "HTML", ".css": "CSS", ".json": "JSON",
    ".md": "Markdown", ".toml": "TOML", ".yaml": "YAML", ".yml": "YAML",
    ".sh": "Shell", ".bat": "Batch",
}


def _walk(root: Path, max_depth: int | None = None):
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        depth = len(Path(dirpath).relative_to(root).parts)
        if max_depth is not None and depth >= max_depth:
            dirnames[:] = []
        yield Path(dirpath), dirnames, filenames


def _tree_lines(root: Path, depth: int = 2, files: bool = True) -> list[str]:
    root = Path(root)
    lines: list[str] = []

    def rec(dirp: Path, prefix: str, level: int) -> None:
        try:
            raw = sorted(dirp.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            return
        items = [p for p in raw if p.name not in IGNORED_DIRS]
        if not files:
            items = [p for p in items if p.is_dir()]
        for i, p in enumerate(items):
            last = i == len(items) - 1
            line = prefix
            line += "\u2514\u2500\u2500 " if last else "\u251c\u2500\u2500 "
            line += p.name + ("/" if p.is_dir() else "")
            lines.append(line)
            if p.is_dir() and (depth is None or level < depth):
                rec(p, prefix + ("    " if last else "\u2502   "), level + 1)

    rec(root, "", 0)
    return lines


def _ls_lines(path: Path, all_: bool = False, size: bool = False) -> list[str]:
    lines: list[str] = []
    try:
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except OSError:
        return lines
    for p in entries:
        if not all_ and p.name.startswith("."):
            continue
        if p.is_dir():
            lines.append(p.name + "/")
        elif size:
            try:
                sz = p.stat().st_size
            except OSError:
                sz = 0
            lines.append(f"{p.name}  ({sz:,} B)")
        else:
            lines.append(p.name)
    return lines


def _notes_path(app: "NixApp") -> Path:
    return app.state.nix / "memory" / "notes.txt"


# ---- help ----------------------------------------------------------


@register("help", "show help", "help [command]")
def cmd_help(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    if rest:
        name = rest[0].lower()
        cmd = get_command(name)
        if cmd is None:
            app.ui.show_message("ERROR", app.t("fb.unknown", name=name))
            return CommandResult()
        app.ui.show_block(app.t("tbl.command"), [
            (cmd.usage, app.t(f"cmd.{cmd.name}.desc") or "", GREEN),
        ])
        return CommandResult()

    groups = []
    for title, names in (
        (app.t("help.grp.core"), ["help", "version", "pwd", "time", "echo", "which"]),
        (app.t("help.grp.project"),
         ["scan", "status", "stats", "tree", "ls", "lang", "tests",
          "deps", "find", "todo"]),
        (app.t("help.grp.pet"), ["pet", "pill", "settings", "tag"]),
        (app.t("help.grp.memory"), ["note", "memory", "journal"]),
        (app.t("help.grp.safety"), ["mode", "attempts", "save"]),
        (app.t("help.grp.system"), ["logs", "history", "checkpoint",
                                    "clear", "quit"]),
    ):
        items = []
        for name in names:
            cmd = get_command(name)
            if cmd is None:
                continue
            usage = cmd.usage or name
            items.append((usage, app.t(f"cmd.{name}.desc")))
        if items:
            groups.append((title, items))
    app.ui.show_help(groups)
    return CommandResult()


@register("which", "show info about a command", "which <command>")
def cmd_which(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    name = rest[0] if rest else ""
    cmd = get_command(name) if name else None
    if cmd is None:
        app.ui.show_message("ERROR", app.t("fb.which_unknown", name=name or "?"))
        return CommandResult()
    desc = app.t(f"cmd.{name}.desc") or cmd.description
    app.ui.show_block(app.t("tbl.command"), [
        (cmd.usage, desc, GREEN),
    ])
    return CommandResult()


# ---- project -------------------------------------------------------


@register("status", "current project and NIX state", "status")
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


@register("scan", "read-only project inventory", "scan [--tree] [--depth N] [--top N]")
def cmd_scan(app: "NixApp", args: list[str]) -> CommandResult:
    from .scanner import scan_project
    flags, rest = parse_flags(args)
    info = scan_project(app.root)
    if flags.get("tree"):
        depth = _num(flags.get("depth"), 2)
        app.ui.show_tree(app.t("tbl.tree"),
                         _tree_lines(app.root, depth=depth, files=True))
    else:
        app.ui.show_scan(info)
    app.journal.write("SCAN",
                       f"files={info.files} dirs={info.directories} "
                       f"functions={info.functions}")
    app.pet = app.pet_store.update_mood(app.pet, "scan")
    app.pet_store.save(app.pet)
    return CommandResult()


@register("stats", "full project analytics", "stats [--top N]")
def cmd_stats(app: "NixApp", args: list[str]) -> CommandResult:
    from .scanner import scan_project
    flags, rest = parse_flags(args)
    top = _num(flags.get("top"), 10)
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
    rows = []
    for ext, count in sorted(info.extensions.items(),
                             key=lambda x: (-x[1], x[0]))[:top]:
        lang = LANG_NAMES.get(ext, ext)
        rows.append((lang, f"{ext}  \u00d7{count}", GREEN))
    if rows:
        app.ui.show_block(app.t("tbl.languages"), rows)
    app.journal.write("SCAN", f"stats: {info.files} files {info.total_lines} lines")
    return CommandResult()


@register("tree", "show project tree", "tree [--depth N]")
def cmd_tree(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    depth = _num(flags.get("depth"), 2)
    lines = _tree_lines(app.root, depth=depth, files=True)
    app.ui.show_tree(app.t("tbl.tree"), lines)
    return CommandResult()


@register("ls", "list a directory", "ls [path] [--all] [--size]")
def cmd_ls(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    target = rest[0] if rest else None
    path = (app.root / target).resolve() if target else app.root
    if not path.exists():
        app.ui.show_message("ERROR", app.t("fb.not_found", name=path))
        return CommandResult()
    lines = _ls_lines(path,
                      all_=bool(flags.get("all")),
                      size=bool(flags.get("size")))
    app.ui.show_tree(f"{app.t('tbl.files')} \u00b7 {path}", lines)
    return CommandResult()


@register("lang", "detect languages in the project", "lang [--top N]")
def cmd_lang(app: "NixApp", args: list[str]) -> CommandResult:
    from .scanner import scan_project
    flags, rest = parse_flags(args)
    top = _num(flags.get("top"), 16)
    info = scan_project(app.root)
    if not info.extensions:
        app.ui.show_message("SYSTEM", app.t("scan.no_ext"))
        return CommandResult()
    rows = []
    for ext, count in sorted(info.extensions.items(),
                             key=lambda x: (-x[1], x[0]))[:top]:
        lang = LANG_NAMES.get(ext, ext)
        rows.append((lang, f"{ext}  \u00d7{count}", CYAN))
    app.ui.show_block(app.t("tbl.languages"), rows)
    return CommandResult()


@register("tests", "find test files and test functions", "tests [--max N] [--count]")
def cmd_tests(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    max_ = _num(flags.get("max"), 30)
    count_only = bool(flags.get("count"))
    found = []
    test_dirs = {"tests", "test"}
    n_files = 0
    n_funcs = 0
    for dirpath, dirnames, filenames in _walk(app.root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fn in filenames:
            if not fn.lower().endswith((".py", ".js", ".ts")):
                continue
            rel = Path(dirpath).relative_to(app.root)
            is_test = fn.lower().startswith("test_") or \
                fn.lower().endswith("_test") or \
                any(p.lower() in test_dirs for p in rel.parts)
            if not is_test:
                continue
            n_files += 1
            funcs = []
            try:
                text = (Path(dirpath) / fn).read_text(
                    encoding="utf-8", errors="ignore")
            except OSError:
                text = ""
            for line in text.splitlines():
                s = line.strip()
                if re.match(r"def\s+test_", s):
                    funcs.append(s.split("(", 1)[0].replace("def ", "").strip())
            n_funcs += len(funcs)
            if count_only:
                continue
            name = (rel / fn).as_posix()
            if funcs:
                found.append(f"{name}  \u00b7 {len(funcs)} test(s)")
            else:
                found.append(name)
            if max_ and len(found) >= max_:
                break
        if max_ and len(found) >= max_:
            break
    if count_only or not found:
        app.ui.show_message(
            "SYSTEM",
            app.t("fb.test_summary", files=n_files, funcs=n_funcs))
        return CommandResult()
    app.ui.show_tree(app.t("tbl.tests"), found)
    app.ui.show_message("SYSTEM",
                        app.t("fb.test_summary", files=n_files, funcs=n_funcs))
    return CommandResult()


@register("deps", "collect imported modules", "deps [--top N]")
def cmd_deps(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    top = _num(flags.get("top"), 20)
    counts: dict[str, int] = {}
    for dirpath, _, filenames in _walk(app.root):
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            try:
                text = (Path(dirpath) / fn).read_text(
                    encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for m in re.finditer(
                    r"^\s*(?:from\s+([A-Za-z_]\w*)|import\s+([A-Za-z_]\w*))",
                    text, re.M):
                mod = m.group(1) or m.group(2)
                base = mod.split(".")[0]
                if base not in ("nix", "__future__"):
                    counts[base] = counts.get(base, 0) + 1
    if not counts:
        app.ui.show_message("SYSTEM", app.t("fb.no_deps"))
        return CommandResult()
    rows = [(mod, f"\u00d7{n}", CYAN)
            for mod, n in sorted(counts.items(), key=lambda x: -x[1])[:top]]
    app.ui.show_block(app.t("tbl.deps"), rows)
    return CommandResult()


@register("find", "search files by name", "find <name> [--ext py,js] [--max N]")
def cmd_find(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    query = (rest[0] if rest else "").lower()
    if not query:
        app.ui.show_message("ERROR", app.t("fb.missing_arg"))
        return CommandResult()
    exts = {("." + e.strip().lstrip(".")) for e in
            str(flags.get("ext", "")).split(",") if e.strip()}
    max_ = _num(flags.get("max"), 50)
    hits = []
    for dirpath, dirnames, filenames in _walk(app.root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fn in filenames:
            if query in fn.lower():
                if exts and not fn.lower().endswith(tuple(exts)):
                    continue
                hits.append(str((Path(dirpath).relative_to(app.root) / fn).as_posix()))
                if max_ and len(hits) >= max_:
                    break
        if max_ and len(hits) >= max_:
            break
    if not hits:
        app.ui.show_message("SYSTEM", app.t("fb.not_found", name=query))
        return CommandResult()
    app.ui.show_tree(app.t("tbl.find"), hits)
    return CommandResult()


@register("todo", "scan code for TODO/FIXME/XXX", "todo [--max N]")
def cmd_todo(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    max_ = _num(flags.get("max"), 50)
    src_ext = (".py", ".js", ".ts", ".rs", ".go", ".java", ".c", ".cpp",
               ".h", ".rb", ".php")
    found = []
    for dirpath, _, filenames in _walk(app.root):
        for fn in filenames:
            if not fn.lower().endswith(src_ext):
                continue
            p = Path(dirpath) / fn
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = p.relative_to(app.root).as_posix()
            for i, line in enumerate(text.splitlines(), 1):
                if re.search(r"\b(?:TODO|FIXME|XXX)\b", line):
                    found.append(f"{rel}:{i}  {line.strip()[:70]}")
                    if max_ and len(found) >= max_:
                        return _finish_todo(app, found)
    if not found:
        app.ui.show_message("SYSTEM", app.t("fb.no_todos"))
        return CommandResult()
    return _finish_todo(app, found)


def _finish_todo(app: "NixApp", found: list[str]) -> CommandResult:
    app.ui.show_block(app.t("tbl.todos"), [(s, "", YELLOW) for s in found])
    count = app.t("fb.todo_summary", n=len(found))
    app.ui.show_message("SYSTEM", count)
    return CommandResult()


# ---- pet -----------------------------------------------------------


@register("pet", "show pet status", "pet")
def cmd_pet(app: "NixApp", args: list[str]) -> CommandResult:
    app.ui.show_pet(app.pet)
    return CommandResult()


@register("pill", "give a skin-changing pill", "pill [--status]")
def cmd_pill(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    if flags.get("status"):
        pet = app.pet or {}
        kind = pet.get("skin")
        if kind not in VARIANT_KINDS:
            from .avatar import genes_for
            kind = genes_for(app.root, pet)["variant"]
        skin = app.t(f"skin.{kind}")
        rem = app.pill_remaining()
        if rem is None or rem <= 0:
            suffix = app.t("set.pill_ready")
        else:
            minutes = int(rem // 60) + (1 if rem % 60 else 0)
            suffix = app.t("set.pill_cd", min=minutes)
        app.ui.show_message("SYSTEM", f"{skin}  \u00b7  {suffix}")
        return CommandResult()
    ok, msg = app.give_pill()
    if ok:
        app.ui._refresh_pet()
    app.ui.show_message("SYSTEM" if ok else "ERROR", msg)
    return CommandResult()


@register("tag", "list/add/remove pet tags", "tag [name] [--remove]")
def cmd_tag(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    pet = app.pet
    if pet is None:
        app.ui.show_message("ERROR", app.t("pet.no_pet"))
        return CommandResult()
    tags = pet.setdefault("tags", [])
    name = rest[0] if rest else ""
    if not name:
        label = ", ".join(tags) if tags else app.t("fb.no_tags")
        app.ui.show_message("SYSTEM", app.t("fb.tags", tags=label))
        return CommandResult()
    if flags.get("remove"):
        if name in tags:
            tags.remove(name)
            app.pet_store.save(pet)
            app.journal.write("PET", f"tag removed: {name}")
            app.ui.show_message("SYSTEM", app.t("fb.tag_removed", tag=name))
        else:
            app.ui.show_message("ERROR", app.t("fb.not_found", name=name))
        return CommandResult()
    if name not in tags:
        tags.append(name)
        app.pet_store.save(pet)
        app.journal.write("PET", f"tag added: {name}")
    app.ui.show_message("SYSTEM", app.t("fb.tag_added", tag=name))
    return CommandResult()


@register("settings", "open settings", "settings")
def cmd_settings(app: "NixApp", args: list[str]) -> CommandResult:
    app.ui.show_settings(app.config)
    return CommandResult()


# ---- memory --------------------------------------------------------


@register("note", "save an idea to project memory", "note <text>")
def cmd_note(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    text = " ".join(rest).strip()
    if not text:
        app.ui.show_message("ERROR", app.t("fb.missing_arg"))
        return CommandResult()
    path = _notes_path(app)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"[{utc_now_iso()}] {text}\n")
    app.journal.write("MEMORY", text)
    app.ui.show_message("SYSTEM", app.t("fb.note_saved"))
    return CommandResult()


@register("memory", "show recent project notes", "memory [N]")
def cmd_memory(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    n = _num(flags.get("n") or (rest[0] if rest else None), 10)
    path = _notes_path(app)
    if not path.exists():
        app.ui.show_message("SYSTEM", app.t("fb.no_memory"))
        return CommandResult()
    lines = [ln for ln in path.read_text(
        encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
    if not lines:
        app.ui.show_message("SYSTEM", app.t("fb.no_memory"))
        return CommandResult()
    app.ui.show_tree(app.t("tbl.notes"), lines[-n:])
    return CommandResult()


@register("journal", "write a journal entry", "journal <text>")
def cmd_journal(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    text = " ".join(rest).strip()
    if not text:
        app.ui.show_message("ERROR", app.t("fb.missing_arg"))
        return CommandResult()
    app.journal.write("NOTE", text)
    app.ui.show_message("SYSTEM", app.t("fb.journal_saved"))
    return CommandResult()


# ---- safety / state ------------------------------------------------


@register("attempts", "show/set attempt budget", "attempts [N|+N|-N]")
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


@register("mode", "show safety mode", "mode [local|safe|git]")
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


@register("save", "persist config and pet", "save")
def cmd_save(app: "NixApp", args: list[str]) -> CommandResult:
    app.config_store.save(app.config)
    if app.pet:
        app.pet_store.save(app.pet)
    app.journal.write("SYSTEM", "state saved")
    app.ui.show_message("SYSTEM", app.t("fb.saved"))
    return CommandResult()


@register("checkpoint", "list or create checkpoints", "checkpoint [name]")
def cmd_checkpoint(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    tmp = app.state.nix / "checkpoints" / "temporary"
    perm = app.state.nix / "checkpoints" / "permanent"
    if rest:
        name = rest[0]
        slug = re.sub(r"[^A-Za-z0-9\-_]", "-", name).strip("-") or "manual"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        dest = tmp / f"{ts}-{slug}"
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            app.ui.show_message("ERROR", app.t("fb.failed", name="checkpoint",
                                               exc=exc))
            return CommandResult()
        manifest = {
            "created": utc_now_iso(),
            "root": str(app.root),
            "mode": app.config.mode,
            "stage": (app.pet or {}).get("body_pattern", "seed"),
            "skin": (app.pet or {}).get("skin"),
        }
        (dest / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8")
        app.journal.write("CHECKPOINT", f"created {dest.name}")
        app.ui.show_message("SYSTEM",
                            app.t("fb.checkpoint_created", name=dest.name))
        return CommandResult()
    rows = []
    for kind_path, kind in ((tmp, "temp"), (perm, "permanent")):
        for p in sorted(kind_path.glob("*")):
            if p.is_dir():
                rows.append((p.name, kind, CYAN))
    if not rows:
        app.ui.show_message("SYSTEM", app.t("fb.no_checkpoints"))
        return CommandResult()
    app.ui.show_block(app.t("tbl.checkpoints"), rows)
    return CommandResult()


# ---- info / system -------------------------------------------------


@register("logs", "show session log path or recent entries", "logs [N]")
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


@register("history", "show journal history", "history [N]")
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


@register("clear", "clear the event log", "clear")
def cmd_clear(app: "NixApp", args: list[str]) -> CommandResult:
    app.ui.clear_log()
    return CommandResult()


@register("quit", "exit NIX", "quit")
def cmd_quit(app: "NixApp", args: list[str]) -> CommandResult:
    app.journal.write("SYSTEM", "session ended by user")
    app.session_logger.write("SYSTEM", "session ended by user")
    return CommandResult(continue_session=False)


@register("version", "show NIX version", "version")
def cmd_version(app: "NixApp", args: list[str]) -> CommandResult:
    from . import __version__
    app.ui.show_message("SYSTEM", app.t("fb.version", version=__version__))
    return CommandResult()


@register("pwd", "show current working directory", "pwd")
def cmd_pwd(app: "NixApp", args: list[str]) -> CommandResult:
    app.ui.show_message("SYSTEM", str(app.root))
    app.journal.write("SYSTEM", f"pwd queried: {app.root}")
    return CommandResult()


@register("echo", "print text to the log", "echo <text>")
def cmd_echo(app: "NixApp", args: list[str]) -> CommandResult:
    flags, rest = parse_flags(args)
    text = " ".join(rest).strip()
    if not text:
        app.ui.show_message("ERROR", app.t("fb.missing_arg"))
        return CommandResult()
    app.ui.show_message("ECHO", text)
    return CommandResult()


@register("time", "show current UTC time", "time")
def cmd_time(app: "NixApp", args: list[str]) -> CommandResult:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    app.ui.show_message("SYSTEM", app.t("fb.time", time=now))
    return CommandResult()