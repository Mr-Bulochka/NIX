import json
import os
import tempfile
import unittest
from pathlib import Path

from nix.daemon import DaemonBackend, run_single


class TestDaemon(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.root = Path(self._tmp.name)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _backend(self):
        _b = DaemonBackend()
        _b.pet_store.create("Dummy")
        return _b

    def test_ping(self):
        result = run_single(self._backend(), "PING")
        self.assertTrue(result["ok"])
        self.assertFalse(result["session_end"])

    def test_quit_ends_session(self):
        result = run_single(self._backend(), "quit")
        self.assertTrue(result["session_end"])

    def test_help_lists_commands(self):
        result = run_single(self._backend(), "HELP")
        self.assertTrue(result["ok"])
        names = [c["name"] for c in result.get("commands", [])]
        self.assertIn("defs", names)
        self.assertIn("git", names)
        self.assertIn("gen", names)

    def test_command_produces_events(self):
        (self.root / "app.py").write_text("def main():\n    pass\n",
                                          encoding="utf-8")
        result = run_single(self._backend(), "defs")
        self.assertTrue(result["ok"])
        ops = [e["op"] for e in result["events"]]
        self.assertIn("block", ops)
        self.assertTrue(any(e["op"] == "block" and e["title"] == "Symbols"
                            for e in result["events"]))

    def test_serializable_envelope(self):
        result = run_single(self._backend(), "status")
        json.dumps(result)  # must not raise

    def test_bad_command_not_crash(self):
        result = run_single(self._backend(), "no_such_command_xyz")
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()