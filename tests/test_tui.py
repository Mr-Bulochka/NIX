import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from nix.app import NixApp
from nix.ui import NixUI
import nix.ui


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

    def test_settings_pill_triggers_celebration(self):
        from textual.widgets import Button
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
                pill = pilot.app.screen.query_one("#set-pill", Button)
                assert not pill.disabled
                before = str(pill.label)
                await pilot.click("#set-pill")
                await pilot.pause(0.1)
                assert self.app.ui._celebrating
                assert str(pill.label) != before
        self._run(scenario())

    def test_clip_length_and_whitespace(self):
        from nix.ui import _clip

        assert _clip("hi") == "hi"
        assert _clip("  a   b  ") == "a b"
        assert _clip("x" * 400) == "x" * 400
        assert _clip("y" * 401) == "y" * 399 + "\u2026"
        assert _clip("z" * 398 + "  w") == "z" * 398 + " w"

    def test_settings_escape_keyboard_closes(self):
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
                mode = pilot.app.screen.query_one("#set-mode")
                mode.value = "git"
                await pilot.pause(0.3)
                await pilot.press("escape")
                await pilot.pause(0.5)
                assert not isinstance(pilot.app.screen, SettingsModal)
                assert self.app.config.mode != "git"
        self._run(scenario())

    def test_settings_enter_keyboard_applies(self):
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
                mode = pilot.app.screen.query_one("#set-mode")
                mode.value = "safe"
                await pilot.pause(0.3)
                pilot.app.screen.set_focus(None)
                await pilot.press("enter")
                await pilot.pause(0.5)
                assert not isinstance(pilot.app.screen, SettingsModal)
                assert self.app.config.mode == "safe"
        self._run(scenario())

    def test_suggest_lists_prefix_matches(self):
        from textual.widgets import Input, Label

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                box = pilot.app.screen.query_one("#suggest", Label)
                cmd = pilot.app.screen.query_one("#cmd", Input)
                assert not box.has_class("visible")

                cmd.value = "che"
                await pilot.pause()
                names = [item[0] for item in ui._suggest_items]
                assert names == sorted(names, key=lambda n: (len(n), n))
                assert all(n.startswith("che") for n in names)
                assert box.has_class("visible")
        self._run(scenario())

    def test_suggest_tab_completes_without_sending(self):
        from textual.widgets import Input, Label

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                box = pilot.app.screen.query_one("#suggest", Label)
                cmd = pilot.app.screen.query_one("#cmd", Input)
                cmd.focus()
                await pilot.press("d", "e")
                await pilot.pause()
                assert box.has_class("visible")
                assert ui._suggest_items[0][0] == "deps"
                before = len(ui._log().lines)

                await pilot.press("tab")
                await pilot.pause()
                assert cmd.value == "deps"
                assert cmd.cursor_position == len("deps")
                assert not box.has_class("visible")
                assert pilot.app.focused is cmd
                assert len(ui._log().lines) == before
                assert ui._cmd_history == []
        self._run(scenario())

    def test_suggest_arrows_own_history_when_visible(self):
        from textual.widgets import Input, Label

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                box = pilot.app.screen.query_one("#suggest", Label)
                cmd = pilot.app.screen.query_one("#cmd", Input)
                cmd.focus()
                await pilot.press("d")
                await pilot.pause()
                assert [item[0] for item in ui._suggest_items][:3] == [
                    "deps", "destruct", "defs"]

                await pilot.press("down")
                await pilot.pause()
                assert ui._suggest_idx == 1
                assert cmd.value == "d"
                await pilot.press("up")
                await pilot.pause()
                assert ui._suggest_idx == 0
                await pilot.press("up")
                await pilot.pause()
                assert ui._suggest_idx == 0
                assert cmd.value == "d"
                assert ui._cmd_hist_idx is None
        self._run(scenario())

    def test_suggest_escape_hides_then_clears(self):
        from textual.widgets import Input, Label

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                box = pilot.app.screen.query_one("#suggest", Label)
                cmd = pilot.app.screen.query_one("#cmd", Input)
                cmd.focus()
                await pilot.press("c", "h")
                await pilot.pause()
                assert box.has_class("visible")

                await pilot.press("escape")
                await pilot.pause()
                assert not box.has_class("visible")
                assert cmd.value == "ch"

                await pilot.press("escape")
                await pilot.pause()
                assert cmd.value == ""
        self._run(scenario())

    def test_suggest_hidden_when_disabled_or_too_short(self):
        from textual.widgets import Input, Label

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                box = pilot.app.screen.query_one("#suggest", Label)
                cmd = pilot.app.screen.query_one("#cmd", Input)

                self.app.config.autocomplete_min_chars = 3
                cmd.value = "ch"
                await pilot.pause()
                assert not box.has_class("visible")

                self.app.config.autocomplete_min_chars = 1
                cmd.value = "zzz"
                await pilot.pause()
                assert not box.has_class("visible")

                cmd.value = "che"
                await pilot.pause()
                assert box.has_class("visible")

                self.app.config.autocomplete_enabled = False
                cmd.value = "chec"
                await pilot.pause()
                assert not box.has_class("visible")
        self._run(scenario())

    def test_animation_tick_is_safe_after_teardown(self):
        """A late animation tick must not raise after the screen is gone."""

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
            # The app is shut down and the default screen's children are
            # detached. A queued animation timer tick used to fire here and
            # raise NoMatches for "#pet-box", failing an unrelated test.
            ui._tick()
            ui._refresh_pet(animate=True)
        self._run(scenario())

    def test_suggest_respects_max_items(self):
        from textual.widgets import Input

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            self.app.config.autocomplete_max_items = 3
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                cmd = pilot.app.screen.query_one("#cmd", Input)
                cmd.value = ""
                await pilot.pause()
                assert len(ui._suggest_matches("")) == 0
                matches = ui._suggest_matches("d")
                assert len(matches) == 3
                assert all(name.startswith("d") for name, _, _ in matches)
        self._run(scenario())

    def test_suggest_ranks_prefix_before_substring(self):
        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                # Prefix matches come first and keep their original order.
                names = [n for n, _, _ in ui._suggest_matches("d")]
                assert names[:3] == ["deps", "destruct", "defs"]
                # Substring matches are now allowed, but always rank below the
                # prefix hits: "c" must surface the c-commands first.
                c_names = [n for n, _, _ in ui._suggest_matches("c")]
                assert c_names[0] == "checkpoint"
                assert "echo" in c_names
                assert c_names.index("echo") > c_names.index("checkpoint")
                # A query in the middle of a name now resolves the command.
                assert [n for n, _, _ in ui._suggest_matches("eck")] == [
                    "checkpoint"]
                # Matching the localized description works too.
                assert "tests" in [n for n, _, _ in ui._suggest_matches("test")]
                assert [n for n, _, _ in ui._suggest_matches("zzzz")] == []
                # No raw i18n keys may leak into the suggestion rows.
                for _n, usage, detail in ui._suggest_matches("e"):
                    assert "cmd." not in usage and "cmd." not in detail
        self._run(scenario())

    def test_suggest_prefix_match_respects_case_setting(self):
        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                self.app.config.autocomplete_case_insensitive = True
                assert [n for n, _, _ in ui._suggest_matches("DE")] == [
                    n for n, _, _ in ui._suggest_matches("de")]
                self.app.config.autocomplete_case_insensitive = False
                assert [n for n, _, _ in ui._suggest_matches("DE")] == []
        self._run(scenario())

    def test_suggest_mouse_click_selects_then_tab_applies(self):
        from textual.geometry import Offset
        from textual.widgets import Input, Label

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                box = pilot.app.screen.query_one("#suggest", Label)
                cmd = pilot.app.screen.query_one("#cmd", Input)
                cmd.focus()
                cmd.value = "d"
                await pilot.pause()
                assert len(ui._suggest_items) >= 2
                expected = ui._suggest_items[1][0]

                before = cmd.value
                await pilot.click("#suggest", offset=Offset(3, 2))
                await pilot.pause()
                assert ui._suggest_idx == 1
                assert cmd.value == before
                assert pilot.app.focused is cmd
                assert box.has_class("visible")

                await pilot.press("tab")
                await pilot.pause()
                assert cmd.value == expected
                assert not box.has_class("visible")
        self._run(scenario())

    def test_suggest_mouse_click_on_border_is_ignored(self):
        from textual.geometry import Offset
        from textual.widgets import Input

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                cmd = pilot.app.screen.query_one("#cmd", Input)
                cmd.focus()
                cmd.value = "d"
                await pilot.pause()
                await pilot.click("#suggest", offset=Offset(3, 2))
                await pilot.pause()
                assert ui._suggest_idx == 1
                # Top border maps to row -1 and must not change selection.
                await pilot.click("#suggest", offset=Offset(3, 0))
                await pilot.pause()
                assert ui._suggest_idx == 1
        self._run(scenario())

    def test_suggest_mouse_click_past_last_item_is_ignored(self):
        from textual.geometry import Offset
        from textual.widgets import Input

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                cmd = pilot.app.screen.query_one("#cmd", Input)
                cmd.focus()
                cmd.value = "d"
                await pilot.pause()
                count = len(ui._suggest_items)
                assert count >= 1
                await pilot.click(
                    "#suggest", offset=Offset(3, count + 1))
                await pilot.pause()
                assert ui._suggest_idx == 0
        self._run(scenario())

    def test_settings_renders_autocomplete_controls(self):
        from textual.widgets import Input, Switch
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
                screen = pilot.app.screen
                assert isinstance(screen, SettingsModal)
                assert screen.query_one("#set-ac-enabled", Switch).value
                assert screen.query_one(
                    "#set-ac-case-insensitive", Switch).value
                assert screen.query_one(
                    "#set-ac-descriptions", Switch).value
                assert screen.query_one("#set-ac-min-chars", Input).value == "1"
                assert screen.query_one("#set-ac-max-items", Input).value == "8"
        self._run(scenario())

    def test_settings_applies_autocomplete_switches(self):
        from textual.widgets import Switch
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
                screen = pilot.app.screen
                assert isinstance(screen, SettingsModal)
                screen.query_one("#set-ac-enabled", Switch).value = False
                screen.query_one(
                    "#set-ac-case-insensitive", Switch).value = False
                screen.query_one(
                    "#set-ac-descriptions", Switch).value = False
                await pilot.pause(0.3)
                await pilot.click("#set-apply")
                await pilot.pause(0.5)
                assert self.app.config.autocomplete_enabled is False
                assert self.app.config.autocomplete_case_insensitive is False
                assert self.app.config.autocomplete_show_descriptions is False
        self._run(scenario())

    def test_settings_autocomplete_int_inputs_clamped(self):
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
                screen = pilot.app.screen
                assert isinstance(screen, SettingsModal)

                max_items = screen.query_one("#set-ac-max-items", Input)
                max_items.value = "999"
                await max_items.action_submit()
                await pilot.pause(0.2)
                assert screen._draft.autocomplete_max_items == 50

                max_items.value = "0"
                await max_items.action_submit()
                await pilot.pause(0.2)
                assert screen._draft.autocomplete_max_items == 1

                min_chars = screen.query_one("#set-ac-min-chars", Input)
                min_chars.value = "-5"
                await min_chars.action_submit()
                await pilot.pause(0.2)
                assert screen._draft.autocomplete_min_chars == 0

                min_chars.value = "3"
                await min_chars.action_submit()
                await pilot.pause(0.2)
                await pilot.click("#set-apply")
                await pilot.pause(0.5)
                assert self.app.config.autocomplete_min_chars == 3
                assert self.app.config.autocomplete_max_items == 1
        self._run(scenario())

    def test_settings_autocomplete_rejects_non_integer(self):
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
                screen = pilot.app.screen
                assert isinstance(screen, SettingsModal)
                field = screen.query_one("#set-ac-max-items", Input)
                field.value = "abc"
                await field.action_submit()
                await pilot.pause(0.2)
                assert screen._draft.autocomplete_max_items == 8
        self._run(scenario())

    def test_settings_disabled_autocomplete_hides_suggestions(self):
        from textual.widgets import Input, Switch
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
                screen = pilot.app.screen
                assert isinstance(screen, SettingsModal)
                screen.query_one("#set-ac-enabled", Switch).value = False
                await pilot.pause(0.3)
                await pilot.click("#set-apply")
                await pilot.pause(0.5)
                cmd = pilot.app.query_one("#cmd", Input)
                cmd.value = "d"
                await pilot.pause(0.2)
                assert ui._suggest_matches("d") == []
                assert not pilot.app.query_one(
                    "#suggest").has_class("visible")
        self._run(scenario())

    def test_cmd_history_navigation(self):
        from textual.widgets import Input

        async def scenario():
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 60)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                cmd = pilot.app.query_one("#cmd", Input)
                cmd.value = "attempts +5"
                cmd.focus()
                await pilot.press("enter")
                await pilot.pause()
                cmd.value = "attempts +10"
                cmd.focus()
                await pilot.press("enter")
                await pilot.pause()
                cmd.focus()
                await pilot.press("up")
                await pilot.pause()
                assert cmd.value == "attempts +10"
                await pilot.press("up")
                await pilot.pause()
                assert cmd.value == "attempts +5"
                await pilot.press("down")
                await pilot.pause()
                assert cmd.value == "attempts +10"
                await pilot.press("down")
                await pilot.pause()
                assert cmd.value == ""
                await pilot.press("down")
                await pilot.pause()
                assert cmd.value == ""
        self._run(scenario())

    def test_hotkeys_run_commands(self):
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
                cmd = pilot.app.query_one("#cmd", Input)
                await pilot.press("ctrl+1")
                await pilot.pause(0.5)
                assert not isinstance(pilot.app.screen, SettingsModal)
                assert cmd.has_focus
                await pilot.press("ctrl+3")
                await pilot.pause(0.5)
                assert not isinstance(pilot.app.screen, SettingsModal)
                assert cmd.has_focus
                await pilot.press("ctrl+6")
                await pilot.pause(0.5)
                assert not isinstance(pilot.app.screen, SettingsModal)
                assert cmd.has_focus
                await pilot.press("ctrl+4")
                await pilot.pause(0.5)
                assert isinstance(pilot.app.screen, SettingsModal)
                await pilot.press("escape")
                await pilot.pause(0.5)
                assert not isinstance(pilot.app.screen, SettingsModal)
        self._run(scenario())

    def _pet_scenario(self, size=(160, 40)):
        async def scenario(body):
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=size) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                await body(pilot, ui)
        return scenario

    def test_tamagotchi_toggle_hides_and_shows_panels(self):
        async def body(pilot, ui):
            wrap = pilot.app.query_one("#pet-wrap")
            stats = pilot.app.query_one("#pet-stats")
            assert wrap.display and stats.display

            self.app.config.tamagotchi_enabled = False
            ui._apply_pet_visibility()
            await pilot.pause()
            assert not wrap.display and not stats.display

            self.app.config.tamagotchi_enabled = True
            ui._apply_pet_visibility()
            await pilot.pause()
            assert wrap.display and stats.display
        self._run(self._pet_scenario()(body))

    def test_settings_apply_toggles_pet_visibility(self):
        from textual.widgets import Switch
        from nix.ui import SettingsModal

        async def body(pilot, ui):
            self.app.config.tamagotchi_enabled = True
            self.app.handle_command("settings")
            await pilot.pause(0.5)
            screen = pilot.app.screen
            assert isinstance(screen, SettingsModal)
            screen.query_one("#set-tamagotchi", Switch).value = False
            await pilot.pause(0.2)
            screen.query_one("#set-apply").press()
            await pilot.pause(0.5)
            assert not pilot.app.query_one("#pet-wrap").display
            assert not pilot.app.query_one("#pet-stats").display
        self._run(self._pet_scenario()(body))

    def test_avatar_toggle_shows_placeholder(self):
        from textual.widgets import Static

        async def body(pilot, ui):
            self.app.config.avatar_enabled = False
            ui._refresh_pet()
            await pilot.pause()
            box = pilot.app.query_one("#pet-box", Static)
            assert ui._t("pet.avatar_off") in str(box.render())

            self.app.config.avatar_enabled = True
            ui._refresh_pet()
            await pilot.pause()
            assert ui._t("pet.avatar_off") not in box.render().plain
        self._run(self._pet_scenario()(body))

    def test_auto_scan_runs_once_at_startup(self):
        calls = []

        async def body(pilot, ui):
            assert calls == [Path(self.root)]
            ui._auto_scan_if_enabled()
            assert calls == [Path(self.root)]
        original = nix.ui.scan_project
        nix.ui.scan_project = lambda root: calls.append(Path(root)) or _empty_info()
        try:
            self._run(self._pet_scenario()(body))
        finally:
            nix.ui.scan_project = original

    def test_auto_scan_skipped_when_disabled(self):
        calls = []

        async def body(pilot, ui):
            assert calls == []
        original = nix.ui.scan_project
        self.app.config.auto_scan = False
        nix.ui.scan_project = lambda root: calls.append(Path(root)) or _empty_info()
        try:
            self._run(self._pet_scenario()(body))
        finally:
            nix.ui.scan_project = original

    def test_registry_covers_every_setting_and_derived_maps(self):
        from nix.ui import (AC_SPEC_IDS, FLOAT_KEYS, INT_KEYS, PATHS_KEYS,
                            SETTING_SPECS, TOGGLE_KEYS)

        keys = [spec.key for spec in SETTING_SPECS]
        assert len(keys) == len(set(keys)), "duplicate config key in registry"
        ids = [spec.widget_id for spec in SETTING_SPECS]
        assert len(ids) == len(set(ids)), "duplicate widget id in registry"

        stable = {
            "set-tamagotchi", "set-animations", "set-avatar", "set-sounds",
            "set-auto-scan", "set-checkpoint", "set-git", "set-ac-enabled",
            "set-ac-case-insensitive", "set-ac-descriptions",
            "set-ac-min-chars", "set-ac-max-items", "set-clock",
            "set-log-max-lines", "set-animation-interval",
            "set-history-size", "set-pill-cooldown", "set-timeout",
            "set-protected-paths",
        }
        assert stable == set(ids)

        for wid in AC_SPEC_IDS:
            assert wid in TOGGLE_KEYS or wid in INT_KEYS
        for spec in SETTING_SPECS:
            if spec.kind == "switch":
                assert TOGGLE_KEYS[spec.widget_id] == spec.key
            elif spec.kind == "int":
                assert INT_KEYS[spec.widget_id][0] == spec.key
            elif spec.kind == "float":
                assert FLOAT_KEYS[spec.widget_id][0] == spec.key
            elif spec.kind == "paths":
                assert PATHS_KEYS[spec.widget_id] == spec.key

    def test_settings_renders_every_registry_control(self):
        from textual.widgets import Input, Switch
        from nix.ui import SETTING_SPECS, SettingsModal

        async def body(pilot, ui):
            self.app.handle_command("settings")
            await pilot.pause(0.5)
            screen = pilot.app.screen
            assert isinstance(screen, SettingsModal)
            for spec in SETTING_SPECS:
                cls = Switch if spec.kind == "switch" else Input
                assert screen.query_one(f"#{spec.widget_id}", cls) is not None
        self._run(self._pet_scenario()(body))

    def test_settings_applies_clock_and_log_limits_live(self):
        from textual.widgets import RichLog, Switch
        from nix.ui import NixHeader, SettingsModal

        async def body(pilot, ui):
            header = pilot.app.query_one(NixHeader)
            assert header.query_one("#hdr-clock").display is True
            assert header.query_one("#hdr-noclock").display is False
            assert pilot.app.query_one("#log", RichLog).max_lines == 500

            self.app.handle_command("settings")
            await pilot.pause(0.5)
            screen = pilot.app.screen
            assert isinstance(screen, SettingsModal)
            screen.query_one("#set-clock", Switch).value = False
            screen.query_one("#set-log-max-lines").value = "123"
            await pilot.click("#set-apply")
            await pilot.pause(0.5)

            assert self.app.config.show_clock is False
            assert self.app.config.log_max_lines == 123
            assert header.query_one("#hdr-clock").display is False
            assert header.query_one("#hdr-noclock").display is True
            assert pilot.app.query_one("#log", RichLog).max_lines == 123
        self._run(self._pet_scenario()(body))

    def test_settings_applies_unssubmitted_typed_values(self):
        from textual.widgets import Input
        from nix.ui import SettingsModal

        async def body(pilot, ui):
            self.app.handle_command("settings")
            await pilot.pause(0.5)
            screen = pilot.app.screen
            assert isinstance(screen, SettingsModal)
            # Typed but never submitted: Apply must still pick this up.
            screen.query_one("#set-animation-interval", Input).value = "0.25"
            screen.query_one("#set-history-size", Input).value = "7"
            await pilot.click("#set-apply")
            await pilot.pause(0.5)
            assert self.app.config.animation_interval == 0.25
            assert self.app.config.command_history_size == 7
            assert ui._anim_timer is not None
        self._run(self._pet_scenario()(body))

    def test_settings_clamps_numeric_ranges_on_apply(self):
        from textual.widgets import Input
        from nix.ui import SettingsModal

        async def body(pilot, ui):
            self.app.handle_command("settings")
            await pilot.pause(0.5)
            screen = pilot.app.screen
            assert isinstance(screen, SettingsModal)
            screen.query_one("#set-log-max-lines", Input).value = "99999"
            screen.query_one("#set-animation-interval", Input).value = "0.0"
            screen.query_one("#set-history-size", Input).value = "-4"
            screen.query_one("#set-pill-cooldown", Input).value = "5000"
            screen.query_one("#set-timeout", Input).value = "1"
            await pilot.click("#set-apply")
            await pilot.pause(0.5)
            assert self.app.config.log_max_lines == 5000
            assert self.app.config.animation_interval == 0.1
            assert self.app.config.command_history_size == 0
            assert self.app.config.pill_cooldown_minutes == 1440
            assert self.app.config.default_command_timeout == 5
        self._run(self._pet_scenario()(body))

    def test_settings_rejects_non_numeric_on_apply_and_stays_open(self):
        from textual.widgets import Input
        from nix.ui import SettingsModal

        async def body(pilot, ui):
            self.app.handle_command("settings")
            await pilot.pause(0.5)
            screen = pilot.app.screen
            assert isinstance(screen, SettingsModal)
            screen.query_one("#set-animation-interval", Input).value = "fast"
            await pilot.click("#set-apply")
            await pilot.pause(0.5)
            assert isinstance(pilot.app.screen, SettingsModal)
            assert self.app.config.animation_interval == 1.0
        self._run(self._pet_scenario()(body))

    def test_settings_normalizes_protected_paths_on_apply(self):
        from textual.widgets import Input
        from nix.ui import SettingsModal

        async def body(pilot, ui):
            self.app.handle_command("settings")
            await pilot.pause(0.5)
            screen = pilot.app.screen
            assert isinstance(screen, SettingsModal)
            field = screen.query_one("#set-protected-paths", Input)
            field.value = "  notes.md , , notes.md,sub\\dir\\ ;   "
            await pilot.click("#set-apply")
            await pilot.pause(0.5)
            # parse_path_list() normalises separators to "/" and strips
            # trailing slashes while preserving order and dropping dupes.
            assert self.app.config.protected_paths == [
                "notes.md", "sub/dir",
            ]
        self._run(self._pet_scenario()(body))

    def test_settings_normalizes_existing_protected_paths_on_apply(self):
        from nix.ui import SettingsModal

        async def body(pilot, ui):
            self.app.config.protected_paths = ["  a.md  ", "a.md", "", "b.md"]
            self.app.handle_command("settings")
            await pilot.pause(0.5)
            screen = pilot.app.screen
            assert isinstance(screen, SettingsModal)
            await pilot.click("#set-apply")
            await pilot.pause(0.5)
            assert self.app.config.protected_paths == ["a.md", "b.md"]
        self._run(self._pet_scenario()(body))

    def test_command_history_trimmed_by_configured_size(self):
        async def body(pilot, ui):
            cmd = pilot.app.query_one("#cmd")
            for command in ("deps", "destruct", "defs", "notes"):
                cmd.value = command
                await cmd.action_submit()
                await pilot.pause(0.1)
            assert ui._cmd_history == ["deps", "destruct", "defs", "notes"]

            self.app.config.command_history_size = 2
            ui._apply_history_limit()
            assert ui._cmd_history == ["defs", "notes"]

            self.app.config.command_history_size = 0
            ui._apply_history_limit()
            assert ui._cmd_history == []
        self._run(self._pet_scenario()(body))

    def test_command_history_trimmed_on_each_submitted_command(self):
        async def body(pilot, ui):
            self.app.config.command_history_size = 2
            cmd = pilot.app.query_one("#cmd")
            for command in ("deps", "destruct", "defs"):
                cmd.value = command
                await cmd.action_submit()
                await pilot.pause(0.1)
            assert ui._cmd_history == ["destruct", "defs"]
        self._run(self._pet_scenario()(body))


