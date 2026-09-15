import sys
from .app import NixApp
from . import __version__


def main() -> None:
    if "--version" in sys.argv or "-V" in sys.argv:
        print(f"NIX {__version__}")
        sys.exit(0)
    if "--help" in sys.argv or "-h" in sys.argv:
        print("NIX - local terminal agent")
        print(f"usage: nix [--version|--help]")
        sys.exit(0)
    try:
        app = NixApp()
        app.run()
    except KeyboardInterrupt:
        print()
        sys.exit(0)
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        sys.exit(1)
