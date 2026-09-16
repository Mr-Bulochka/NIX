import unittest

from rich.text import Text

from nix.avatar import (
    CYCLOPS_PAL,
    EYES,
    OCTOPUS_PAL,
    PALETTES,
    POU_PAL,
    TOMMY_PAL,
    VARIANTS,
    W,
    H,
    LOOKS,
    _body_matrix,
    _face,
    _to_text,
    _variant,
    genes_for,
    idle_look,
    render,
)


def _styled(text: Text) -> str:
    import io
    from rich.console import Console
    buf = io.StringIO()
    Console(file=buf, force_terminal=True,
            color_system="truecolor").print(text, end="")
    return buf.getvalue()


class _Root:
    name = "proj"

    def __str__(self):
        return "proj"


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
        g1 = genes_for(_Root(), pet)
        g2 = genes_for(_Root(), pet)
        self.assertEqual(g1, g2)
        self.assertIn(g1["variant"], [v["kind"] for v in VARIANTS])
        self.assertIn(g1["palette"], PALETTES)

    def test_render_smoke(self):
        pet = {"name": "Test", "body_pattern": "sprout", "mood": "happy",
               "evolution_level": 1}
        for scale in (1, 2):
            text = render(pet, _Root(), scale=scale)
            self.assertIn("\u2580", text.plain)

    def test_render_uses_skin_override(self):
        base = {"name": "Test", "body_pattern": "seed", "mood": "curious"}
        octo = dict(base, skin="octopus")
        slime = dict(base, skin="slime")
        self.assertNotEqual(render(octo, _Root(), scale=1).plain,
                            render(slime, _Root(), scale=1).plain)
        garbage = dict(base, skin="garbage")
        render(garbage, _Root(), scale=1)  # must not raise

    def test_gaze_changes_visible_pupil_position(self):
        pet = {"name": "Test", "body_pattern": "seed", "mood": "curious",
               "skin": "octopus"}
        renders = {look: _styled(render(pet, _Root(), scale=2, look=look))
                   for look in LOOKS}
        # left, right and straight must all look different
        self.assertEqual(len(set(renders.values())), 3)

    def test_alert_focused_pupils_stay_visible(self):
        """The glint must never cover an entire eye (older bug: pupils
        vanished in alert/focused moods)."""
        pet = {"name": "Test", "body_pattern": "seed", "skin": "octopus"}
        expected_eye = EYES[genes_for(_Root(), pet)["eye"]]
        for mood in ("alert", "focused", "happy"):
            p = dict(pet, mood=mood)
            text = render(p, _Root(), scale=2, look="straight")
            styles = {str(s.style) for s in text.spans if s.style}
            self.assertTrue(any("#ffffff" in s for s in styles), mood)
            self.assertTrue(any(expected_eye in s for s in styles), mood)

    def test_idle_look_deterministic_and_valid(self):
        a1 = idle_look("proj:Test", now=1_000_000.0)
        a2 = idle_look("proj:Test", now=1_000_000.0)
        self.assertEqual(a1, a2)
        self.assertIn(a1, LOOKS)
        b = idle_look("proj:Other", now=1_000_000.0)
        self.assertIn(b, LOOKS)

    def test_idle_look_changes_over_time(self):
        looks = {idle_look("proj:Test", now=t) for t in range(0, 60, 2)}
        self.assertGreater(len(looks), 1)


if __name__ == "__main__":
    unittest.main()