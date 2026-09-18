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
