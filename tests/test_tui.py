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
                await pilot.press("escape")
                await pilot.pause()
                await pilot.click("#btn-status")
                await pilot.pause()
                await pilot.press("escape")
                await pilot.pause()
                from textual.widgets import Input
                cmd = pilot.app.query_one("#cmd", Input)
                cmd.focus()
                cmd.value = "attempts +5"
                await pilot.press("enter")
                await pilot.pause()
                assert self.app.config.attempts == 5
                assert cmd.value == ""
                assert cmd.has_focus
                await pilot.click("#btn-quit")
                await pilot.pause()
        self._run(scenario())

    def test_command_without_slash_and_focus_stays(self):
        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                from textual.widgets import Input
                cmd = pilot.app.query_one("#cmd", Input)
                cmd.value = "pet"
                await pilot.press("enter")
                await pilot.pause()
                assert cmd.value == ""
                assert cmd.has_focus
        self._run(scenario())

    def test_first_launch_does_not_leak_name_into_cmd(self):
        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            calls = []
            orig = self.app.handle_command

            def spy(raw):
                calls.append(raw)
                return orig(raw)

            self.app.handle_command = spy
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause(0.5)
                assert self.app.pet is not None
                assert calls == []
        self._run(scenario())

    def test_settings_close_button_works(self):
        from textual.widgets import Input
        from nix.ui import SettingsModal

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 60)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                self.app.handle_command("settings")
                await pilot.pause(0.5)
                assert isinstance(pilot.app.screen, SettingsModal)
                await pilot.click("#set-close")
                await pilot.pause(0.5)
                assert not isinstance(pilot.app.screen, SettingsModal)
                cmd = pilot.app.query_one("#cmd", Input)
                assert cmd.has_focus
        self._run(scenario())

    def test_settings_pill_button_and_skin(self):
        from textual.widgets import Button, Input
        from nix.avatar import VARIANT_KINDS
        from nix.ui import SettingsModal

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 60)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                self.app.handle_command("settings")
                await pilot.pause(0.5)
                assert self.app.pet["skin"] is None
                await pilot.click("#set-pill")
                await pilot.pause(0.5)
                assert self.app.pet["skin"] in VARIANT_KINDS
                assert self.app.pet["last_pill_at"] is not None
                assert self.app.pet["body_pattern"] == "seed"
                pill = pilot.app.screen.query_one("#set-pill", Button)
                assert pill.disabled  # cooldown active
                await pilot.click("#set-close")
                await pilot.pause(0.3)
        self._run(scenario())

    def test_settings_no_autosave_until_apply(self):
        from nix.ui import SettingsModal

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            saved = []
            orig = self.app.config_store.save

            def spy(cfg):
                saved.append(cfg)
                return orig(cfg)

            self.app.config_store.save = spy
            async with ui.run_test(size=(160, 60)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                saved.clear()  # ignore the pet-creation save
                self.app.handle_command("settings")
                await pilot.pause(0.5)
                assert isinstance(pilot.app.screen, SettingsModal)
                assert saved == []  # nothing saved on open
                mode = pilot.app.screen.query_one("#set-mode")
                mode.value = "safe"
                await pilot.pause(0.3)
                assert saved == []  # still nothing while editing
                assert self.app.config.mode != "safe"
                await pilot.click("#set-apply")
                await pilot.pause(0.5)
                assert len(saved) == 1  # exactly one save on apply
                assert self.app.config.mode == "safe"
                assert not isinstance(pilot.app.screen, SettingsModal)
        self._run(scenario())

    def test_settings_close_without_apply_discards(self):
        from nix.ui import SettingsModal

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            saved = []
            orig = self.app.config_store.save

            def spy(cfg):
                saved.append(cfg)
                return orig(cfg)

            self.app.config_store.save = spy
            async with ui.run_test(size=(160, 60)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                saved.clear()
                self.app.handle_command("settings")
                await pilot.pause(0.5)
                mode = pilot.app.screen.query_one("#set-mode")
                mode.value = "git"
                await pilot.pause(0.3)
                await pilot.click("#set-close")
                await pilot.pause(0.5)
                assert saved == []
                assert self.app.config.mode != "git"
        self._run(scenario())


if __name__ == "__main__":
    unittest.main()