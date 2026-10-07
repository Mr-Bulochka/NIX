import sys
from .app import NixApp
from . import __version__


def main() -> None:
    if "--version" in sys.argv or "-V" in sys.argv:
        print(f"NIX {__version__}")
        sys.exit(0)
    if "--help" in sys.argv or "-h" in sys.argv:
        print("NIX - local terminal agent")
        print("usage: nix [--version|--help]")
        print("       nix daemon [--socket host:port] [--once 'command']")
        sys.exit(0)
    # Only the leading `daemon` token is the subcommand. Filtering every
    # occurrence used to eat a legitimate argument, so `nix daemon --once
    # daemon` lost its command value entirely.
    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        from .daemon import main as daemon_main
        sys.exit(daemon_main(sys.argv[2:]))
    try:
        app = NixApp()
        app.run()
    except KeyboardInterrupt:
        print()
        sys.exit(0)
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        sys.exit(1)
