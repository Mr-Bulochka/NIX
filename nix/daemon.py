from __future__ import annotations

import json
import re
import socket
import sys
from pathlib import Path

from .app import NixApp
from .commands import get_all_commands


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


def run_single(backend: DaemonBackend, line: str) -> dict:
    """Execute one command line, return a JSON-serializable envelope."""
    line = line.strip()
    if line.upper() == "PING":
        return {"ok": True, "session_end": False, "events": []}
    if line.upper() in ("QUIT", "EXIT"):
        return {"ok": True, "session_end": True, "events": []}
    if line.upper() == "HELP":
        commands = [
            {"name": c.name, "description": c.description, "usage": c.usage}
            for c in sorted(get_all_commands().values(),
                            key=lambda c: c.name)
        ]
        return {"ok": True, "session_end": False, "events": [],
                "commands": commands}
    backend.ui.events = []
    try:
        continue_session = backend.handle_command(line)
        return {"ok": True, "session_end": not continue_session,
                "events": backend.ui.events}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "session_end": False,
                "events": [{"op": "message", "kind": "ERROR",
                            "text": f"daemon error: {exc}"}]}


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


def run_stdin(backend: DaemonBackend) -> None:
    """Line-oriented protocol over stdin/stdout (JSON Lines)."""
    import io
    try:
        stream = io.TextIOWrapper(sys.stdout.buffer,
                                  encoding=sys.stdout.encoding or "utf-8",
                                  errors="replace")
    except (AttributeError, ValueError):
        stream = sys.stdout
    for raw in sys.stdin:
        stream.write(_encode(run_single(backend, raw)) + "\n")
        stream.flush()


def run_socket(backend: DaemonBackend, host: str, port: int) -> None:
    """TCP server: each connection is a request/response session."""
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
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        text = line.decode("utf-8", errors="replace")
                        result = run_single(backend, text)
                        conn.sendall((_encode(result) + "\n").encode("utf-8"))
                        if result["session_end"]:
                            return


def _parse_socket_arg(value: str) -> tuple[str, int]:
    if value.startswith("["):
        host, _, port = value[1:].partition("]:")
        return host, int(port)
    host, _, port = value.rpartition(":")
    if ":" in value and not host:
        host = "127.0.0.1"
    return (host or "127.0.0.1"), int(port)


def main(argv: list[str]) -> int:
    backend = DaemonBackend()
    once = None
    if "--once" in argv:
        idx = argv.index("--once")
        if idx + 1 < len(argv):
            once = argv[idx + 1]
    socket_arg = None
    if "--socket" in argv:
        idx = argv.index("--socket")
        if idx + 1 < len(argv):
            socket_arg = argv[idx + 1]
    if once is not None:
        sys.stdout.write(_encode(run_single(backend, once)) + "\n")
        return 0
    if socket_arg is not None:
        host, port = _parse_socket_arg(socket_arg)
        run_socket(backend, host, port)
        return 0
    run_stdin(backend)
    return 0