def _empty_info():
    from nix.scanner import ProjectInfo

    return ProjectInfo(root=Path("."), files=0, directories=0, extensions={},
                       functions=0, classes=0, total_lines=0, source_files=0)


class TestLayoutHelpers(unittest.TestCase):
    """Width-correct column layout for localized (Cyrillic) text."""

    def test_ljust_pads_to_exact_cell_width(self):
        from rich.cells import cell_len

        for text, width in (("Core", 12), ("Ядро", 12), ("Настройки", 12),
                            ("", 8)):
            out = nix.ui._ljust(text, width)
            self.assertEqual(cell_len(out), width, msg=text)
            self.assertTrue(out.startswith(text))

    def test_ljust_truncates_overlong_without_exceeding(self):
        from rich.cells import cell_len

        long_usage = "wrap <файл> <строка> in <оп> [--слот значение] [--apply]"
        for width in (12, 22, 40):
            out = nix.ui._ljust(long_usage, width)
            self.assertLessEqual(cell_len(out), width, msg=width)
            self.assertTrue(out.endswith("\u2026"), msg=width)

    def test_ljust_keeps_column_aligned_across_mixed_scripts(self):
        from rich.cells import cell_len

        # Every rendered label must occupy the same number of cells, which is
        # what makes the two columns line up in the terminal.
        labels = ["Root", "Mode", "Files", "Корень", "Режим", "Файлы"]
        padded = [nix.ui._ljust(label, 20) for label in labels]
        self.assertEqual({cell_len(p) for p in padded}, {20})

    def test_clip_respects_cell_width(self):
        from rich.cells import cell_len

        text = "gen <тип> <имя> [--into файл] [--at строка] [--apply]"
        for limit in (10, 20, 40):
            out = nix.ui._clip(text, limit)
            self.assertLessEqual(cell_len(out), limit, msg=limit)
            self.assertTrue(out.endswith("\u2026"), msg=limit)

    def test_clip_short_text_untouched(self):
        from rich.cells import cell_len

        self.assertEqual(nix.ui._clip("Ядро", 40), "Ядро")

    def test_head_uppercases_without_widening(self):
        from rich.cells import cell_len

        self.assertEqual(nix.ui._head("Core"), "CORE")
        # 'ß'.upper() is 'SS': two cells from one. The original must win.
        widened = "ßrden"
        self.assertLessEqual(cell_len(nix.ui._head(widened)),
                             cell_len(widened))

    def test_head_keeps_ascii_headings_uppercase(self):
        self.assertEqual(nix.ui._head("Project Status"), "PROJECT STATUS")


