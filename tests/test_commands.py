import os
import tempfile
import unittest
from pathlib import Path

from nix.commands import COMMANDS, get_command, CommandResult, parse_flags


class _StubUI:
    def show_message(self, kind, text):
        pass

    def show_block(self, *args):
        pass

    def show_tree(self, *args):
        pass

    def _refresh_pet(self):
        pass

    def show_help(self, *args):
        pass

    def show_status(self, **kwargs):
        pass

    def show_scan(self, *args):
        pass

    def show_pet(self, *args):
        pass

    def show_logs(self, *args):
        pass

    def show_code(self, *args):
        pass

    def show_history(self, *args):
        pass

    def show_error(self, *args):
        pass

    def clear_log(self):
        pass


class TestCommands(unittest.TestCase):
    def test_all_commands_registered(self):
        self.assertIn("help", COMMANDS)
        self.assertIn("status", COMMANDS)
        self.assertIn("scan", COMMANDS)
        self.assertIn("attempts", COMMANDS)
        self.assertIn("pet", COMMANDS)
        self.assertIn("mode", COMMANDS)
        self.assertIn("settings", COMMANDS)
        self.assertIn("logs", COMMANDS)
        self.assertIn("history", COMMANDS)
        self.assertIn("clear", COMMANDS)
        self.assertIn("quit", COMMANDS)
        self.assertIn("version", COMMANDS)
        self.assertIn("pwd", COMMANDS)
        for name in ("pill", "tree", "ls", "lang", "tests", "deps", "find",
                     "todo", "note", "memory", "journal", "tag",
                     "checkpoint", "save", "echo", "time", "which", "stats",
                     "module", "defs", "blocks", "wrap", "gen", "ident",
                     "rename", "git", "remote"):
            self.assertIn(name, COMMANDS)

    def test_get_command(self):
        self.assertIsNotNone(get_command("help"))
        self.assertIsNone(get_command("nonexistent"))

    def test_command_result_defaults(self):
        r = CommandResult()
        self.assertTrue(r.continue_session)
        self.assertFalse(r.clear_screen)

    def test_parse_flags(self):
        flags, rest = parse_flags(
            ["--depth", "2", "--ext=py,js", "-all", "name", "-5"])
        self.assertEqual(flags["depth"], "2")
        self.assertEqual(flags["ext"], "py,js")
        self.assertTrue(flags["all"])
        self.assertEqual(rest, ["name", "-5"])

    def test_chained_commands(self):
        from nix.app import NixApp
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                app = NixApp()
                app.ui = _StubUI()
                app.pet = app.pet_store.create("Tester")
                calls = []
                from nix.commands import get_all_commands
                for name in ("version", "echo"):
                    calls.append(get_all_commands()[name])
                self.assertTrue(app.handle_command("version; echo hello"))
                self.assertFalse(app.handle_command("version; quit"))
            finally:
                os.chdir(old)

    def test_pill_cooldown(self):
        from nix.avatar import VARIANT_KINDS
        from nix.app import NixApp
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                app = NixApp()
                app.ui = _StubUI()
                app.pet = app.pet_store.create("Tester")
                ok, msg = app.give_pill()
                self.assertTrue(ok)
                self.assertIn(app.pet["skin"], VARIANT_KINDS)
                self.assertGreater(app.pill_remaining(), 0)
                first_skin = app.pet["skin"]
                ok2, msg2 = app.give_pill()
                self.assertFalse(ok2)
                self.assertEqual(app.pet["skin"], first_skin)
                app.pet["last_pill_at"] = 0
                ok3, _ = app.give_pill()
                self.assertTrue(ok3)
                self.assertNotEqual(app.pet["skin"], first_skin)
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
