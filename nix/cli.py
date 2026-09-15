import sys
from .app import NixApp


def main() -> None:
    try:
        app = NixApp()
        app.run()
    except KeyboardInterrupt:
        print()
        sys.exit(0)
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        sys.exit(1)
