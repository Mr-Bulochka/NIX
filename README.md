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
- Buttons row — **clickable with the mouse**: Scan, Status, Pet, Settings, Help, Clear, Quit
- Scrollable color-coded event log (syntax highlighting, tables, panels)
- Command input with focus, arrow-key navigation
- Hotkeys: `Ctrl+Q` quit, `Ctrl+L` clear, `Ctrl+S` scan, `Ctrl+P` pet

## Commands

| Command | Description |
|---------|-------------|
| `help` | Show all commands |
| `status` | Current project and NIX state |
| `scan` | Read-only project inventory |
| `attempts` | Show attempt budget |
| `attempts N` | Set attempt budget |
| `attempts +N` | Add attempts |
| `attempts -N` | Remove attempts |
| `pet` | Show pet status |
| `mode [local\|safe\|git]` | Show/set safety mode |
| `pwd` | Show current working directory |
| `settings` | Open settings |
| `logs [N]` | Show session log |
| `history [N]` | Show journal history |
| `clear` | Clear the event log |
| `version` | Show NIX version |
| `quit` | Exit NIX |

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