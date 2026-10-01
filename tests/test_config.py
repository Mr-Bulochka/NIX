import json
import tempfile
import unittest
from pathlib import Path
from nix.config import Config, ConfigStore


class TestConfig(unittest.TestCase):
    def test_defaults(self):
        c = Config()
        self.assertEqual(c.theme, "green")
        self.assertEqual(c.mode, "local")
        self.assertEqual(c.attempts, 0)
        self.assertEqual(c.max_attempts, 100)
        self.assertEqual(c.mutation_budget, 10)
        self.assertTrue(c.tamagotchi_enabled)
        self.assertTrue(c.avatar_enabled)
        self.assertTrue(c.auto_scan)
        self.assertFalse(c.sounds_enabled)
        self.assertFalse(c.git_auto_commit)

    def test_toggles_coerce_strings(self):
        c = Config(tamagotchi_enabled="false", avatar_enabled="0",
                   auto_scan="no", sounds_enabled="true",
                   git_auto_commit="1")
        self.assertFalse(c.tamagotchi_enabled)
        self.assertFalse(c.avatar_enabled)
        self.assertFalse(c.auto_scan)
        self.assertTrue(c.sounds_enabled)
        self.assertTrue(c.git_auto_commit)

    def test_toggles_bad_types_fall_back(self):
        c = Config(tamagotchi_enabled=None, avatar_enabled=[], auto_scan=3.5,
                   git_auto_commit={"a": 1})
        self.assertTrue(c.tamagotchi_enabled)
        self.assertTrue(c.avatar_enabled)
        self.assertTrue(c.auto_scan)
        self.assertFalse(c.git_auto_commit)

    def test_invalid_mode_falls_back(self):
        c = Config(mode="invalid")
        self.assertEqual(c.mode, "local")

    def test_attempts_clamped(self):
        c = Config(attempts=-5, max_attempts=100)
        self.assertEqual(c.attempts, 0)
        c2 = Config(attempts=200, max_attempts=100)
        self.assertEqual(c2.attempts, 100)

    def test_enabled_modules_default(self):
        c = Config()
        self.assertIsNone(c.enabled_modules)

    def test_enabled_modules_dedupes_and_filters(self):
        c = Config(enabled_modules=["python", "go", "python", "b@d", 5])
        self.assertEqual(c.enabled_modules, ["python", "go"])

    def test_enabled_modules_non_list_resets(self):
        c = Config(enabled_modules={"python": True})
        self.assertIsNone(c.enabled_modules)

    def test_priority_lang_valid(self):
        c = Config(priority_lang="python")
        self.assertEqual(c.priority_lang, "python")

    def test_priority_lang_invalid(self):
        c = Config(priority_lang="my lang!")
        self.assertEqual(c.priority_lang, "")
        c2 = Config(priority_lang=42)
        self.assertEqual(c2.priority_lang, "")

    def test_autocomplete_defaults(self):
        c = Config()
        self.assertTrue(c.autocomplete_enabled)
        self.assertEqual(c.autocomplete_max_items, 8)
        self.assertTrue(c.autocomplete_case_insensitive)
        self.assertEqual(c.autocomplete_min_chars, 1)
        self.assertTrue(c.autocomplete_show_descriptions)

    def test_autocomplete_clamped(self):
        c = Config(autocomplete_max_items=0, autocomplete_min_chars=99)
        self.assertEqual(c.autocomplete_max_items, 1)
        self.assertEqual(c.autocomplete_min_chars, 10)
        c2 = Config(autocomplete_max_items=500, autocomplete_min_chars=-3)
        self.assertEqual(c2.autocomplete_max_items, 50)
        self.assertEqual(c2.autocomplete_min_chars, 0)

    def test_autocomplete_bad_types_fall_back(self):
        c = Config(autocomplete_max_items="abc", autocomplete_min_chars=None,
                   autocomplete_enabled="maybe")
        self.assertEqual(c.autocomplete_max_items, 8)
        self.assertEqual(c.autocomplete_min_chars, 1)
        self.assertTrue(c.autocomplete_enabled)

    def test_autocomplete_coerces_strings(self):
        c = Config(autocomplete_enabled="false",
                   autocomplete_case_insensitive="no",
                   autocomplete_show_descriptions="1",
                   autocomplete_max_items="12",
                   autocomplete_min_chars="3")
        self.assertFalse(c.autocomplete_enabled)
        self.assertFalse(c.autocomplete_case_insensitive)
        self.assertTrue(c.autocomplete_show_descriptions)
        self.assertEqual(c.autocomplete_max_items, 12)
        self.assertEqual(c.autocomplete_min_chars, 3)


class TestConfigStore(unittest.TestCase):
    def test_load_creates_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConfigStore(Path(tmp) / ".nix")
            config = store.load()
            self.assertEqual(config.attempts, 0)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            store = ConfigStore(nix_dir)
            config = store.load()
            config.attempts = 42
            config.mode = "safe"
            store.save(config)
            loaded = store.load()
            self.assertEqual(loaded.attempts, 42)
            self.assertEqual(loaded.mode, "safe")

    def test_save_and_load_module_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            store = ConfigStore(nix_dir)
            config = store.load()
            config.enabled_modules = ["python", "go"]
            config.priority_lang = "go"
            store.save(config)
            loaded = store.load()
            self.assertEqual(loaded.enabled_modules, ["python", "go"])
            self.assertEqual(loaded.priority_lang, "go")

    def test_corrupt_file_returns_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            (nix_dir / "config.json").write_text("not json!!!")
            config = ConfigStore(nix_dir).load()
            self.assertEqual(config.attempts, 0)

    def test_old_config_gets_autocomplete_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            (nix_dir / "config.json").write_text(
                json.dumps({"theme": "blue", "attempts": 3}), "utf-8")
            config = ConfigStore(nix_dir).load()
            self.assertEqual(config.theme, "blue")
            self.assertEqual(config.attempts, 3)
            self.assertTrue(config.autocomplete_enabled)
            self.assertEqual(config.autocomplete_max_items, 8)

    def test_autocomplete_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            store = ConfigStore(nix_dir)
            config = store.load()
            config.autocomplete_enabled = False
            config.autocomplete_max_items = 4
            config.autocomplete_case_insensitive = False
            config.autocomplete_min_chars = 2
            config.autocomplete_show_descriptions = False
            store.save(config)
            loaded = store.load()
            self.assertFalse(loaded.autocomplete_enabled)
            self.assertEqual(loaded.autocomplete_max_items, 4)
            self.assertFalse(loaded.autocomplete_case_insensitive)
            self.assertEqual(loaded.autocomplete_min_chars, 2)
            self.assertFalse(loaded.autocomplete_show_descriptions)

    def test_corrupt_typed_values_return_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            (nix_dir / "config.json").write_text(
                json.dumps({"attempts": "abc", "mode": "nope"}), "utf-8")
            config = ConfigStore(nix_dir).load()
            self.assertEqual(config.attempts, 0)
            self.assertEqual(config.mode, "local")


if __name__ == "__main__":
    unittest.main()
