import tempfile
import unittest
from pathlib import Path
from nix.state import State


class TestState(unittest.TestCase):
    def test_initialize_creates_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = State(root)
            state.initialize()
            self.assertTrue((root / ".nix").is_dir())
            self.assertTrue((root / ".nix" / "state").is_dir())
            self.assertTrue((root / ".nix" / "journal").is_dir())
            self.assertTrue((root / ".nix" / "logs").is_dir())
            self.assertTrue((root / ".nix" / "memory").is_dir())
            self.assertTrue((root / ".nix" / "experiments").is_dir())
            self.assertTrue((root / ".nix" / "checkpoints" / "permanent").is_dir())
            self.assertTrue((root / ".nix" / "checkpoints" / "temporary").is_dir())
            self.assertTrue((root / ".nix" / "pet").is_dir())
            self.assertTrue((root / ".nix" / "origin").is_dir())

    def test_read_write_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = State(Path(tmp))
            state.initialize()
            state.write_json("test/data.json", {"key": "value"})
            result = state.read_json("test/data.json")
            self.assertEqual(result, {"key": "value"})

    def test_read_json_missing_returns_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = State(Path(tmp))
            state.initialize()
            result = state.read_json("nonexistent.json", default=42)
            self.assertEqual(result, 42)

    def test_exists_before_after_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = State(Path(tmp))
            self.assertFalse(state.exists())
            state.initialize()
            self.assertTrue(state.exists())


if __name__ == "__main__":
    unittest.main()
