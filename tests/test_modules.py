import unittest

from nix.modules.engine import (
    apply_wrap,
    find_block_at_line,
    leading_ws,
    render_template,
    scan_blocks,
)
from nix.modules import all_modules, module_for_file, load_module


class TestCodeModule(unittest.TestCase):
    def test_load_python(self):
        mod = load_module("python")
        self.assertIsNotNone(mod)
        self.assertEqual(mod.id, "python")
        self.assertIn(".py", mod.extensions)
        self.assertIn("function", mod.blocks)
        self.assertIn("class", mod.blocks)
        self.assertIn("wrap-in-try", mod.ops)
        self.assertIn("function", mod.gen)

    def test_module_for_file(self):
        self.assertEqual(module_for_file("a.py"), "python")
        self.assertIsNone(module_for_file("a.unknownext"))

    def test_all_modules_contains_python(self):
        ids = [m.id for m in all_modules()]
        self.assertIn("python", ids)


class TestEngineBlocks(unittest.TestCase):
    SRC = (
        "import os\n"
        "\n"
        "def fetch(url, retries=2):\n"
        "    for i in range(retries):\n"
        "        try:\n"
        "            return os.get(url)\n"
        "        except Exception as e:\n"
        "            pass\n"
        "    return None\n"
        "\n"
        "class Client:\n"
        "    def __init__(self, base):\n"
        "        self.base = base\n"
        "\n"
        "    def get(self, path):\n"
        "        return self.base + path\n"
    )

    @classmethod
    def setUpClass(cls):
        cls.lines = cls.SRC.splitlines()
        cls.mod = load_module("python")

    def test_functions_include_nested(self):
        fns = scan_blocks(self.lines, "function", self.mod.blocks["function"])
        names = [f.name for f in fns]
        self.assertEqual(names, ["fetch", "__init__", "get"])
        fetch = fns[0]
        self.assertEqual(fetch.start, 3)
        self.assertEqual(fetch.end, 9)

    def test_class_span(self):
        classes = scan_blocks(self.lines, "class", self.mod.blocks["class"])
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0].name, "Client")
        self.assertEqual(classes[0].start, 11)
        self.assertEqual(classes[0].end, 16)

    def test_find_block_at_line(self):
        b = find_block_at_line(self.lines, 5, self.mod.blocks)
        self.assertIsNotNone(b)
        self.assertEqual(b.kind, "try")
        b2 = find_block_at_line(self.lines, 3, self.mod.blocks)
        self.assertEqual(b2.kind, "function")
        self.assertEqual(b2.name, "fetch")

    def test_leading_ws(self):
        self.assertEqual(leading_ws("    x"), 4)
        self.assertEqual(leading_ws("x"), 0)

    def test_probe_smoke(self):
        probe = self.mod.probe
        for case in probe.get("tests", []):
            lines = case["source"].splitlines()
            for expected in case["blocks"]:
                found = scan_blocks(lines, expected["kind"],
                                    self.mod.blocks[expected["kind"]])
                self.assertTrue(found, case["name"])
                self.assertEqual(found[0].name, expected["name"])


class TestEngineOps(unittest.TestCase):
    def test_wrap_try_preserves_nesting(self):
        lines = (
            "def foo(x):\n"
            "    if x > 0:\n"
            "        return x\n"
            "    return -x\n"
        ).splitlines()
        mod = load_module("python")
        fn = scan_blocks(lines, "function", mod.blocks["function"])[0]
        out = apply_wrap(lines, fn, mod.ops["wrap-in-try"],
                         {"err": "ValueError", "e": "err"})
        text = "\n".join(out)
        self.assertIn("try:", text)
        self.assertIn("except ValueError as err:", text)
        self.assertIn("        if x > 0:", text)
        self.assertTrue(any(l == "            return x" for l in out))

    def test_wrap_default_slots(self):
        lines = ("def f():\n    pass\n").splitlines()
        mod = load_module("python")
        fn = scan_blocks(lines, "function", mod.blocks["function"])[0]
        out = apply_wrap(lines, fn, mod.ops["wrap-in-try"])
        self.assertIn("except Exception as e:", "\n".join(out))

    def test_render_template_drops_empty_slots(self):
        mod = load_module("python")
        rendered = render_template(mod.gen["function"], {
            "name": "foo", "params": "x", "ret": "", "docstring": "",
            "body": "return x", "base": "",
        })
        self.assertNotIn("{{docstring}}", rendered)
        self.assertIn("def foo(x):", rendered)
        self.assertIn("return x", rendered)

    def test_render_template_with_doc(self):
        mod = load_module("python")
        rendered = render_template(mod.gen["class"], {
            "name": "Box", "base": "(object)", "docstring": '"A box."',
            "body": "pass",
        })
        self.assertIn('"A box."', rendered)
        self.assertIn("class Box(object):", rendered)


if __name__ == "__main__":
    unittest.main()