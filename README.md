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
  <img src="https://raw.githubusercontent.com/Mr-Bulochka/NIX/master/docs/screenshots/main.svg"
       alt="NIX main screen" width="820">
</p>

> Live main view of the TUI — pet panel, buttons, event log and command
> input. A real headless render of the actual app, exported as an SVG.

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
- **World laws + mutation engine** — every write is checked against the
  sandbox's world laws (protected paths, budgets) and each applied mutation
  is recorded (`laws`, `mutations`)
- **Checkpoint manager + pet XP** — snapshot and restore project checkpoints
  (`checkpoint`, permanent/temporary, with protection and backup files);
  every checkpoint and mutation earns the pet experience (`pet`, `status`)
- **Git companion** — status, diff, log, branch, auto-messaged commits,
  remote info and optional `gh`/`glab` PR support
- **IDE daemon** — headless JSON-line protocol over stdin/stdout or a socket
- Chain commands on one line with `;` or `&&`

## Install

### From PyPI (recommended)

```bash
pip install cli-nix
nix
```

Upgrade to the latest published version with `pip install -U cli-nix`.
Prefer an isolated environment? `uv tool install cli-nix` installs the `nix`
command in its own environment and leaves your system Python untouched.

### From a git clone (any platform)

**uv (fast — Python 3.11+ on any platform)**

```bash
git clone https://github.com/Mr-Bulochka/NIX.git
cd NIX
uv sync
uv run nix          # or: uv run python -m nix
```

**Alternative — plain pip (Python 3.11+)**

Windows 10/11:

```bat
git clone https://github.com/Mr-Bulochka/NIX.git
cd NIX
python -m pip install -r requirements.txt
python -m nix
```

Linux / macOS:

```bash
git clone https://github.com/Mr-Bulochka/NIX.git
cd NIX
python3 -m pip install -r requirements.txt
python3 -m nix
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
| `run [--timeout N]` | Run all tests |
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
| `laws` | Show sandbox world laws and limits |
| `mutations` | Show recent mutation engine records |
| `destruct [--apply] [--keep] [--timeout N] [--max N]` | Destructive testing: mutate the project and verify tests catch it (dry-run unless `--apply`) |

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
deterministic toolkit. Every request is one line; every response is one JSON
object per line (JSON Lines).

```
nix daemon                     # line protocol over stdin/stdout (JSON Lines)
nix daemon --socket 127.0.0.1:7411
nix daemon --once "status"     # one command, one JSON response + exit code
```

#### Transport

- **stdin** (default): read one line per request, write one envelope per
  response, forever. A response with `session_end: true` ends the session.
- **`--socket host:port`**: TCP server (`127.0.0.1:7411`). Each connection is
  one request/response session; `session_end: true` closes it.
- **`--once "text"`**: run exactly one request, print one envelope, exit.

`--once` and `--socket` are mutually exclusive; extra positional arguments
after either flag are a usage error. All protocol input and output is UTF-8;
diagnostics (e.g. the listening banner) go to stderr so stdout stays
parseable JSON Lines.

#### Envelope

```
{"ok": bool, "session_end": bool, "events": [...]}
```

- `ok` — `false` when the request could not be completed; then `error`
  carries a human-readable reason.
- `session_end` — `true` only after `quit`/`exit` or a command chain that
  ends the session. The client must then stop sending requests.
- `events` — ordered command output, re-renderable verbatim:
  `message`, `block`, `code`, `tree`, `pet`, `status`, `scan`, `logs`,
  `history`, `help`. Empty for `HELP`.
- `commands` (only on `HELP`) — the full command table as
  `[{"name", "description", "usage"}, ...]`.

Examples:

```
> HELP
{"ok": true, "session_end": false, "commands": [{"name": "defs", ...}]}
> defs
{"ok": true, "session_end": false, "events": [{"op": "block", "title": "Symbols", ...}]}
> status; quit
{"ok": true, "session_end": true, "events": [{"op": "status", ...}]}
> definitely_not_a_command
{"ok": false, "session_end": false, "events": [], "error": "unknown command: definitely_not_a_command"}
```

`PING` answers `{"ok": true, "session_end": false, "events": []}` and is the
liveness check.

#### Request parsing

One request line may hold several commands separated by `;`. Every token is
parsed with the same tokenizer the TUI uses (quotes and escapes included);
the first token of each command is its name, the rest are its arguments and
are passed to the very handlers `COMMANDS` registers. A command that fails
mid-way still delivers the events it already emitted, but the envelope is
`ok: false` with `error`. A request that makes no sense at the protocol level
(unknown command, malformed line) is never answered with a fake `ok: true`.

#### Exit codes

| Mode | Code | Meaning |
|------|------|---------|
| `--once` | 0 | `ok: true` |
| `--once` | 1 | `ok: false` (command failure) |
| any | 2 | usage/parse error (no envelope, message on stderr) |

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
uv sync                       # create the env, install the package + dev deps
uv run pytest                 # run the test suite (pytest, with subtests)
uv run python -m nix          # start the TUI
```

