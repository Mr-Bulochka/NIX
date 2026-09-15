# NIX — Local Project Testing Agent

NIX is a local-first terminal agent that lives inside your project directory. It scans, analyzes, mutates, tests, and learns — all through a rich terminal interface.

## Quick Start

**Windows 10/11 + Python 3.11+**

```bat
cd C:\MyProject
nix.bat
```

or:

```bat
python -m nix
```

On first launch, NIX creates a `.nix/` directory and asks for your pet's name.

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/status` | Current project and NIX state |
| `/scan` | Read-only project inventory |
| `/attempts` | Show attempt budget |
| `/attempts N` | Set attempt budget |
| `/attempts +N` | Add attempts |
| `/attempts -N` | Remove attempts |
| `/pet` | Show pet status |
| `/mode [local\|safe\|git]` | Show/set safety mode |
| `/settings` | Current settings |
| `/logs [N]` | Show session log |
| `/history [N]` | Show journal history |
| `/clear` | Redraw interface |
| `/version` | Show NIX version |
| `/quit` | Exit NIX |

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
pip install rich prompt_toolkit
python -m unittest discover -s tests -v
python -m nix
```

## Roadmap

- **Stage A** — Foundation (current)
- **Stage B** — Mutation Engine + Sandbox + World Laws
- **Stage C** — Checkpoint Manager + Experience System
- **Stage D** — Destructive Testing
- **Stage E** — Git/GitHub Bridge
- **Stage F** — Tamagotchi Evolution
- **Stage G** — Full TUI
- **Stage H** — Integration Testing + Packaging
