import tempfile
import unittest
from pathlib import Path
from nix.scanner import scan_project


class TestScanner(unittest.TestCase):
    def test_ignores_nix_and_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("def foo(): pass\n", encoding="utf-8")
            (root / ".nix").mkdir()
            (root / ".nix" / "internal.py").write_text("x=1", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("x", encoding="utf-8")
            info = scan_project(root)
            self.assertEqual(info.files, 1)
            self.assertEqual(info.extensions[".py"], 1)

    def test_counts_functions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = (
                "def foo():\n"
                "    pass\n"
                "class Bar:\n"
                "    def baz(self):\n"
                "        pass\n"
            )
            (root / "app.py").write_text(code, encoding="utf-8")
            info = scan_project(root)
            self.assertEqual(info.functions, 2)
            self.assertEqual(info.classes, 1)

    def test_empty_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = scan_project(Path(tmp))
            self.assertEqual(info.files, 0)
            self.assertEqual(info.directories, 0)

    def test_top_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(5):
                (root / f"f{i}.py").write_text("x=1", encoding="utf-8")
            for i in range(3):
                (root / f"f{i}.js").write_text("x=1", encoding="utf-8")
            info = scan_project(root)
            top = info.top_extensions
            self.assertEqual(top[0][0], ".py")
            self.assertEqual(top[0][1], 5)
            self.assertEqual(top[1][0], ".js")
            self.assertEqual(top[1][1], 3)


if __name__ == "__main__":
    unittest.main()