## Release

The version is kept in three places — `VERSION`, `pyproject.toml` and
`nix/__init__.py`. `tests/test_version.py` fails the build if they drift
apart, so bump all three together.

### Publish a new version

1. Update the version in `VERSION`, `pyproject.toml` and `nix/__init__.py`
2. Add the release entry to `CHANGELOG.md`
3. Commit, then tag the commit with `v<version>` (e.g. `v0.3.9`) and push the tag

Pushing the tag runs `.github/workflows/release.yml`, which verifies the tag
matches the project version, runs the tests, builds the sdist and wheel,
validates the metadata with `twine check`, creates the GitHub Release and
publishes to PyPI.

### One-time PyPI setup

Publishing uses [trusted publishing](https://docs.pypi.org/trusted-publishers/),
so no API token is stored in the repository. Add a pending publisher on
pypi.org for the `cli-nix` project:

| Field | Value |
|-------|-------|
| Repository | `Mr-Bulochka/NIX` |
| Workflow | `release.yml` |
| Environment | `release` |

The `release` environment is configured with required reviewers if you want
an approval gate before anything reaches PyPI.

### Check a build locally

```bash
uv build
uv run --group dev twine check dist/*
```

The wheel embeds all bundled language modules, so a plain
`pip install dist/cli_nix-<version>-py3-none-any.whl` gives a working install.

### Backfilling an unpublished version

Versions `0.3.2`–`0.3.8` were released on GitHub but never uploaded to PyPI.
To publish one, go to **Actions → Release → Run workflow** and set
`backfill_ref` to a tag or a commit SHA:

| Version | `backfill_ref` |
|---------|----------------|
| 0.3.2 | `c4d7975` |
| 0.3.3 | `6eb9d44` |
| 0.3.4 | `f471f3d` |
| 0.3.5 | `v0.3.5` |
| 0.3.6 | `v0.3.6` |
| 0.3.7 | `v0.3.7` |
| 0.3.8 | `v0.3.8` |

The backfill job checks out the historical ref, builds from it, and uploads
with `skip-existing: true` — so it can never overwrite a file that is already
on PyPI. Each ref is independent, so run it once per version.

## License

[MIT-0](LICENSE) — the code is free to use, copy, modify, merge, publish,
distribute, sublicense, or sell, with **no obligations** to the author.

That said, it would make my day if you mention the author or link to this
repository — purely as a nice-to-have, never a requirement.

## Roadmap

- **Stage A** — Foundation + modern TUI (done)
- **Stage B** — Code modules + project brain: structural engine, `defs`/`blocks`/`wrap`/`gen`/`rename` + `git` companion (done)
- **Stage C** — Mutation Engine + Sandbox + World Laws (done)
- **Stage D** — Checkpoint Manager + Experience System (done)
- **Stage E** — Destructive Testing (done)
- **Stage F** — GitHub/GitLab Bridge (done)
- **Stage G** — Tamagotchi Evolution (done): 8 skins, XP-driven level-up mood,
  rewarding pill (cooldown + skin change), mood/energy drain on failed commands,
  None-pet crash guards
- **Stage H** — Full TUI polish (done): celebration flash + pill state badge
  (cooldown/ready), keyboard-first settings (Esc closes, Enter applies),
  command history navigation (Up/Down), global hotkeys (Ctrl+1/3/4/6),
  ringing status banner, error/warning color coding
- **Stage I** — IDE daemon + protocol (done: `nix daemon`, see above; plugins per-editor remain)