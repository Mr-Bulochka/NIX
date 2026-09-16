# NIX — Local Project Testing Agent

NIX is a local-first terminal agent that lives inside your project directory. It scans, analyzes, mutates, tests, and learns — all through a rich, modern TUI (Text User Interface) in the terminal.

## Quick Start

**Windows 10/11 + Python 3.11+**

```bat
cd C:\MyProject
nix
```

or run from the source:

```bat
python -m nix
```

On first launch, NIX creates a `.nix/` directory and asks for your pet's name.

## The Interface

NIX runs as a full-screen terminal application (built on [Textual](https://github.com/Textualize/textual)) — like opencode or Claude Code:

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
| `gen <type> <name> [--into f] [--at N] [--apply] [--params .. --ret .. --doc .. --body ..]` | Generate code from a template (preview unless `--into`; `--apply` writes) |
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

## `.nix/` Structure

```
.nix/
├── config.json
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

```bat
pip install -e .
python -m unittest discover -s tests -v
python -m nix
```

## Roadmap

- **Stage A** — Foundation + modern TUI (done)
- **Stage B** — Code modules + project brain: structural engine, `defs`/`blocks`/`wrap`/`gen`/`rename` + `git` companion (current)
- **Stage C** — Mutation Engine + Sandbox + World Laws
- **Stage D** — Checkpoint Manager + Experience System
- **Stage E** — Destructive Testing
- **Stage F** — GitHub/GitLab Bridge
- **Stage G** — Tamagotchi Evolution
- **Stage H** — Full TUI polish
- **Stage I** — IDE daemon + protocol (NIX as a language-agnostic senior multi-tool)