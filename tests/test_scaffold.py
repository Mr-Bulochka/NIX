"""Tests for make, testgen, recipe commands and scaffold engine."""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from nix.commands import get_command, COMMANDS


class _UI:
    def __init__(self):
        self.shown: list[tuple[str, str]] = []
        self.code_shown: list[tuple[str, list[str]]] = []
        self.blocks: list[tuple[str, list]] = []

    def show_message(self, kind, msg):
        self.shown.append((kind, msg))

    def show_code(self, title, lines):
        self.code_shown.append((title, lines))

    def show_block(self, title, rows):
        self.blocks.append((title, rows))


class _Journal:
    def __init__(self):
        self.entries: list[tuple[str, str]] = []

    def write(self, kind, msg):
        self.entries.append((kind, msg))


class _PetStore:
    def __init__(self):
        self.pet = MagicMock()
        self.pet.name = "testpet"
        self.moods: list[str] = []

    def update_mood(self, pet, mood):
        self.moods.append(mood)

    def save(self, pet):
        pass


class _State:
    def __init__(self, tmp):
        self.nix = tmp / ".nix"
        self.nix.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, object] = {}

    def read_json(self, path):
        p = self.nix / path
        if p.exists():
            return json.loads(p.read_text("utf-8"))
        return None

    def write_json(self, path, data):
        p = self.nix / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

    def remove_json(self, path):
        p = self.nix / path
        if p.exists():
            p.unlink()


class _FakeMutations:
    def __init__(self):
        self.records = []

    def check_laws(self, path):
        return None

    def record(self, kind, target, backup):
        self.records.append({"kind": kind, "target": str(target), "backup": str(backup)})

    @property
    def count(self):
        return len(self.records)

    def remaining(self):
        return 10


class _Rec:
    def __init__(self, tmp):
        self.mutations = _FakeMutations()
        self.ui = _UI()
        self.journal = _Journal()
        self.pet_store = _PetStore()
        self.pet = self.pet_store.pet
        self.state = _State(tmp)
        self.config = MagicMock()
        self.config.mode = "suggest"
        self.config.attempts = 0
        self.config.max_attempts = 3
        self.config.lang = "en"
        self.config.priority_lang = ""
        self.root = tmp
        self.brain = MagicMock()
        self.brain.load.return_value = (
            {"files": 1, "symbols": [
                {"kind": "function", "name": "get_user",
                 "file": "core.py", "line": 1, "end": 5},
                {"kind": "class", "name": "UserService",
                 "file": "core.py", "line": 10, "end": 30},
            ]},
            {"naming_top": "snake_case", "functions": 1,
             "function_doc_ratio": 0.5, "exception_var": "e"},
        )
        self.brain.build.return_value = self.brain.load.return_value[0]

    def t(self, key, **kw):
        from nix.i18n import t
        return t(self.config.lang, key, **kw)


def _fire(app, name, args):
    cmd = get_command(name)
    return cmd.handler(app, args)


class TestParseColumns(unittest.TestCase):
    def test_simple(self):
        from nix.scaffold import parse_columns
        cols = parse_columns("name:str:pk,age:int,email:str:opt")
        self.assertEqual(len(cols), 3)
        self.assertTrue(cols[0].is_pk)
        self.assertFalse(cols[1].is_pk)
        self.assertTrue(cols[2].is_optional)

    def test_single(self):
        from nix.scaffold import parse_columns
        cols = parse_columns("title:str")
        self.assertEqual(len(cols), 1)
        self.assertEqual(cols[0].name, "title")

    def test_empty_fallback(self):
        from nix.scaffold import parse_columns
        cols = parse_columns("")
        self.assertEqual(len(cols), 0)


class TestBuildSlots(unittest.TestCase):
    def test_basic(self):
        from nix.scaffold import parse_columns, build_slots
        cols = parse_columns("name:str:pk,age:int")
        slots = build_slots("user", cols, "models.user")
        self.assertEqual(slots["Ent"], "User")
        self.assertEqual(slots["snake"], "user")
        self.assertEqual(slots["upper"], "USER")
        self.assertEqual(slots["pk_name"], "name")
        self.assertEqual(slots["module"], "models.user")
        self.assertIn("name: str", slots["fields"])
        self.assertIn("age: int = 0", slots["fields"])


