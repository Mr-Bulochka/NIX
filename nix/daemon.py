from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

from .app import NixApp, _tokenize_nix
from .commands import get_all_commands, get_command


class HeadlessUI:
    """Collects everything a command renders into an ordered event list.

    The daemon protocol delivers these events verbatim, so any IDE can
    re-render them: message, block, code, pet, status, scan, ...
    """

    def __init__(self) -> None:
        self.events: list[dict] = []

    def _emit(self, op: str, **data) -> None:
        self.events.append({"op": op, **data})

    # ---- event producers ----------------------------------------------

    def show_message(self, kind: str, text: str) -> None:
        self._emit("message", kind=kind, text=text)

    def show_error(self, text: str) -> None:
        self._emit("message", kind="ERROR", text=text)

    def show_block(self, title: str, rows) -> None:
        self._emit("block", title=title, rows=[
            list(row) if isinstance(row, (list, tuple)) else row
            for row in rows
        ])

    def show_code(self, title: str, lines) -> None:
        self._emit("code", title=title, lines=list(lines))

    def show_tree(self, title: str, lines) -> None:
        self._emit("tree", title=title, lines=list(lines))

    def show_scan(self, info) -> None:
        self._emit("scan", **info.__dict__)

    def show_pet(self, pet) -> None:
        self._emit("pet", pet=pet)

    def show_logs(self, path, lines) -> None:
        self._emit("logs", path=str(path), lines=list(lines))

    def show_history(self, entries) -> None:
        self._emit("history", entries=entries)

    def show_help(self, groups) -> None:
        self._emit("help", groups=groups)

    def show_status(self, **kw) -> None:
        self._emit("status", **kw)

    def _refresh_pet(self) -> None:
        pass

    def clear_log(self) -> None:
        self.events.clear()

    def show_settings(self, config) -> None:
        self.show_message("SYSTEM", config.t("fb.headless_no_settings"))


class DaemonBackend(NixApp):
    """Headless NIX: same commands, no TUI.  Pets get a default
    identity on first run so brain/pet features work everywhere."""

    def __init__(self, cwd: str | None = None) -> None:
        self.ui = HeadlessUI()
        super().__init__()
        if self.pet is None:
            self.pet = self.pet_store.create("NIX")


def _chunks(text: str) -> list[list[str]]:
    """Split a request line into command chunks (same as the TUI)."""
    chunks: list[list[str]] = []
    cur: list[str] = []
    for kind, value in _tokenize_nix(text):
        if kind == "arg":
            cur.append(value)
        elif cur:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def _dispatch(backend: DaemonBackend, args: list[str]) -> tuple[str | None, bool]:
    """Run one command chunk. Returns (error, continue_session).

    ``error`` is None on success and carries a human-readable reason
    otherwise; the envelope then answers ``ok: false`` without a fake
    success. The exception path mirrors the TUI (log, pet penalty, mood)
    but keeps the reason in the envelope instead of a UI ERROR event, so
    the events a command already emitted stay re-renderable.
    """
    if not args:
        return None, True
    name = args[0].lower()
    rest = args[1:]

    if name in ("quit", "exit"):
        backend.session_logger.write("SYSTEM", "session ended by user")
        backend.journal.write("SYSTEM", "session ended by user")
        return None, False

    cmd = get_command(name)
    if cmd is None:
        return f"unknown command: {name}", True

    try:
        result = cmd.handler(backend, rest)
    except Exception as exc:  # noqa: BLE001
        backend.session_logger.write("ERROR", f"/{name} failed: {exc}")
        backend.add_pet_xp(2, "failure", save=True)
        if backend.pet is not None:
            try:
                backend.pet = backend.pet_store.update_mood(
                    backend.pet, "failure"
                )
            except Exception:  # noqa: BLE001
                pass
        return f"{name} failed: {exc}", True

    if result.message:
        backend.ui.show_message("SYSTEM", result.message)
    return None, result.continue_session


def run_single(backend: DaemonBackend, line: str) -> dict:
    """Execute one request line, return a JSON-serializable envelope."""
    line = line.strip()
    if not line:
        return {"ok": True, "session_end": False, "events": []}
    if line.upper() == "PING":
        return {"ok": True, "session_end": False, "events": []}
    if line.upper() == "HELP":
        commands = [
            {"name": c.name, "description": c.description, "usage": c.usage}
            for c in sorted(get_all_commands().values(),
                            key=lambda c: c.name)
        ]
        return {"ok": True, "session_end": False, "events": [],
                "commands": commands}

    backend.ui.events = []
    chunks = _chunks(line)
    if not chunks:
        return {"ok": False, "session_end": False, "events": [],
                "error": "malformed command line"}

    error: str | None = None
    session_end = False
    for chunk in chunks:
        err, cont = _dispatch(backend, chunk)
        if err is not None and error is None:
            error = err
        if not cont:
            session_end = True
            break

    result: dict = {"ok": error is None, "session_end": session_end,
                    "events": backend.ui.events}
    if error is not None:
        result["error"] = error
    return result


