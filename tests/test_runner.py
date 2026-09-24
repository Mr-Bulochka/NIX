import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nix.app import NixApp
from nix.checkpoints import KIND_PERM, KIND_TEMP
from nix.runner import DEFAULT_TIMEOUT, TestRun, run_tests


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


class TestRunner(unittest.TestCase):
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

    def _cp_dir(self, app, kind):
        return app.state.nix / "checkpoints" / kind

    def _run_mocked(self, use_pytest, tests_dir=False,
                    stdout="1 passed in 0.01s\n", stderr="",
                    returncode=0):
        captured = {}
        cp = subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr)

        def fake_run(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            captured["cwd"] = kwargs.get("cwd")
            captured["capture_output"] = kwargs.get("capture_output")
            captured["text"] = kwargs.get("text")
            captured["timeout"] = kwargs.get("timeout")
            return cp

        with mock.patch("nix.runner.has_pytest",
                        return_value=use_pytest):
            with mock.patch("nix.runner.subprocess.run",
                            side_effect=fake_run):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    if tests_dir:
                        (root / "tests").mkdir()
                    result = run_tests(root)
        return captured, result, root

    def test_bare_run_is_killed(self):
        run = TestRun()
        self.assertFalse(run.ok)
        self.assertTrue(run.killed)
        self.assertIsNone(run.returncode)

    def test_prefers_pytest_command(self):
        captured, result, root = self._run_mocked(use_pytest=True)
        self.assertEqual(
            captured["cmd"],
            [sys.executable, "-m", "pytest", "-q", "--tb=no"])
        self.assertEqual(captured["cwd"], str(root))
        self.assertTrue(captured["capture_output"])
        self.assertTrue(captured["text"])
        self.assertEqual(captured["timeout"], DEFAULT_TIMEOUT)
        self.assertTrue(result.ok)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.passed, 1)

    def test_pytest_command_ignores_tests_dir(self):
        captured, result, root = self._run_mocked(
            use_pytest=True, tests_dir=True)
        self.assertEqual(
            captured["cmd"],
            [sys.executable, "-m", "pytest", "-q", "--tb=no"])
        self.assertNotIn("-s", captured["cmd"])
        self.assertTrue(result.ok)

    def test_falls_back_to_unittest_without_tests_dir(self):
        captured, result, root = self._run_mocked(use_pytest=False)
        self.assertEqual(
            captured["cmd"],
            [sys.executable, "-m", "unittest", "discover"])
        self.assertNotIn("-s", captured["cmd"])
        self.assertTrue(result.ok)

    def test_unittest_scopes_to_tests_dir(self):
        captured, result, root = self._run_mocked(
            use_pytest=False, tests_dir=True)
        self.assertEqual(
            captured["cmd"],
            [sys.executable, "-m", "unittest", "discover",
             "-s", "tests"])
        self.assertTrue(result.ok)

    def test_parses_pass_and_skip_counts(self):
        captured, result, root = self._run_mocked(
            use_pytest=True, stdout="5 passed, 1 skipped in 0.10s\n")
        self.assertEqual(result.passed, 5)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.ran_tests, 6)
        self.assertTrue(result.ok)
        self.assertFalse(result.killed)

    def test_marks_suite_killed_on_failure(self):
        captured, result, root = self._run_mocked(
            use_pytest=True, stdout="3 passed, 2 failed in 0.20s\n",
            returncode=1)
        self.assertEqual(result.passed, 3)
        self.assertEqual(result.failed, 2)
        self.assertEqual(result.ran_tests, 5)
        self.assertFalse(result.ok)
        self.assertTrue(result.killed)

    def test_marks_suite_killed_on_error(self):
        captured, result, root = self._run_mocked(
            use_pytest=True, stdout="1 error in 0.05s\n",
            returncode=1)
        self.assertEqual(result.errors, 1)
        self.assertEqual(result.ran_tests, 1)
        self.assertFalse(result.ok)
        self.assertTrue(result.killed)

    def test_nonzero_exit_kills_successful_counts(self):
        captured, result, root = self._run_mocked(
            use_pytest=True, stdout="2 passed in 0.01s\n",
            returncode=1)
        self.assertEqual(result.passed, 2)
        self.assertEqual(result.ran_tests, 2)
        self.assertFalse(result.ok)
        self.assertTrue(result.killed)

    def test_counts_tests_from_unittest_summary(self):
        captured, result, root = self._run_mocked(
            use_pytest=False,
            stdout="Ran 1 test in 0.001s\n\nOK\n")
        self.assertEqual(result.ran_tests, 1)
        self.assertEqual(result.passed, 1)
        self.assertTrue(result.ok)

    def test_parses_unittest_failure_summary(self):
        captured, result, root = self._run_mocked(
            use_pytest=False,
            stdout="Ran 3 tests in 0.01s\n\n"
                   "FAILED (failures=1, errors=1)\n",
            returncode=1)
        self.assertEqual(result.ran_tests, 3)
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.errors, 1)
        self.assertEqual(result.passed, 1)
        self.assertFalse(result.ok)

    def test_tail_keeps_last_nonempty_lines(self):
        captured, result, root = self._run_mocked(
            use_pytest=True, stdout="\n\n3 passed in 0.1s\n")
        self.assertEqual(result.tail, ["3 passed in 0.1s"])
        self.assertTrue(result.ok)

    def test_pytest_exit_code_five_means_no_tests(self):
        captured, result, root = self._run_mocked(
            use_pytest=True, stdout="no tests ran in 0.01s\n",
            returncode=5)
        self.assertTrue(result.no_tests)
        self.assertEqual(result.ran_tests, 0)
        self.assertFalse(result.ok)
        self.assertTrue(result.killed)

    def test_clean_empty_run_means_no_tests(self):
        captured, result, root = self._run_mocked(
            use_pytest=True, stdout="", returncode=0)
        self.assertTrue(result.no_tests)
        self.assertFalse(result.ok)

    def test_uncollected_nonzero_exit_counts_error(self):
        captured, result, root = self._run_mocked(
            use_pytest=True, stdout="", returncode=2)
        self.assertFalse(result.no_tests)
        self.assertEqual(result.errors, 1)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(result.ok)

    def test_timeout_parses_partial_output(self):
        exc = subprocess.TimeoutExpired(
            cmd=[], timeout=1, output=b"", stderr=b"1 passed\n")
        with mock.patch("nix.runner.subprocess.run", side_effect=exc):
            result = run_tests(Path("."))
        self.assertTrue(result.timed_out)
        self.assertEqual(result.passed, 1)
        self.assertEqual(result.ran_tests, 1)
        self.assertEqual(result.tail, ["1 passed"])
        self.assertFalse(result.ok)
        self.assertTrue(result.killed)
        self.assertIsNone(result.returncode)

    def test_oserror_returns_minus_one(self):
        with mock.patch("nix.runner.subprocess.run",
                        side_effect=OSError("boom")):
            result = run_tests(Path("."))
        self.assertEqual(result.returncode, -1)
        self.assertEqual(result.errors, 1)
        self.assertEqual(result.tail, ["boom"])
        self.assertFalse(result.ok)
        self.assertTrue(result.killed)

    def test_real_pytest_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "tests" / "test_ok.py").write_text(
                "def test_true():\n    assert True\n",
                encoding="utf-8")
            result = run_tests(root)
        self.assertTrue(result.ok)
        self.assertFalse(result.killed)
        self.assertEqual(result.returncode, 0)
        self.assertGreaterEqual(result.ran_tests, 1)
        self.assertGreaterEqual(result.passed, 1)

    def test_real_unittest_fallback_run(self):
        with mock.patch("nix.runner.has_pytest", return_value=False):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "tests").mkdir()
                (root / "tests" / "test_ok.py").write_text(
                    "import unittest\n"
                    "\n"
                    "class Ok(unittest.TestCase):\n"
                    "    def test_true(self):\n"
                    "        self.assertTrue(True)\n",
                    encoding="utf-8")
                result = run_tests(root)
        self.assertTrue(result.ok)
        self.assertEqual(result.returncode, 0)
        self.assertGreaterEqual(result.ran_tests, 1)