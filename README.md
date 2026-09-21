<div align="center">

<pre>
    _   _______  __
   / | / /  _/ |/ /
  /  |/ // / |   / 
 / /|  // / /   |  
/_/ |_/___//_/|_|  
</pre>

# NIX — Local Project Testing Agent

A local-first terminal agent that lives inside your project directory.
It scans, analyzes, mutates, tests, and learns — all through a rich,
modern TUI in the terminal.

![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT--0-brightgreen)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![TUI](https://img.shields.io/badge/built_on-Textual-8BE9FD)

</div>

---

## Screenshot

<p align="center">
  <img src="https://raw.githubusercontent.com/Mr-Bulochka/NIX/master/docs/screenshots/main.jpg"
       alt="NIX main screen" width="820">
</p>

> Live main view of the TUI — pet panel, buttons, event log and command
> input. A real headless render of the actual app, exported as a JPG.

## Features

- Full-screen terminal UI built on [Textual](https://github.com/Textualize/textual)
  — like opencode or Claude Code
- **Pet companion** — a tamagotchi that lives in your repo, evolves, and
  gets a new skin every `pill` (8 skins, 30-minute cooldown)
- **Language modules** — plain-data packs (no code) describing how blocks,
  operations and generation work per language
- **Project brain** — `.nix/brain/` index of functions/classes/patterns that
  the pet rebuilds on demand (always fresher than the developer's memory)
- **Read-only by default** — dry-runs for everything (scan, status, git,
  gen, wrap, rename): nothing changes unless `--apply`
- **Git companion** — status, diff, log, branch, auto-messaged commits,
  remote info and optional `gh`/`glab` PR support
- **IDE daemon** — headless JSON-line protocol over stdin/stdout or a socket
- Chain commands on one line with `;` or `&&`

## Install

### From a git clone (any platform)

**Windows 10/11 + Python 3.11+**

```bat
git clone https://github.com/Mr-Bulochka/NIX.git
cd NIX
python -m pip install -r requirements.txt
python -m nix
```

**Linux / macOS + Python 3.11+**

```bash
git clone https://github.com/Mr-Bulochka/NIX.git
cd NIX
python3 -m pip install -r requirements.txt
python3 -m nix
```

### From PyPI

```bash
pip install cli-nix
nix
```

### From the latest GitHub Release

Check the **Releases** tab for the current `.whl`, then:

```bash
pip install https://github.com/Mr-Bulochka/NIX/releases/download/v0.3.0/cli_nix-0.3.0-py3-none-any.whl
nix
```

### Platform support

NIX is pure Python (3.11+) with two cross-platform dependencies
(`rich`, `textual`) — the same code runs on Windows, Linux and macOS.
The `nix` console command is created by the package entry point and works
everywhere; `nix.bat` in the repo root is just a Windows convenience
launcher equivalent to `python -m nix`.

## Quick Start

```bash
cd C:\MyProject        # or /home/you/myproject on Linux/macOS
nix                    # or: python -m nix
```

On first launch, NIX creates a `.nix/` directory and asks for your pet's name.

## The Interface

- Header bar with project name, safety mode and live clock
- Pet panel with animated idle spinner and stats
- Buttons row — **clickable with the mouse**: Pet, Scan, Status, Settings, Quit
- Scrollable color-coded event log (syntax highlighting, tables, panels)
- Command input with focus, arrow-key navigation
- Hotkeys: `Ctrl+Q` quit, `Ctrl+L` clear, `Ctrl+S` scan, `Ctrl+P` pet

## Commands

Every command is a **constructor**: positional words + `--flag value`, `-flag`
switches and `k=v` pairs, all combinable on one infinite-length line. Chain
several commands in a single line with `;` or `&&`.

| Command | Description |
|---------|-------------|
| `help [cmd]` | Show all commands, or details of one |
| `which <cmd>` | Show info about a command |
| `status` | Current project and NIX state |
| `stats [--top N]` | Full project analytics |
| `scan [--tree] [--depth N]` | Read-only project inventory |
| `tree [--depth N]` | Show project tree |
| `ls [path] [--all] [--size]` | List a directory |
| `lang [--top N]` | Detect languages in the project |
| `tests [--max N] [--count]` | Find test files and functions |
| `deps [--top N]` | Collect imported modules |
| `find <name> [--ext py,js]` | Search files by name |
| `todo [--max N]` | Scan code for TODO/FIXME |
| `attempts [N\|+N\|-N]` | Show/set attempt budget |
| `mode [local\|safe\|git]` | Show/set safety mode |
| `save` | Persist config and pet |
| `pet` | Show pet status |
| `pill [--status]` | Give the pet a skin pill (30 min cooldown) |
| `settings` | Open settings |
| `tag [name] [--remove]` | List/add/remove pet tags |
| `note <text>` | Save an idea to project memory |
| `memory [N]` | Show recent project notes |
| `journal <text>` | Write a journal entry |
| `logs [N]` | Show session log |
| `history [N]` | Show journal history |
| `checkpoint [name]` | List or create checkpoints |
| `echo <text>` | Print text to the log |
| `time` | Show current UTC time |
| `pwd` | Show current working directory |
| `version` | Show NIX version |
| `clear` | Clear the event log |
| `quit` | Exit NIX |

### Code & language modules

NIX understands code through **code modules** (language modules) —
plain-data packs (no code) that describe how blocks, operations and
generation work in a given language. Bundled modules live in
`nix/modules/bundled/`; user modules are picked up from
`~/.nix/modules/<id>/` and shadow bundled ones.

| Command | Description |
|---------|-------------|
| `module [name]` | List language modules or show one in detail |
| `defs [--max N] [glob]` | List project functions/classes (from the project index) |
| `blocks <file> <line>` | Show the block enclosing a line |
| `wrap <file> <line> in <op> [--slot v] [--apply]` | Wrap a block in a language op (dry-run unless `--apply`) |
| `gen <type> <name> [--into f] [--at N] [--apply] [--params .. --ret .. --doc .. --body ..]` | Generate code from a template (preview unless `--into`; `--apply` writes into it or creates a new file) |
| `make <entity> [--cols name:str:pk,...] [--into f] [--test-into f] [--apply]` | Scaffold a model + CRUD + tests from column specs (dry-run unless `--apply`; language inferred from `--into` extension or `--lang`, an unsupported hint is an error) |
| `testgen <file\|all> [--into f] [--apply]` | Generate test stubs from the project index (dry-run unless `--apply`) |
| `recipe [list\|<name>] [--apply] [args...]` | Run named command chains; built-ins: `feature`, `scaffold`, `test`; user recipes live in `.nix/recipes.json` (`{0}`, `{1}`, ... are positional args; re-run with `--apply` to write) |
| `rename <old> <new> [--file f] [--apply]` | Project-wide symbolic rename (dry-run unless `--apply`) |
| `ident` | Show the project's identity patterns (naming, docstrings, ...) |

### Version control companion

| Command | Description |
|---------|-------------|
| `git status` | Short working-tree status |
| `git log [N]` | Last N commits oneline |
| `git diff` | Change statistics |
| `git branch` | Current branch |
| `git commit [msg] [--apply]` | Stage all and commit; message auto-generated from diff (dry-run unless `--apply`) |
| `remote info` | Show origin, platform (GitHub/GitLab/other), branch, ahead/behind |
| `remote fetch` / `pull` / `push` | Remote sync, dry-run unless `--apply` |
| `remote pr` | List open PRs/MRs via `gh`/`glab`; `remote pr "title" --apply` opens one |

### IDE daemon & protocol (Stage I)

NIX runs headless without the TUI, so any IDE/editor can drive the same
deterministic toolkit:

```
nix daemon                     # line protocol over stdin/stdout (JSON Lines)
nix daemon --socket 127.0.0.1:7411
nix daemon --once "status"     # one command, one JSON response
```

Each request is one line; each response is one JSON object:

```
> HELP
{"ok": true, "session_end": false, "commands": [{"name": "defs", ...}]}
> defs
{"ok": true, "session_end": false, "events": [{"op": "block", "title": "Symbols", ...}]}
> quit
{"ok": true, "session_end": true}
```

Commands are the exact `COMMANDS` the TUI uses; events are ordered
(`message`, `block`, `code`, `tree`, `pet`, `status`, `scan`, `logs`,
`history`, `help`) and re-renderable by the client verbatim.

Module layout:

```
nix/modules/bundled/python/
├── module.json     id, name, version, extensions
├── blocks.json     block start regex + body mode (indent/braces/do-end)
├── ops.json        semantic ops (wrap-in-try, wrap-in-if, ...)
├── gen/*.tmpl      generation templates (function, class, ...)
└── probe.json      self-test cases
```

The pet's memory of a project lives in `.nix/brain/` (`index.json`,
`patterns.json`) and is (re)built by `defs`/`ident`/`gen` on demand, so
the pet always knows the project fresher than the developer does.

Pets evolve and get a **new random skin** when you give them a pill (once every
30 minutes); the stage/pattern is always preserved. Each of the 8 skins has
its own signature palette, so every pill is a visible transformation.

## Learning how a project works

NIX is interesting when it can *change* things. Try, in order:

```text
status          # what is here
scan            # inventory (read-only)
lang            # what languages live here
ident           # how this project is written
defs            # what functions/classes exist
wrap src/app.py 12 in try      # dry-run proposed edit
gen function login --into src/app.py   # preview a generated function
recipe feature "my idea text"
```

Everything stays a dry-run until you add `--apply`.

## `.nix/` Structure

```
.nix/
├── config.json
├── recipes.json
├── state/
├── journal/
├── logs/
├── memory/
├── experiments/
├── checkpoints/
│   ├── permanent/
│   └── temporary/
├── pet/
│   └── identity.json
├── brain/
│   ├── index.json
│   ├── patterns.json
│   └── backups/
└── origin/
```

## Development

```bash
pip install -e .
python -m unittest discover -s tests -v
python -m nix
```

## Build a release

```bash
pip install build
python -m build
```

Produces `dist/cli_nix-<version>*.whl` and `.tar.gz` (the wheel embeds
all bundled language modules). Attach both to a GitHub Release to let anyone
`pip install` the program directly.

## License

[MIT-0](LICENSE) — the code is free to use, copy, modify, merge, publish,
distribute, sublicense, or sell, with **no obligations** to the author.

That said, it would make my day if you mention the author or link to this
repository — purely as a nice-to-have, never a requirement.

## Roadmap

- **Stage A** — Foundation + modern TUI (done)
- **Stage B** — Code modules + project brain: structural engine, `defs`/`blocks`/`wrap`/`gen`/`rename` + `git` companion (done)
- **Stage C** — Mutation Engine + Sandbox + World Laws (current)
- **Stage D** — Checkpoint Manager + Experience System
- **Stage E** — Destructive Testing
- **Stage F** — GitHub/GitLab Bridge
- **Stage G** — Tamagotchi Evolution
- **Stage H** — Full TUI polish
- **Stage I** — IDE daemon + protocol (done: `nix daemon`, see above; plugins per-editor remain)