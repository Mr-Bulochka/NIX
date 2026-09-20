"""Regenerate the README screenshots (SVG, rendered by GitHub).

Usage:
    python scripts/make_screenshots.py

Writes SVG files into docs/screenshots/.  Each screenshot is a real,
headless render of the NixUI terminal app driven through Textual's test
pilot, so the images always reflect the current UI.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from nix.app import NixApp
from nix.ui import NixUI

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"

SAMPLE_FILES = {
    "README.md": "# demo\n\nA sample project used to generate NIX screenshots.\n",
    "src/__init__.py": "",
    "src/app.py": (
        "def main() -> int:\n"
        "    print('hello')\n"
        "    return 0\n"
        "\n"
        "\n"
        "class Server:\n"
        "    def __init__(self, host: str) -> None:\n"
        "        self.host = host\n"
        "\n"
        "    def start(self) -> None:\n"
        "        pass\n"
    ),
    "src/utils.py": (
        "def parse(query: str) -> dict:\n"
        "    return {}\n"
    ),
    "tests/test_app.py": (
        "import unittest\n"
        "\n"
        "\n"
        "class TestApp(unittest.TestCase):\n"
        "    def test_main(self) -> None:\n"
        "        self.assertEqual(1, 1)\n"
    ),
    "ui/app.js": (
        "export function boot() {\n"
        "  console.log('ok');\n"
        "}\n"
    ),
}


def write_sample_project(root: Path) -> None:
    for rel, content in SAMPLE_FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def create_app(root: Path) -> NixApp:
    cwd = os.getcwd()
    os.chdir(root)
    try:
        app = NixApp()
    finally:
        os.chdir(cwd)
    return app


async def snapshot(ui: NixUI, name: str) -> None:
    await asyncio.sleep(0.4)
    ui.save_screenshot(str(OUT / name))
    print(f"wrote docs/screenshots/{name}")


async def generate() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_sample_project(root)
        app = create_app(root)

        app.pet_store.create("Pixel")
        app.pet = app.pet_store.load()
        app.pet["mood"] = "focused"
        app.pet["energy"] = 84
        app.pet["age"] = 12
        app.pet["body_pattern"] = "bloom"
        app.pet_store.save(app.pet)
        app.config.tamagotchi_enabled = True

        ui = NixUI(app)
        app.ui = ui
        async with ui.run_test(size=(116, 38)) as pilot:
            await pilot.pause()
            await pilot.pause(0.5)

            await snapshot(ui, "main.svg")

            app.handle_command("scan")
            await snapshot(ui, "scan.svg")

            app.handle_command("status")
            await snapshot(ui, "status.svg")

            app.handle_command("help")
            await snapshot(ui, "help.svg")

            app.handle_command("pet")
            await snapshot(ui, "pet.svg")


if __name__ == "__main__":
    try:
        asyncio.run(generate())
    except KeyboardInterrupt:
        raise SystemExit(1)