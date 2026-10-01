# Changelog

All notable changes to NIX are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.10] - 2026-10-01

### Fixed
- The animation timer no longer raises after the screen has been torn down.
  `_tick()` now returns early when the app is not running, and `_refresh_pet()`
  treats a missing/ambiguous `#pet-box` or `#top-pet-name` as a no-op instead of
  letting `NoMatches` escape. A late tick from a queued timer used to fail an
  otherwise unrelated test.

### Changed
- The release workflow is now idempotent. A tag push updates an existing GitHub
  release and re-uploads assets with `--clobber` instead of failing, and the
  PyPI publish step uses `skip-existing`, so a re-run of a tag no longer breaks
  mid-way.
- The `backfill_ref` job rebuilds the assets, creates *or* updates the GitHub
  release, and publishes to PyPI. It now verifies that the requested tag matches
  the `pyproject.toml` version and that the tag resolves to the checked-out
  commit, so a wrong ref fails loudly instead of publishing a mismatched build.

## [0.3.9] - 2026-09-30

### Added
- Seven new settings, all editable in the settings modal and applied live:
  header clock, log line limit, animation interval, command history size,
  pill cooldown, default command timeout and protected paths.
- Declarative settings registry (`SettingSpec` / `SETTING_SPECS`) that drives
  modal layout, validation and the derived `TOGGLE_KEYS` / `INT_KEYS` /
  `FLOAT_KEYS` / `PATHS_KEYS` maps. The autocomplete-specific maps remain
  available as compatibility aliases.
- `show_clock`, `log_max_lines`, `animation_interval`,
  `command_history_size`, `pill_cooldown_minutes`, `default_command_timeout`
  and `protected_paths` config fields, all bounded and normalized on load.
- Public `parse_path_list()` helper: splits on comma, semicolon and newline,
  trims entries, drops empties, normalizes separators, removes duplicates and
  preserves order.
- New "Input & history" settings section in EN and RU.

### Changed
- `nix.bat` now launches the local checkout via `pushd "%~dp0"` and prefers
  `.venv\Scripts\python.exe -m nix`, falling back to `python`. Previously the
  launcher depended on the caller's working directory, which broke
  `State.nix` (it resolves paths from `Path.cwd()`).
- Apply re-reads every settings control from the DOM instead of relying only on
  `Input.Submitted`, so typed-but-unsubmitted values are no longer lost.
- The settings modal is generated from the registry, and the header clock is
  toggled in place through `#hdr-clock` / `#hdr-noclock` because Textual
  `Header.__init__` has no runtime `show_clock` parameter.
- Pill cooldown is read from config; `0` disables it. The hardcoded cooldown is
  gone and values are capped at 1440 minutes.
- `cmd_run` and `cmd_destruct` use the configured command timeout instead of
  the internal runner default. The internal `timeout=10` in `nix/git.py` is
  unchanged.
- Command history is trimmed to `command_history_size` after every submitted
  command; `0` clears it.

### Fixed
- Startup auto-scan no longer produces UI, journal or mood side effects.
  Checkpoints plus `Git.add_file(path)` give a target-only auto-commit, so
  auto-scan can no longer commit unrelated working-tree changes.
- Values written via `setattr()` are no longer left unnormalized; Apply
  explicitly re-runs `protected_paths` normalization because `setattr()` does
  not trigger `Config.__post_init__()`.
- Invalid numeric input now keeps the settings modal open and leaves the
  stored config untouched, instead of silently applying.
- Fixed the EN label `"set.section_input"`, which was left as a raw key.
- The sdist now ships `VERSION` and `CHANGELOG.md`. `MANIFEST.in` shipped
  `tests/` but omitted `VERSION`, so the version-consistency test raised
  `FileNotFoundError` for anyone running the suite from an unpacked sdist.
  The sdist is now self-verifying.

