import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from nix.app import NixApp
from nix.ui import NixUI


class TestTUI(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.root = Path(self._tmp.name)
        self.app = NixApp()

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _run(self, coro):
        return asyncio.run(coro)

    def test_first_launch_creates_pet(self):
        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                name_input = pilot.app.screen.query_one("Input")
                name_input.value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                assert self.app.pet is not None
                assert self.app.pet["name"] == "Tester"
        self._run(scenario())

    def test_first_launch_language_ru(self):
        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                from textual.widgets import Select
                select = pilot.app.screen.query_one(Select)
                select.value = "ru"
                await pilot.pause()
                name_input = pilot.app.screen.query_one("Input")
                name_input.value = "Тест"
                await pilot.press("enter")
                await pilot.pause()
                assert self.app.pet is not None
                assert self.app.pet["name"] == "Тест"
                assert self.app.config.language == "ru"
        self._run(scenario())

    def test_buttons_and_commands(self):
        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                await pilot.click("#btn-scan")
                await pilot.pause()
                await pilot.click("#btn-status")
                await pilot.pause()
                from textual.widgets import Input
                cmd = pilot.app.query_one("#cmd", Input)
                cmd.focus()
                cmd.value = "/attempts +5"
                await pilot.press("enter")
                await pilot.pause()
                assert self.app.config.attempts == 5
                await pilot.click("#btn-quit")
                await pilot.pause()
        self._run(scenario())


if __name__ == "__main__":
    unittest.main()