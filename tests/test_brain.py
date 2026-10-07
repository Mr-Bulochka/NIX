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

    def test_utf8_bom_is_tolerated(self):
        root, nix = self._make_project()
        path = root / "api.py"
        path.write_text("\ufeff" + path.read_text(encoding="utf-8"),
                        encoding="utf-8")
        brain = Brain(nix, root)
        index = brain.build()
        names = [s["name"] for s in index["symbols"]]
        self.assertIn("fetch", names)


class TestBrainStaleness(unittest.TestCase):
    """The index must follow the sources, not freeze on the first scan."""

    def _project(self):
        tmp = Path(tempfile.mkdtemp())
        root = tmp / "proj"
        root.mkdir()
        (root / "api.py").write_text(
            "def first():\n    return 1\n", encoding="utf-8")
        return root, tmp / "nixstate"

    def test_ensure_rebuilds_after_a_source_edit(self):
        root, nix = self._project()
        brain = Brain(nix, root)
        index, _ = brain.ensure()
        self.assertIn("first", [s["name"] for s in index["symbols"]])

        # Add a new function. The old ensure() returned the frozen index.
        import os
        import time
        (root / "api.py").write_text(
            "def first():\n    return 1\n\ndef second():\n    return 2\n",
            encoding="utf-8")
        # Make the mtime bump unambiguous on coarse-grained filesystems.
        stamp = time.time() + 2
        os.utime(root / "api.py", (stamp, stamp))

        index, _ = brain.ensure()
        names = [s["name"] for s in index["symbols"]]
        self.assertIn("second", names,
                      "index went stale: ensure() must rebuild after an edit")

    def test_ensure_rebuilds_after_a_new_file(self):
        root, nix = self._project()
        brain = Brain(nix, root)
        index, _ = brain.ensure()
        self.assertNotIn("added", [s["name"] for s in index["symbols"]])
        (root / "extra.py").write_text(
            "def added():\n    return 3\n", encoding="utf-8")
        index, _ = brain.ensure()
        self.assertIn("added", [s["name"] for s in index["symbols"]])

    def test_ensure_does_not_rebuild_when_nothing_changed(self):
        root, nix = self._project()
        brain = Brain(nix, root)
        brain.ensure()
        before = brain.index_path.stat().st_mtime_ns
        import time
        time.sleep(0.01)
        brain.ensure()
        self.assertEqual(brain.index_path.stat().st_mtime_ns, before,
                         "unchanged sources must not trigger a rebuild")


if __name__ == "__main__":
    unittest.main()