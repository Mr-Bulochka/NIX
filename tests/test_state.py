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


class TestAtomicWrites(unittest.TestCase):
    """State must never be left half-written.

    A plain ``write_text`` truncates first, so an interruption mid-write leaves
    invalid JSON; ``read_json`` then returns the default, which silently
    reverts every user setting.
    """

    def test_write_json_leaves_no_temp_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = State(Path(tmp))
            state.write_json("thing.json", {"a": 1})
            self.assertTrue((state.nix / "thing.json").is_file())
            leftovers = [p.name for p in state.nix.rglob("*.tmp")]
            self.assertEqual(leftovers, [], f"temp files left: {leftovers}")

    def test_failed_write_leaves_previous_content_intact(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = State(Path(tmp))
            state.write_json("thing.json", {"a": 1})
            target = state.nix / "thing.json"
            original = target.read_text(encoding="utf-8")

            boom = {"a": 1, "b": {1, 2, 3}}  # sets are not JSON serialisable
            with self.assertRaises(TypeError):
                state.write_json("thing.json", boom)

            self.assertEqual(target.read_text(encoding="utf-8"), original,
                             "a failed save must not destroy existing state")
            self.assertEqual(state.read_json("thing.json", default=None),
                             {"a": 1})
            leftovers = [p.name for p in state.nix.rglob("*.tmp")]
            self.assertEqual(leftovers, [], f"temp files left: {leftovers}")

    def test_overwrite_replaces_content_entirely(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = State(Path(tmp))
            state.write_json("thing.json", {"long": "x" * 500})
            state.write_json("thing.json", {"s": 1})
            self.assertEqual(state.read_json("thing.json"), {"s": 1})


if __name__ == "__main__":
    unittest.main()
