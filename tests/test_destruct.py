import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nix.app import NixApp
from nix.destruct import _collect_candidates, _mutate, plan_mutations, run_destruct
from nix.runner import TestRun


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
        self.records = []

    def show_message(self, kind, text):
        self.records.append((kind, text))


class _FakeRunner:
    def __init__(self, results=None):
        self.stock = list(results or [])
        self.calls = 0

    def __call__(self, root, timeout=None):
        self.calls += 1
        if self.stock:
            return self.stock.pop(0)
        return TestRun()


class TestMutate(unittest.TestCase):
    def test_eq_becomes_ne(self):
        self.assertEqual(_mutate("x == y\n"), ("x != y\n", "==->!="))

    def test_ne_becomes_eq(self):
        self.assertEqual(_mutate("x != y\n"), ("x == y\n", "!=-=>=="))

    def test_true_becomes_false(self):
        self.assertEqual(_mutate("flag = True\n"), ("flag = False\n", "True->False"))

    def test_false_becomes_true(self):
        self.assertEqual(_mutate("flag = False\n"), ("flag = True\n", "False->True"))

    def test_def_renamed(self):
        self.assertEqual(_mutate("def foo():\n"), ("def _m():\n", "def->_m"))

    def test_class_renamed(self):
        self.assertEqual(_mutate("class Foo:\n"), ("class _m:\n", "class->_m"))

    def test_import_untouched(self):
        self.assertIsNone(_mutate("import os\n"))


class TestCollectCandidates(unittest.TestCase):
    def test_collect_skips_tests_and_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rels = [
                "tests/test_example.py",
                "test_top.py",
                "foo_test.py",
                "__pycache__/cached.py",
                ".nix/state/note.json",
                "app.py",
                "src/mod.py",
            ]
            for rel in rels:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x = 1\n", encoding="utf-8")
            found = [str(p.relative_to(root)).replace("\\", "/")
                     for p in _collect_candidates(root)]
            self.assertEqual(found, ["app.py", "src/mod.py"])


class TestPlan(unittest.TestCase):
    def test_plan_finds_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "calc.py").write_text(
                "def add(a, b):\n    return a == b\n", encoding="utf-8")
            plan = plan_mutations(root)
            self.assertEqual(len(plan), 1)
            item = plan[0]
            self.assertEqual(item["rel"], "calc.py")
            self.assertEqual(item["operator"], "==->!=")
            self.assertIn("a != b", item["modified"])
            self.assertEqual(sorted(item.keys()),
                             ["modified", "operator", "original", "path", "rel"])

    def test_max_mutations_limits_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x == 1\n", encoding="utf-8")
            (root / "b.py").write_text("x == 2\n", encoding="utf-8")
            plan = plan_mutations(root, max_mutations=1)
            self.assertEqual(len(plan), 1)
            self.assertEqual(plan[0]["rel"], "a.py")


