"""Tests for body inference (gen --body auto) and its wiring."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from nix.commands import get_command
from nix.body import infer_body


class TestInferBody(unittest.TestCase):
    def test_init_assigns_params(self):
        body = infer_body("__init__", "name: str, age: int = 0", "")
        self.assertIn("self.name = name", body)
        self.assertIn("self.age = age", body)

    def test_init_indents_inner_lines(self):
        body = infer_body("__init__", "name, age, email", "")
        expected = "self.name = name\n    self.age = age\n    self.email = email"
        self.assertEqual(body, expected)

    def test_init_skips_self_and_kwargs(self):
        body = infer_body("__init__", "self, name, **kwargs", "")
        self.assertEqual(body, "self.name = name")
        body2 = infer_body("__init__", "self, *args", "")
        self.assertEqual(body2, "pass")

    def test_init_no_params(self):
        self.assertEqual(infer_body("__init__", ""), "pass")

    def test_getter(self):
        self.assertEqual(infer_body("get_name", ""), "return self._name")

    def test_getter_bare_prefix(self):
        self.assertEqual(infer_body("get_", ""), "pass")

    def test_setter_with_field_param(self):
        self.assertEqual(infer_body("set_age", "age: int"), "self._age = age")

    def test_setter_uses_first_param(self):
        self.assertEqual(infer_body("set_name", "value: str"), "self._name = value")

    def test_setter_matches_field_when_no_params(self):
        self.assertEqual(infer_body("set_active", ""), "self._active = active")

    def test_unknown_name_falls_back_pass(self):
        self.assertEqual(infer_body("compute_total", "x, y"), "pass")

    def test_return_annotation_is_ignored(self):
        self.assertEqual(infer_body("get_name", "", "-> str"),
                         "return self._name")


class _UI:
    def __init__(self):
        self.shown = []
        self.code_shown = []

    def show_message(self, kind, msg):
        self.shown.append((kind, msg))

    def show_code(self, title, lines):
        self.code_shown.append((title, lines))


class _Journal:
    def __init__(self):
        self.entries = []

    def write(self, kind, msg):
        self.entries.append((kind, msg))


class _State:
    def __init__(self, tmp):
        self.nix = tmp / ".nix"


class _Rec:
    def __init__(self, tmp):
        self.ui = _UI()
        self.journal = _Journal()
        self.state = _State(tmp)
        self.config = MagicMock()
        self.config.lang = "en"
        self.root = tmp
        self.brain = MagicMock()
        self.brain.ensure.return_value = (
            {"files": 1, "symbols": []},
            {"naming_top": "snake", "functions": 0,
             "function_doc_ratio": 0.0, "exception_var": "e"},
        )

    def t(self, key, **kw):
        from nix.i18n import t
        return t(self.config.lang, key, **kw)


def _fire(app, name, args):
    return get_command(name).handler(app, args)


class TestGenBodyAuto(unittest.TestCase):
    def test_preview_uses_auto_body_getter(self):
        tmp = Path("/tmp/_test_body_getter")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        _fire(app, "gen", ["function", "get_name", "--body", "auto"])
        self.assertTrue(len(app.ui.code_shown) > 0)
        shown = "\n".join(app.ui.code_shown[0][1])
        self.assertIn("return self._name", shown)

    def test_preview_uses_auto_body_constructor(self):
        tmp = Path("/tmp/_test_body_init")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        _fire(app, "gen",
              ["function", "__init__", "--params", "self, name, age: int",
               "--body", "auto"])
        self.assertTrue(len(app.ui.code_shown) > 0)
        shown = "\n".join(app.ui.code_shown[0][1])
        self.assertIn("self.name = name", shown)
        self.assertIn("self.age = age", shown)

    def test_default_body_still_pass(self):
        tmp = Path("/tmp/_test_body_default")
        tmp.mkdir(parents=True, exist_ok=True)
        app = _Rec(tmp)
        _fire(app, "gen", ["function", "anything", "--params", "x"])
        shown = "\n".join(app.ui.code_shown[0][1])
        self.assertIn("pass", shown)


if __name__ == "__main__":
    unittest.main()