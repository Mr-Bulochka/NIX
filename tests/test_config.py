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

    def test_corrupt_file_returns_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            (nix_dir / "config.json").write_text("not json!!!")
            config = ConfigStore(nix_dir).load()
            self.assertEqual(config.attempts, 0)


if __name__ == "__main__":
    unittest.main()
