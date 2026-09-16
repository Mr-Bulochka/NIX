import unittest

from rich.text import Text

from nix.avatar import (
    CYCLOPS_PAL,
    OCTOPUS_PAL,
    PALETTES,
    POU_PAL,
    TOMMY_PAL,
    VARIANTS,
    W,
    H,
    _body_matrix,
    _face,
    _to_text,
    _variant,
    genes_for,
    render,
)


class TestAvatar(unittest.TestCase):
    def test_variant_grids_are_valid(self):
        for v in VARIANTS:
            with self.subTest(variant=v["kind"]):
                self.assertLessEqual(len(v["grid"]), H)
                for row in v["grid"]:
                    self.assertEqual(len(row), W, row)
                    self.assertTrue(all(c in ".#b" for c in row), row)
                self.assertIn("face_y", v)
                self.assertIn("mouth_y", v)

    def test_octopus_in_variants_and_orange(self):
        self.assertIn("octopus", [v["kind"] for v in VARIANTS])
        vm = _variant("octopus")
        self.assertIs(vm["palette"], OCTOPUS_PAL)
        self.assertTrue(OCTOPUS_PAL["hi"].startswith("#ff"))

    def test_easter_egg_palettes(self):
        vm = _variant("pou")
        self.assertIs(vm["palette"], POU_PAL)
        self.assertTrue(vm.get("pou_eyes"))
        vm = _variant("tommy")
        self.assertIs(vm["palette"], TOMMY_PAL)
        vm = _variant("cyclops")
        self.assertIs(vm["palette"], CYCLOPS_PAL)
        self.assertTrue(vm.get("single_eye"))

    def test_octopus_renders_orange_not_palette_colors(self):
        vm = _variant("octopus")
        genes = {"eye": "amber", "variant": "octopus", "palette": "mint"}
        m = _body_matrix(vm, vm["palette"], "seed")
        _face(m, vm, genes, vm["palette"], "curious", False)
        text = _to_text(m, 1)
        self.assertIsInstance(text, Text)
        styles = {str(s.style) for s in text.spans if s.style}
        self.assertTrue(any("#8a2b06" in s for s in styles))
        self.assertFalse(any("#8ef0b4" in s for s in styles))

    def test_genes_are_deterministic_and_valid(self):
        pet = {"name": "Test"}

        class Root:
            name = "proj"
            def __str__(self):
                return "proj"

        g1 = genes_for(Root(), pet)
        g2 = genes_for(Root(), pet)
        self.assertEqual(g1, g2)
        self.assertIn(g1["variant"], [v["kind"] for v in VARIANTS])
        self.assertIn(g1["palette"], PALETTES)

    def test_render_smoke(self):
        pet = {"name": "Test", "body_pattern": "sprout", "mood": "happy",
               "evolution_level": 1}

        class Root:
            name = "proj"
            def __str__(self):
                return "proj"

        for scale in (1, 2):
            text = render(pet, Root(), scale=scale)
            self.assertIn("\u2580", text.plain)


if __name__ == "__main__":
    unittest.main()