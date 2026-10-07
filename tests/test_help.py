"""Regression guards for the `help` / `which` command surfaces.

Four defects motivated this file:

1. `help` and `which` rendered `Command.usage` straight from the registry, so
   the `cmd.<name>.usage` translation overrides in `nix/i18n.py` were dead.
2. `nix help` never listed `laws` or `mutations`, hiding 2 of 47 commands.
3. The `make` / `testgen` registry usage strings omitted flags the handlers
   already accepted.
4. `checkpoint` usage advertised the subcommands but not `restore --force` /
   `--dry`.
"""

import types
import unittest

from nix.commands import (
    COMMANDS,
    HELP_GROUP_NAMES,
    _usage,
    cmd_help,
    cmd_which,
)
from nix.i18n import LANGUAGES


class _StubUI:
    def __init__(self):
        self.help_groups = []
        self.blocks = []

    def show_message(self, kind, text):
        pass

    def show_block(self, title, rows):
        self.blocks.append((title, list(rows)))

    def show_help(self, groups):
        self.help_groups = groups


class _StubApp:
    """Minimal `NixApp` surface: `config.language`, `config.t`, `ui`."""

    def __init__(self, language="en"):
        self.config = types.SimpleNamespace(language=language)
        self.ui = _StubUI()

    def t(self, key, **kwargs):
        from nix.i18n import t as translate
        return translate(self.config.language, key, **kwargs)


def _listed_command_names():
    names = []
    for _title_key, group in HELP_GROUP_NAMES:
        for name in group:
            if name in COMMANDS:
                names.append(name)
    return names


class TestHelpCoverage(unittest.TestCase):
    def test_every_registered_command_is_listed(self):
        self.assertEqual(sorted(_listed_command_names()), sorted(COMMANDS))

    def test_no_command_listed_twice(self):
        names = _listed_command_names()
        self.assertEqual(len(names), len(set(names)))

    def test_help_output_matches_registry(self):
        app = _StubApp()
        cmd_help(app, [])
        shown = [
            cmd
            for _title, items in app.ui.help_groups
            for cmd, _desc in items
        ]
        self.assertEqual(len(shown), len(COMMANDS))


class TestUsageResolution(unittest.TestCase):
    @staticmethod
    def _table(language):
        from nix.i18n import DEFAULT_LANGUAGE, TRANSLATIONS
        return TRANSLATIONS.get(language) or TRANSLATIONS[DEFAULT_LANGUAGE]

    def test_translation_override_wins(self):
        overrides_seen = 0
        for language in LANGUAGES:
            table = self._table(language)
            app = _StubApp(language)
            for name, cmd in COMMANDS.items():
                expected = table.get(f"cmd.{name}.usage")
                if expected is None:
                    continue
                overrides_seen += 1
                with self.subTest(language=language, command=name):
                    self.assertEqual(_usage(app, cmd), expected)
        self.assertGreater(overrides_seen, 0, "no usage overrides exercised")

    def test_falls_back_to_registry_usage(self):
        for language in LANGUAGES:
            table = self._table(language)
            app = _StubApp(language)
            for name, cmd in COMMANDS.items():
                if table.get(f"cmd.{name}.usage") is not None:
                    continue
                with self.subTest(language=language, command=name):
                    self.assertEqual(_usage(app, cmd), cmd.usage or cmd.name)

    def test_never_leaks_a_translation_key(self):
        for language in LANGUAGES:
            app = _StubApp(language)
            for name, cmd in COMMANDS.items():
                with self.subTest(language=language, command=name):
                    resolved = _usage(app, cmd)
                    self.assertNotIn("cmd.", resolved)
                    self.assertTrue(resolved.strip())

    def test_unknown_language_falls_back_to_english(self):
        app = _StubApp("zz-not-a-language")
        for name, cmd in COMMANDS.items():
            with self.subTest(command=name):
                self.assertEqual(_usage(app, cmd), cmd.usage or cmd.name)


class TestRegistryUsageAccuracy(unittest.TestCase):
    def test_make_usage_lists_supported_flags(self):
        usage = COMMANDS["make"].usage
        for flag in ("--cols", "--into", "--test-into", "--apply", "--lang"):
            with self.subTest(flag=flag):
                self.assertIn(flag, usage)

    def test_testgen_usage_lists_supported_flags(self):
        usage = COMMANDS["testgen"].usage
        for flag in ("--into", "--apply", "--lang"):
            with self.subTest(flag=flag):
                self.assertIn(flag, usage)

    def test_checkpoint_usage_lists_subcommands_and_restore_flags(self):
        usage = COMMANDS["checkpoint"].usage
        for token in ("create", "list", "info", "promote", "restore",
                      "delete", "--force", "--dry"):
            with self.subTest(token=token):
                self.assertIn(token, usage)


class TestWhichAndSingleCommandHelp(unittest.TestCase):
    def test_which_uses_localized_usage(self):
        app = _StubApp("en")
        cmd_which(app, ["make"])
        title, rows = app.ui.blocks[-1]
        self.assertEqual(rows[0][0], _usage(app, COMMANDS["make"]))

    def test_help_single_command_uses_localized_usage(self):
        app = _StubApp("en")
        cmd_help(app, ["checkpoint"])
        _title, rows = app.ui.blocks[-1]
        self.assertEqual(rows[0][0], _usage(app, COMMANDS["checkpoint"]))

    def test_help_unknown_command_reports_error(self):
        app = _StubApp()
        cmd_help(app, ["definitely-not-a-command"])
        self.assertEqual(app.ui.blocks, [])


class TestLocalizedUsageWidth(unittest.TestCase):
    """Russian usage strings are much longer than the old fixed 22-char column.

    The help table used ``usage.ljust(22)``, which silently did nothing once the
    localized string exceeded 22 characters, so every such row pushed its
    description out of alignment.
    """

    def test_russian_usage_exceeds_the_old_fixed_column(self):
        # Guards the premise of the bug: if this ever stops being true the
        # dynamic column below is no longer needed.
        app = _StubApp("ru")
        over = [
            name for name, cmd in COMMANDS.items()
            if len(_usage(app, cmd)) > 22
        ]
        self.assertTrue(over, "expected some RU usage strings longer than 22")

    def test_every_russian_usage_string_is_non_empty(self):
        app = _StubApp("ru")
        for name, cmd in COMMANDS.items():
            with self.subTest(name=name):
                usage = _usage(app, cmd)
                self.assertTrue(usage)
                self.assertNotIn("cmd.", usage)

    def test_help_rows_carry_localized_usage_under_ru(self):
        app = _StubApp("ru")
        cmd_help(app, [])
        shown = [usage
                 for _title, items in app.ui.help_groups
                 for usage, _desc in items]
        self.assertEqual(len(shown), len(COMMANDS))
        # Cyrillic usage text must reach the table, not a raw registry string
        # and not a raw i18n key.
        self.assertTrue(any(usage == _usage(app, COMMANDS["make"])
                            for usage in shown))
        self.assertTrue(any(usage == _usage(app, COMMANDS["recipe"])
                            for usage in shown))
        for usage in shown:
            self.assertNotIn("cmd.", usage)


if __name__ == "__main__":
    unittest.main()
