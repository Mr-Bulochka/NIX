import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from nix import __version__
from nix.commands import COMMANDS, Command
from nix.daemon import (
    DaemonBackend,
    _handle_line,
    _parse_socket_arg,
    run_single,
)

ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestDaemonInProcess(unittest.TestCase):
    """In-process tests for the v1 JSON-Lines daemon protocol."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.root = Path(self._tmp.name)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _backend(self):
        return DaemonBackend()

    # ---- envelope basics ----------------------------------------------

    def test_blank_line_ok_no_events(self):
        result = run_single(self._backend(), "   \n")
        self.assertTrue(result["ok"])
        self.assertFalse(result["session_end"])
        self.assertEqual(result["events"], [])

    def test_ping_ok_no_events(self):
        for line in ("PING", "ping"):
            result = run_single(self._backend(), line)
            self.assertTrue(result["ok"])
            self.assertFalse(result["session_end"])
            self.assertEqual(result["events"], [])

    def test_serializable_envelope(self):
        result = run_single(self._backend(), "status")
        json.dumps(result)  # must not raise

    # ---- help ---------------------------------------------------------

    def test_help_lists_commands(self):
        result = run_single(self._backend(), "HELP")
        self.assertTrue(result["ok"])
        self.assertFalse(result["session_end"])
        names = [c["name"] for c in result["commands"]]
        for expected in ("defs", "git", "gen", "help", "status",
                         "clear", "quit", "settings"):
            self.assertIn(expected, names)

    def test_help_exact_shape(self):
        result = run_single(self._backend(), "help")
        commands = result["commands"]
        self.assertGreater(len(commands), 10)
        names = [c["name"] for c in commands]
        self.assertEqual(names, sorted(names))
        for entry in commands:
            self.assertEqual(set(entry.keys()),
                             {"name", "description", "usage"})

    def test_help_does_not_reset_events(self):
        b = self._backend()
        run_single(b, "defs")
        self.assertGreater(len(b.ui.events), 0)
        run_single(b, "PING")
        self.assertGreater(len(b.ui.events), 0)
        run_single(b, "HELP")
        self.assertGreater(len(b.ui.events), 0)

    def test_help_single_command(self):
        b = self._backend()
        result = run_single(b, "help status")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["events"]), 1)
        event = result["events"][0]
        self.assertEqual(event["op"], "block")
        self.assertEqual(event["title"], b.config.t("tbl.command"))
        status = COMMANDS["status"]
        self.assertEqual(event["rows"][0][0], status.usage)
        self.assertEqual(event["rows"][0][1], status.description)

    def test_help_unknown_command(self):
        b = self._backend()
        result = run_single(b, "help nosuchcmd")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["events"]), 1)
        event = result["events"][0]
        self.assertEqual(event["op"], "message")
        self.assertEqual(event["kind"], "ERROR")
        self.assertEqual(event["text"],
                         b.config.t("fb.unknown", name="nosuchcmd"))

    # ---- known commands -----------------------------------------------

    def test_status(self):
        b = self._backend()
        result = run_single(b, "status")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["events"]), 1)
        event = result["events"][0]
        self.assertEqual(event["op"], "status")
        for key in ("root", "mode", "attempts", "max_attempts", "files",
                    "dirs", "functions", "classes", "source_files",
                    "total_lines"):
            self.assertIn(key, event)

    def test_defs_empty_project(self):
        b = self._backend()
        result = run_single(b, "defs")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["events"]), 1)
        event = result["events"][0]
        self.assertEqual(event["op"], "message")
        self.assertEqual(event["kind"], "SYSTEM")
        self.assertEqual(event["text"], b.config.t("fb.no_symbols"))

    def test_defs_finds_symbols(self):
        (self.root / "app.py").write_text("def main():\n    pass\n",
                                          encoding="utf-8")
        b = self._backend()
        result = run_single(b, "defs")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["events"]), 1)
        event = result["events"][0]
        self.assertEqual(event["op"], "block")
        self.assertEqual(event["title"], b.config.t("tbl.symbols"))
        self.assertGreater(len(event["rows"]), 0)

    def test_settings_headless(self):
        b = self._backend()
        result = run_single(b, "settings")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["events"]), 1)
        event = result["events"][0]
        self.assertEqual(event["op"], "message")
        self.assertEqual(event["kind"], "SYSTEM")
        self.assertEqual(event["text"], b.config.t("fb.headless_no_settings"))

    def test_clear_resets_events(self):
        (self.root / "app.py").write_text("def main():\n    pass\n",
                                          encoding="utf-8")
        b = self._backend()
        run_single(b, "defs")
        self.assertGreater(len(b.ui.events), 0)
        result = run_single(b, "clear")
        self.assertTrue(result["ok"])
        self.assertFalse(result["session_end"])
        self.assertEqual(result["events"], [])

    def test_version_message(self):
        b = self._backend()
        result = run_single(b, "version")
        self.assertTrue(result["ok"])
        events = result["events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["op"], "message")
        self.assertEqual(events[0]["kind"], "SYSTEM")
        self.assertEqual(events[0]["text"],
                         b.config.t("fb.version", version=__version__))

    def test_pwd_message(self):
        b = self._backend()
        result = run_single(b, "pwd")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["text"], str(b.root))

    def test_echo_no_args(self):
        b = self._backend()
        result = run_single(b, "echo")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["kind"], "ERROR")
        self.assertEqual(result["events"][0]["text"],
                         b.config.t("fb.missing_arg"))

    def test_echo_utf8_round_trip(self):
        b = self._backend()
        result = run_single(b, "echo привет мир")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["kind"], "ECHO")
        self.assertEqual(result["events"][0]["text"], "привет мир")
        reloaded = json.loads(json.dumps(result, ensure_ascii=False))
        self.assertEqual(reloaded["events"][0]["text"], "привет мир")

    def test_quit_ends_session(self):
        b = self._backend()
        result = run_single(b, "quit")
        self.assertTrue(result["ok"])
        self.assertTrue(result["session_end"])

    def test_unknown_command_reports_error(self):
        b = self._backend()
        result = run_single(b, "no_such_command_xyz")
        self.assertFalse(result["ok"])
        self.assertFalse(result["session_end"])
        self.assertEqual(result["events"], [])
        self.assertEqual(result["error"],
                         "unknown command: no_such_command_xyz")

    # ---- failure path -------------------------------------------------

    def test_boom_failure_path(self):
        b = self._backend()

        def _raise(_backend, _args):
            raise RuntimeError("boom")

        COMMANDS["_boom"] = Command("_boom", "boom", "", _raise)
        self.addCleanup(COMMANDS.pop, "_boom", None)
        result = run_single(b, "_boom")
        self.assertFalse(result["ok"])
        self.assertFalse(result["session_end"])
        self.assertEqual(result["events"], [])
        self.assertEqual(result["error"], "_boom failed: boom")

        self.assertEqual(b.pet["xp"], 2)
        self.assertEqual(b.pet["level"], 1)
        self.assertEqual(b.pet["mood"], "thoughtful")
        self.assertEqual(b.pet["energy"], 97)
        self.assertEqual(b.pet["age"], 1)
        log = b.session_logger.read_last()
        self.assertTrue(any("_boom failed" in line for line in log))

    # ---- wire-level ---------------------------------------------------

    def test_handle_line_invalid_utf8(self):
        b = self._backend()
        result = _handle_line(b, b"\xff\xfe\x00")
        self.assertEqual(
            result,
            {"ok": False, "session_end": False, "events": [],
             "error": "invalid UTF-8"},
        )

    def test_parse_socket_arg(self):
        cases = [
            ("8080", ("127.0.0.1", 8080)),
            ("127.0.0.1:9000", ("127.0.0.1", 9000)),
            ("[::1]:9001", ("::1", 9001)),
            ("localhost:7000", ("localhost", 7000)),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(_parse_socket_arg(value), expected)
        with self.assertRaises(ValueError):
            _parse_socket_arg("8080x")


def _daemon_env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    return env


class TestDaemonSubprocess(unittest.TestCase):
    """End-to-end tests for the ``nix daemon`` CLI."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, *args, **kwargs):
        return subprocess.run(
            [sys.executable, "-m", "nix", "daemon", *args],
            cwd=self.cwd,
            env=_daemon_env(),
            **kwargs,
        )

    def test_once_status(self):
        cp = self._run("--once", "status", capture_output=True)
        self.assertEqual(cp.returncode, 0)
        payload = json.loads(cp.stdout.decode("utf-8"))
        self.assertTrue(payload["ok"])

    def test_once_unknown_command(self):
        cp = self._run("--once", "nosuchcmd", capture_output=True)
        self.assertEqual(cp.returncode, 1)
        payload = json.loads(cp.stdout.decode("utf-8"))
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "unknown command: nosuchcmd")

    def test_once_requires_single_argument(self):
        cp = self._run("--once", "status", "extra", capture_output=True)
        self.assertEqual(cp.returncode, 2)
        err = cp.stderr.decode("utf-8")
        self.assertIn("--once requires exactly one command argument", err)
        self.assertEqual(cp.stdout, b"")

    def test_once_socket_mutually_exclusive(self):
        port = _free_port()
        cp = self._run("--once", "status",
                       "--socket", f"127.0.0.1:{port}",
                       capture_output=True)
        self.assertEqual(cp.returncode, 2)
        self.assertIn("mutually exclusive",
                      cp.stderr.decode("utf-8"))

    def test_help_flag(self):
        cp = self._run("--help", capture_output=True)
        self.assertEqual(cp.returncode, 0)
        self.assertIn("nix daemon [--socket host:port]",
                      cp.stdout.decode("utf-8"))

    def test_unexpected_arguments(self):
        cp = self._run("bogus", capture_output=True)
        self.assertEqual(cp.returncode, 2)
        self.assertIn("unexpected arguments",
                      cp.stderr.decode("utf-8"))

    def test_stdin_json_lines(self):
        cp = self._run(input=b"settings\nquit\n", capture_output=True)
        self.assertEqual(cp.returncode, 0)
        lines = cp.stdout.decode("utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        first = json.loads(lines[0])
        self.assertTrue(first["ok"])
        self.assertFalse(first["session_end"])
        second = json.loads(lines[1])
        self.assertTrue(second["session_end"])

    def test_socket_sessions(self):
        port = _free_port()
        proc = subprocess.Popen(
            [sys.executable, "-m", "nix", "daemon",
             "--socket", f"127.0.0.1:{port}"],
            cwd=self.cwd,
            env=_daemon_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.time() + 15
            connected = False
            while time.time() < deadline:
                if proc.poll() is not None:
                    out, err = proc.communicate(timeout=5)
                    self.fail(
                        f"daemon exited early rc={proc.returncode} "
                        f"stdout={out!r} stderr={err!r}")
                try:
                    with socket.create_connection(
                            ("127.0.0.1", port), timeout=0.5):
                        connected = True
                    break
                except OSError:
                    time.sleep(0.1)
            self.assertTrue(connected, "daemon never started listening")

            with socket.create_connection(
                    ("127.0.0.1", port), timeout=5) as conn:
                stream = conn.makefile("rb")
                conn.sendall(b"PING\n")
                pong = json.loads(stream.readline())
                self.assertTrue(pong["ok"])
                self.assertEqual(pong["events"], [])
                conn.sendall(b"quit\n")
                bye = json.loads(stream.readline())
                self.assertTrue(bye["session_end"])

            with socket.create_connection(
                    ("127.0.0.1", port), timeout=5) as conn:
                stream = conn.makefile("rb")
                conn.sendall(b"HELP\n")
                help_payload = json.loads(stream.readline())
                self.assertTrue(help_payload["ok"])
                self.assertGreater(len(help_payload["commands"]), 0)
        finally:
            proc.terminate()
            try:
                proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    unittest.main()