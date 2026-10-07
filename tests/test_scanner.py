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


class TestScannerLanguageCoverage(unittest.TestCase):
    """`functions` / `classes` must not be silently 0 for non-Python projects.

    The counter used to look for a Python-only ``def `` / ``class `` prefix even
    though it ran for 13 extensions, so a Go or Rust project reported zero of
    both -- indistinguishable from an empty directory in `scan`.
    """

    def test_counts_go_and_rust_functions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.go").write_text(
                "package main\n"
                "func Add(a int, b int) int {\n\treturn a + b\n}\n"
                "func Sub(a int, b int) int {\n\treturn a - b\n}\n",
                encoding="utf-8")
            (root / "lib.rs").write_text(
                "pub fn compute(x: i32) -> i32 {\n    x + 1\n}\n",
                encoding="utf-8")
            info = scan_project(root)
            self.assertGreaterEqual(info.functions, 3,
                                    f"expected Go+Rust functions, got {info.functions}")

    def test_python_fallback_still_counts_methods(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text(
                "class S:\n"
                "    def run(self):\n"
                "        pass\n"
                "def helper():\n"
                "    pass\n", encoding="utf-8")
            info = scan_project(root)
            self.assertEqual(info.functions, 2)
            self.assertEqual(info.classes, 1)

    def test_unknown_extension_still_counted_as_python_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # .rb is in the scan extension list but has no bundled module, so
            # the Python-shaped fallback runs.
            (root / "a.rb").write_text(
                "def ruby_method(arg)\n  arg\nend\nclass Thing:\n  pass\n",
                encoding="utf-8")
            info = scan_project(root)
            self.assertGreaterEqual(info.functions, 1)
            self.assertGreaterEqual(info.classes, 1)


if __name__ == "__main__":
    unittest.main()