class TestSuggestLocalization(unittest.TestCase):
    """Autocomplete must match Cyrillic queries against Russian descriptions."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.root = Path(self._tmp.name)
        self.app = NixApp()

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_russian_query_matches_russian_descriptions(self):
        async def scenario():
            self.app.config.language = "ru"
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                # "настр" only appears in the Russian description of settings.
                assert [n for n, _, _ in ui._suggest_matches("настр")] == [
                    "settings"]
                # "журнал" appears in the Russian descriptions of these three.
                assert set(n for n, _, _ in ui._suggest_matches("журнал")) == {
                    "logs", "history", "journal"}
                # Details shown next to a Russian match are Russian too.
                details = [d for _n, _u, d in ui._suggest_matches("настр")]
                self.assertTrue(any("Настройки" in d or "настройки" in d
                                    for d in details), details)

        asyncio.run(scenario())

    def test_suggest_box_becomes_visible_and_tab_applies(self):
        async def scenario():
            self.app.config.language = "ru"
            ui = NixUI(self.app)
            self.app.ui = ui
            async with ui.run_test(size=(160, 40)) as pilot:
                await pilot.pause()
                pilot.app.screen.query_one("Input").value = "Tester"
                await pilot.press("enter")
                await pilot.pause()
                cmd = pilot.app.query_one("#cmd")
                box = pilot.app.query_one("#suggest")
                cmd.focus()
                cmd.value = "пит"
                await pilot.pause()
                assert ui._suggest_items
                assert "visible" in box.classes
                # Applying a suggestion clears the list, so capture the
                # expected value before pressing Tab.
                expected = ui._suggest_items[0][0]
                await pilot.press("tab")
                await pilot.pause()
                assert cmd.value == expected
                assert not ui._suggest_items

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()