class DestructTests(unittest.TestCase):
    def _make_app(self, files=None, with_pet=True):
        tmp = tempfile.TemporaryDirectory()
        old = os.getcwd()
        os.chdir(tmp.name)
        root = Path(tmp.name)
        for rel, content in (files or {}).items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        app = NixApp()
        app.ui = _RecordingUI()
        if with_pet:
            app.pet = app.pet_store.create("Tester")
        self.addCleanup(tmp.cleanup)
        self.addCleanup(lambda: os.chdir(old))
        return app

    def test_killed_restores_original(self):
        app = self._make_app(
            {"calc.py": "def add(a, b):\n    return a == b\n"})
        app.config.checkpoint_on_mutate = False
        fake = _FakeRunner([TestRun(returncode=0, ran_tests=1, passed=1),
                            TestRun(returncode=1, ran_tests=1, failed=1)])
        with mock.patch("nix.destruct.run_tests", fake):
            report = run_destruct(app, timeout=5)
        self.assertEqual(fake.calls, 2)
        self.assertEqual(app.pet["xp"], 45)
        self.assertFalse(report.kept)
        self.assertTrue(report.restored)
        self.assertEqual(len(report.items), 1)
        self.assertIn("restored", report.items[0])
        self.assertIn("destruct-", report.checkpoint)
        text = (app.root / "calc.py").read_text(encoding="utf-8")
        self.assertEqual(text, "def add(a, b):\n    return a == b\n")
        self.assertEqual(app.mutations.count, 1)

    def test_survived_keep_true(self):
        app = self._make_app(
            {"calc.py": "def add(a, b):\n    return a == b\n"})
        app.config.checkpoint_on_mutate = False
        fake = _FakeRunner([TestRun(returncode=0, ran_tests=1, passed=1),
                            TestRun(returncode=0, ran_tests=1, passed=1)])
        with mock.patch("nix.destruct.run_tests", fake):
            report = run_destruct(app, timeout=5, keep=True)
        self.assertEqual(fake.calls, 2)
        self.assertEqual(app.pet["xp"], 45)
        self.assertTrue(report.kept)
        self.assertFalse(report.restored)
        self.assertEqual(report.items, [])
        text = (app.root / "calc.py").read_text(encoding="utf-8")
        self.assertIn("a != b", text)

    def test_survived_restores(self):
        app = self._make_app(
            {"calc.py": "def add(a, b):\n    return a == b\n"})
        app.config.checkpoint_on_mutate = False
        fake = _FakeRunner([TestRun(returncode=0, ran_tests=1, passed=1),
                            TestRun(returncode=0, ran_tests=1, passed=1)])
        with mock.patch("nix.destruct.run_tests", fake):
            report = run_destruct(app, timeout=5)
        self.assertEqual(fake.calls, 2)
        self.assertEqual(app.pet["xp"], 45)
        self.assertFalse(report.kept)
        self.assertTrue(report.restored)
        self.assertEqual(len(report.items), 1)
        self.assertIn("restored", report.items[0])
        text = (app.root / "calc.py").read_text(encoding="utf-8")
        self.assertEqual(text, "def add(a, b):\n    return a == b\n")

    def test_blocked_by_protected_path(self):
        app = self._make_app(
            {"calc.py": "def add(a, b):\n    return a == b\n"})
        app.config.checkpoint_on_mutate = False
        app.config.protected_paths = ["calc.py"]
        fake = _FakeRunner([TestRun(returncode=0, ran_tests=1, passed=1)])
        with mock.patch("nix.destruct.run_tests", fake):
            report = run_destruct(app, timeout=5)
        self.assertEqual(fake.calls, 1)
        self.assertEqual(app.pet["xp"], 30)
        self.assertEqual(len(report.candidates), 1)
        item = report.candidates[0]
        self.assertEqual(item["status"], "blocked")
        self.assertIn("blocked by world law", item["detail"])
        self.assertIn("protected_paths", item["detail"])
        self.assertNotIn("result", item)
        self.assertNotIn("backup", item)
        self.assertEqual(app.mutations.count, 0)
        text = (app.root / "calc.py").read_text(encoding="utf-8")
        self.assertEqual(text, "def add(a, b):\n    return a == b\n")

    def test_baseline_failure_aborts(self):
        app = self._make_app(
            {"calc.py": "def add(a, b):\n    return a == b\n"})
        app.config.checkpoint_on_mutate = False
        fake = _FakeRunner([])
        with mock.patch("nix.destruct.run_tests", fake):
            report = run_destruct(app, timeout=5)
        self.assertEqual(fake.calls, 1)
        self.assertEqual(report.checkpoint, "")
        self.assertEqual(report.items, [])
        self.assertEqual(app.pet["xp"], 0)

    def test_empty_plan(self):
        app = self._make_app({"readme.txt": "hello\n"})
        app.config.checkpoint_on_mutate = False
        fake = _FakeRunner([])
        with mock.patch("nix.destruct.run_tests", fake):
            report = run_destruct(app, timeout=5)
        self.assertEqual(fake.calls, 0)
        self.assertIsNone(report.baseline)
        self.assertEqual(report.candidates, [])
        self.assertEqual(app.pet["xp"], 0)


if __name__ == "__main__":
    unittest.main()