def _jsonable(value):
    """Recursively turn Paths, enums and other non-JSON objects into
    strings so the protocol never crashes on a payload."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _encode(payload: dict) -> str:
    return json.dumps(_jsonable(payload), ensure_ascii=False)


def _handle_line(backend: DaemonBackend, raw: bytes) -> dict:
    """Decode one binary line strictly; a non-UTF-8 input is never
    answered with a fake success."""
    try:
        return run_single(backend, raw.decode("utf-8"))
    except UnicodeDecodeError:
        return {"ok": False, "session_end": False, "events": [],
                "error": "invalid UTF-8"}


def _stdout_stream():
    """A UTF-8 text stream for protocol output on any console.

    The daemon payloads may contain non-ASCII (e.g. a ``×`` in diff
    stats); wrapping the buffer prevents UnicodeEncodeError on cp1251
    consoles while keeping the reader decoding deterministic.
    """
    import io
    try:
        return io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                errors="replace")
    except (AttributeError, ValueError):
        return sys.stdout


def run_stdin(backend: DaemonBackend) -> None:
    """Line-oriented protocol over stdin/stdout (JSON Lines).

    A response with ``session_end: true`` ends the session.
    """
    stream = _stdout_stream()
    buffer = getattr(sys.stdin, "buffer", None)
    for raw in buffer if buffer is not None else sys.stdin:
        if buffer is not None:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                result = {"ok": False, "session_end": False, "events": [],
                          "error": "invalid UTF-8"}
            else:
                result = run_single(backend, text)
        else:
            result = run_single(backend, raw)
        stream.write(_encode(result) + "\n")
        stream.flush()
        if result["session_end"]:
            break


def run_socket(backend: DaemonBackend, host: str, port: int) -> None:
    """TCP server: each connection is a request/response session.

    ``session_end: true`` closes the connection but the server keeps
    accepting new ones.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(1)
        sys.stderr.write(f"NIX daemon listening on {host}:{port}\n")
        sys.stderr.flush()
        while True:
            conn, _addr = srv.accept()
            with conn:
                buf = b""
                ended = False
                while not ended:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        result = _handle_line(backend, line)
                        conn.sendall((_encode(result) + "\n").encode("utf-8"))
                        if result["session_end"]:
                            ended = True
                            break


def _parse_socket_arg(value: str) -> tuple[str, int]:
    if value.startswith("["):
        host, _, port = value[1:].partition("]:")
        return host, int(port)
    host, _, port = value.rpartition(":")
    if ":" in value and not host:
        host = "127.0.0.1"
    return (host or "127.0.0.1"), int(port)


def _print_usage(stream=sys.stdout) -> None:
    print("usage: nix daemon [--socket host:port] [--once 'command']",
          file=stream)


def _usage_error(message: str) -> int:
    print(f"nix daemon: {message}", file=sys.stderr)
    _print_usage(sys.stderr)
    return 2


def main(argv: list[str]) -> int:
    backend = DaemonBackend()

    if "--help" in argv or "-h" in argv:
        _print_usage()
        return 0

    has_once = "--once" in argv
    has_socket = "--socket" in argv
    if has_once and has_socket:
        return _usage_error("--once and --socket are mutually exclusive")

    if has_once:
        idx = argv.index("--once")
        rest = argv[idx + 1:]
        if len(rest) != 1:
            return _usage_error(
                "--once requires exactly one command argument")
        result = run_single(backend, rest[0])
        stream = _stdout_stream()
        stream.write(_encode(result) + "\n")
        stream.flush()
        return 0 if result["ok"] else 1

    if has_socket:
        idx = argv.index("--socket")
        rest = argv[idx + 1:]
        if len(rest) != 1:
            return _usage_error(
                "--socket requires exactly one host:port argument")
        try:
            host, port = _parse_socket_arg(rest[0])
        except ValueError as exc:
            return _usage_error(f"invalid socket address: {exc}")
        run_socket(backend, host, port)
        return 0

    if argv:
        return _usage_error("unexpected arguments")

    run_stdin(backend)
    return 0