# Changelog

All notable changes to NIX are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

## [0.3.6] - 2026-09-25

### Added
- Cache remote state on `fetch`, `pull`, and `push`; cached state is shown in
  remote info.
- Adopted `uv` lockfile with a dev dependency group; README updated to the
  `uv` workflow.

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

[Unreleased]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.7...HEAD
[0.3.7]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.6...v0.3.7
[0.3.6]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/Mr-Bulochka/NIX/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Mr-Bulochka/NIX/releases/tag/v0.3.0