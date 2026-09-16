import tempfile
import unittest
from pathlib import Path

from nix.brain import Brain


class TestBrain(unittest.TestCase):
    def _make_project(self):
        tmp = Path(tempfile.mkdtemp())
        root = tmp / "proj"
        nix = tmp / "nixstate"
        root.mkdir()
        (root / "api.py").write_text(
            "import os\n\n"
            "def fetch(url):\n"
            "    \"\"\"Fetch a url.\"\"\"\n"
            "    return os.get(url)\n"
            "\n"
            "class Client:\n"
            "    def __init__(self):\n"
            "        try:\n"
            "            pass\n"
            "        except ValueError as err:\n"
            "            raise err\n",
            encoding="utf-8")
        (root / "util.py").write_text(
            "def _helper(x):\n    return x + 1\n",
            encoding="utf-8")
        return root, nix

    def test_build_index(self):
        root, nix = self._make_project()
        brain = Brain(nix, root)
        index = brain.build()
        self.assertEqual(index["files"], 2)
        names = [s["name"] for s in index["symbols"]]
        self.assertIn("fetch", names)
        self.assertIn("Client", names)
        self.assertIn("__init__", names)
        self.assertIn("_helper", names)

    def test_patterns_derived(self):
        root, nix = self._make_project()
        brain = Brain(nix, root)
        brain.build()
        _, patterns = brain.load()
        self.assertEqual(patterns["naming_top"], "snake")
        self.assertEqual(patterns["functions"], 3)
        self.assertEqual(patterns["exception_var"], "err")
        self.assertGreaterEqual(patterns["docstrings"], 1)

    def test_ensure_builds_if_missing(self):
        root, nix = self._make_project()
        brain = Brain(nix, root)
        index, patterns = brain.ensure()
        self.assertIn("symbols", index)
        self.assertIn("naming_top", patterns)

    def test_index_file_location(self):
        root, nix = self._make_project()
        brain = Brain(nix, root)
        brain.build()
        self.assertTrue(brain.index_path.exists())
        self.assertTrue(brain.patterns_path.exists())


if __name__ == "__main__":
    unittest.main()