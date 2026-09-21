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


class _RecordingUI(_StubUI):
    def __init__(self):
        self.errors = []
        self.shown_code = []

    def show_message(self, kind, text):
        if kind == "ERROR":
            self.errors.append(text)

    def show_code(self, *args):
        self.shown_code.append(args)


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

    def test_scan_auto_detects_priority_language(self):
        from nix.app import NixApp
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                Path(tmp, "app.py").write_text(
                    "print('hello')\n", encoding="utf-8")
                Path(tmp, "util.py").write_text(
                    "def f(): pass\n", encoding="utf-8")
                Path(tmp, "script.js").write_text(
                    "console.log(1)\n", encoding="utf-8")
                app = NixApp()
                app.ui = _StubUI()
                app.pet = app.pet_store.create("Tester")
                app.config.priority_lang = ""
                from nix.commands import cmd_scan
                cmd_scan(app, [])
                self.assertEqual(app.config.priority_lang, "python")
                self.assertEqual(app.config_store.load().priority_lang,
                                 "python")
            finally:
                os.chdir(old)

    def test_scan_keeps_manual_priority(self):
        from nix.app import NixApp
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                Path(tmp, "app.py").write_text(
                    "print('hello')\n", encoding="utf-8")
                app = NixApp()
                app.ui = _StubUI()
                app.pet = app.pet_store.create("Tester")
                app.config.priority_lang = "go"
                from nix.commands import cmd_scan
                cmd_scan(app, [])
                self.assertEqual(app.config.priority_lang, "go")
            finally:
                os.chdir(old)

    def test_wrap_shorthand_op_name(self):
        from nix.app import NixApp
        from nix.commands import cmd_wrap
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                Path(tmp, "app.py").write_text(
                    "def main():\n    print('hi')\n", encoding="utf-8")
                app = NixApp()
                ui = _RecordingUI()
                app.ui = ui
                app.pet = app.pet_store.create("Tester")
                cmd_wrap(app, ["app.py", "2", "in", "try"])
                self.assertEqual(ui.errors, [])
                joined = " ".join(
                    str(part) for args in ui.shown_code for part in args)
                self.assertIn("try:", joined)
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