class TestMake(unittest.TestCase):
    def test_no_args_shows_error(self, tmp=Path("/tmp/_test_make")):
        app = _Rec(tmp)
        _fire(app, "make", [])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("ERROR", kinds)

    def test_preview_mode(self):
        tmp = Path("/tmp/_test_make_preview")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        _fire(app, "make", ["user", "--cols", "name:str:pk,age:int"])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("SCAFFOLD", kinds)
        self.assertIn("SYSTEM", kinds)
        self.assertTrue(len(app.ui.code_shown) > 0)

    def test_apply_writes_files(self):
        tmp = Path("/tmp/_test_make_apply")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        into = str(tmp / "user.py")
        test_into = str(tmp / "test_user.py")
        _fire(app, "make", ["user", "--cols", "name:str:pk,age:int",
                            "--into", into, "--test-into", test_into,
                            "--apply"])
        self.assertTrue(Path(into).exists())
        content = Path(into).read_text("utf-8")
        self.assertIn("class User:", content)
        self.assertIn("def create_user", content)
        self.assertIn("def get_user", content)
        self.assertIn("def delete_user", content)

    def test_apply_writes_test_file(self):
        tmp = Path("/tmp/_test_make_test")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        into = str(tmp / "user.py")
        test_into = str(tmp / "test_user.py")
        _fire(app, "make", ["user", "--cols", "name:str:pk",
                            "--into", into, "--test-into", test_into,
                            "--apply"])
        self.assertTrue(Path(test_into).exists())
        content = Path(test_into).read_text("utf-8")
        self.assertIn("class TestUser", content)
        self.assertIn("test_create_and_get", content)

    def test_unknown_lang_errors(self):
        tmp = Path("/tmp/_test_make_bad_lang")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        into = str(tmp / "user.rs")
        _fire(app, "make", ["user", "--cols", "name:str",
                            "--lang", "rust", "--into", into, "--apply"])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("ERROR", kinds)
        self.assertFalse(Path(into).exists())

    def test_unknown_ext_errors(self):
        tmp = Path("/tmp/_test_make_bad_ext")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        into = str(tmp / "user.rs")
        _fire(app, "make", ["user", "--cols", "name:str",
                            "--into", into, "--apply"])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("ERROR", kinds)
        self.assertFalse(Path(into).exists())

    def test_apply_marks_mood(self):
        tmp = Path("/tmp/_test_make_mood")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        into = str(tmp / "user.py")
        test_into = str(tmp / "test_user.py")
        _fire(app, "make", ["user", "--cols", "name:str:pk",
                            "--into", into, "--test-into", test_into,
                            "--apply"])
        self.assertIn("success", app.pet_store.moods)


class TestTestgen(unittest.TestCase):
    def test_no_args_shows_error(self):
        tmp = Path("/tmp/_test_testgen")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        _fire(app, "testgen", [])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("ERROR", kinds)

    def test_preview_for_file(self):
        tmp = Path("/tmp/_test_testgen_preview")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        _fire(app, "testgen", ["core.py"])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("TESTGEN", kinds)
        self.assertTrue(len(app.ui.code_shown) > 0)

    def test_all_symbols(self):
        tmp = Path("/tmp/_test_testgen_all")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        _fire(app, "testgen", ["all"])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("TESTGEN", kinds)

    def test_apply_writes(self):
        tmp = Path("/tmp/_test_testgen_apply")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        into = str(tmp / "test_core.py")
        _fire(app, "testgen", ["core.py", "--into", into, "--apply"])
        self.assertTrue(Path(into).exists())
        content = Path(into).read_text("utf-8")
        self.assertIn("unittest", content)

    def test_empty_index(self):
        tmp = Path("/tmp/_test_testgen_empty")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        app.brain.build.return_value = {"files": 0, "symbols": []}
        _fire(app, "testgen", ["core.py"])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("ERROR", kinds)

    def test_unknown_lang_errors(self):
        tmp = Path("/tmp/_test_testgen_bad_lang")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        _fire(app, "testgen", ["core.py", "--lang", "rust"])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("ERROR", kinds)


class TestRecipe(unittest.TestCase):
    def test_list_builtin(self):
        tmp = Path("/tmp/_test_recipe_list")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        _fire(app, "recipe", ["list"])
        self.assertTrue(len(app.ui.blocks) > 0, "expected blocks to be shown")

    def test_unknown_recipe(self):
        tmp = Path("/tmp/_test_recipe_unknown")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        _fire(app, "recipe", ["nonexistent"])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("ERROR", kinds)

    def test_dry_does_not_write(self):
        tmp = Path("/tmp/_test_recipe_dry")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        prev = os.getcwd()
        os.chdir(tmp)
        try:
            _fire(app, "recipe", ["scaffold", "widget", "name:str"])
        finally:
            os.chdir(prev)
        self.assertFalse(Path(str(tmp / "widget.py")).exists())

    def test_apply_writes(self):
        tmp = Path("/tmp/_test_recipe_apply")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        prev = os.getcwd()
        os.chdir(tmp)
        try:
            _fire(app, "recipe", ["scaffold", "widget", "name:str",
                                  "--apply"])
        finally:
            os.chdir(prev)
        self.assertTrue(Path(str(tmp / "widget.py")).exists())
        content = (tmp / "widget.py").read_text("utf-8")
        self.assertIn("class Widget:", content)

    def test_missing_args_error(self):
        tmp = Path("/tmp/_test_recipe_args")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        app.state.write_json("recipes.json", {"oops": "echo {0} {1} {2}"})
        _fire(app, "recipe", ["oops", "one"])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("ERROR", kinds)

    def test_braces_no_crash(self):
        tmp = Path("/tmp/_test_recipe_braces")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        app.state.write_json("recipes.json", {"bad": "echo {hello} {0 {"})
        _fire(app, "recipe", ["bad"])
        kinds = [k for k, _ in app.ui.shown]
        self.assertIn("ECHO", kinds)


class TestGenNewFile(unittest.TestCase):
    def test_into_new_file(self):
        tmp = Path("/tmp/_test_gen_newfile")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        app.brain.ensure.return_value = (
            {"files": 0, "symbols": []}, {},
        )
        into = str(tmp / "sub" / "newmod.py")
        _fire(app, "gen", ["function", "hello", "--into", into,
                           "--doc", "says hi", "--apply"])
        self.assertTrue(Path(into).exists())
        content = Path(into).read_text("utf-8")
        self.assertIn("def hello(", content)
        self.assertIn("says hi", content)


if __name__ == "__main__":
    unittest.main()
