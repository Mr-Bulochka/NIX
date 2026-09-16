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

Pets evolve and get a **new random skin** when you give them a pill (once every
30 minutes); the stage/pattern is always preserved.

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
└── origin/
```

## Development

```bat
pip install -e .
python -m unittest discover -s tests -v
python -m nix
```

## Roadmap

- **Stage A** — Foundation + modern TUI (current)
- **Stage B** — Mutation Engine + Sandbox + World Laws
- **Stage C** — Checkpoint Manager + Experience System
- **Stage D** — Destructive Testing
- **Stage E** — Git/GitHub Bridge
- **Stage F** — Tamagotchi Evolution
- **Stage G** — Full TUI polish
- **Stage H** — Integration Testing + Packaging