### Tests
- 301 tests pass (`12 subtests`), including new regression coverage for
  settings persistence, clamping, rejection of non-numeric input, path
  normalization, live clock/log/timer/history apply and command-history
  trimming.

## [0.3.8] - 2026-09-28

### Added
- v1 IDE daemon protocol (`nix daemon`): strict UTF-8 decoding, request envelope
  with an explicit `error` field instead of a fake-success ERROR event, and
  TUI-compatible tokenized parsing with multi-command chunk dispatch.
- `--help` / `-h` support; usage errors exit with code 2 (`--once` and `--socket`
  are mutually exclusive; each now requires exactly one argument).
- `--once` exits with code 1 when the command fails; the socket server keeps
  accepting new connections after a `session_end` response.
- Rewrote the daemon test suite: 30 tests across in-process and subprocess modes
  (`--once`, `--help`, stdin, socket).

### Fixed
- Non-UTF-8 input on stdin/socket is answered with `ok: false` and
  `error: invalid UTF-8` instead of a silently mangled success envelope.
- The stdin loop now stops after a `session_end: true` response.

## [0.3.7] - 2026-09-27

### Added
- Full TUI polish pass:
  - Celebrate flash animation on successful actions.
  - Pill badge showing the active command/context.
  - Keyboard-first settings modal navigation.
  - Command history navigation in the input.
  - Hotkeys for common actions.
  - Ringing banner highlights.
  - Color coding across log/status elements.
- 6 new tests covering the Stage H polish behavior.
- Completed Stage H.

## [0.3.6] - 2026-09-25

### Added
- Cache remote state on `fetch`, `pull`, and `push`; cached state is shown in
  remote info.
- Adopted `uv` lockfile with a dev dependency group; README updated to the
  `uv` workflow.
- Completed Stage G.

## [0.3.5] - 2026-09-24

### Added
- `run` and `destruct` commands.
- README and screenshot refresh for the release.

## [0.3.4] - 2026-09-23

### Added
- Checkpoint manager: create, list, inspect, promote, restore, delete
  checkpoints.
- Pet XP gained from checkpoints and mutations.

## [0.3.3] - 2026-09-22

### Added
- Mutation engine with sandboxing.
- World laws (`laws`/`mutations` commands).
- Guarded mutation restore.

### Fixed
- Failing stub commands.

## [0.3.2] - 2026-09-21

### Fixed
- Wrap shorthand op-name lookup (`wrap X in try` now resolves correctly to
  `wrap-in-try`), with a regression test.
- Completed Stage B.

## [0.3.1] - 2026-09-20

### Fixed
- README screenshot URLs now point to `raw.githubusercontent.com` so they
  render on PyPI now that the repository is public.

## [0.3.0] - 2026-09-20

### Changed
- Renamed the PyPI package to `cli-nix` (`nix-agent` was rejected by PyPI as
  too similar to an existing package).

### Added
- First tagged release bundling the Stage A-F foundation:
  - Full-screen terminal UI built on Textual with a pixel-art pet companion.
  - Bilingual i18n with first-launch language picker and language auto-detect.
  - Project brain and code modules (`nix/modules`) with generated file output,
    rename, and git companion commands.
  - Scaffolding: `make`, `testgen`, `recipe` commands with dry-run and
    headless stubs.
  - Remote bridge with GitHub/GitLab platform detection and pull-request
    support.
  - IDE daemon with headless protocol (stdin/socket/once) and BOM-tolerant
    brain scanning.
  - Interactive settings modal with apply button, responsive layout, and
    plus/minus modifiers.
  - CLI robustness: multi-word flags, diff stat for binaries, keep-focus
    input.
  - Release packaging with bundled modules in the wheel.
- MIT-0 license (no attribution required).

[Unreleased]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.9...HEAD
[0.3.9]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.8...v0.3.9
[0.3.8]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.7...v0.3.8
[0.3.7]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.6...v0.3.7
[0.3.6]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Mr-Bulochka/NIX/releases/tag/v0.3.0