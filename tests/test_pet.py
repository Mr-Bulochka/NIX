import tempfile
import unittest
from pathlib import Path
from nix.pet import Pet, xp_to_next


class TestPet(unittest.TestCase):
    def test_create_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            pet = Pet(nix_dir)
            data = pet.create("Buddy")
            self.assertEqual(data["name"], "Buddy")
            self.assertEqual(data["mood"], "curious")
            self.assertEqual(data["energy"], 100)
            loaded = pet.load()
            self.assertEqual(loaded["name"], "Buddy")

    def test_load_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            pet = Pet(nix_dir)
            self.assertIsNone(pet.load())

    def test_mood_transitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            pet_store = Pet(nix_dir)
            pet = pet_store.create("X")
            pet = pet_store.update_mood(pet, "success")
            self.assertEqual(pet["mood"], "happy")
            pet = pet_store.update_mood(pet, "failure")
            self.assertEqual(pet["mood"], "determined")

    def test_xp_to_next(self):
        self.assertEqual(xp_to_next(1), 50)
        self.assertEqual(xp_to_next(2), 100)
        self.assertEqual(xp_to_next(3), 150)

    def test_add_xp_below_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            pet_store = Pet(nix_dir)
            pet = pet_store.create("X")
            pet = pet_store.add_xp(pet, 25)
            self.assertEqual(pet["level"], 1)
            self.assertEqual(pet["xp"], 25)

    def test_add_xp_exact_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            pet_store = Pet(nix_dir)
            pet = pet_store.create("X")
            pet = pet_store.add_xp(pet, 50)
            self.assertEqual(pet["level"], 2)
            self.assertEqual(pet["xp"], 0)

    def test_add_xp_carries_remainder(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            pet_store = Pet(nix_dir)
            pet = pet_store.create("X")
            pet = pet_store.add_xp(pet, 60)
            self.assertEqual(pet["level"], 2)
            self.assertEqual(pet["xp"], 10)

    def test_add_xp_multiple_levels(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            pet_store = Pet(nix_dir)
            pet = pet_store.create("X")
            pet = pet_store.add_xp(pet, 150)
            self.assertEqual(pet["level"], 3)
            self.assertEqual(pet["xp"], 0)

    def test_add_xp_accumulates_across_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            pet_store = Pet(nix_dir)
            pet = pet_store.create("X")
            pet = pet_store.add_xp(pet, 40)
            pet = pet_store.add_xp(pet, 20)
            self.assertEqual(pet["level"], 2)
            self.assertEqual(pet["xp"], 10)

    def test_evolve_stage_progression(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            store = Pet(nix_dir)
            pet = store.create("X")
            self.assertEqual(pet["body_pattern"], "seed")
            self.assertEqual(pet["evolution_level"], 0)
            self.assertEqual(pet["mutations_witnessed"], 0)
            pet = store._evolve(pet)
            self.assertEqual(pet["body_pattern"], "seed")
            pet["age"] = 4
            pet = store._evolve(pet)
            self.assertEqual(pet["body_pattern"], "seed")
            self.assertEqual(pet["evolution_level"], 0)
            pet["age"] = 5
            pet = store._evolve(pet)
            self.assertEqual(pet["body_pattern"], "sprout")
            self.assertEqual(pet["evolution_level"], 1)
            self.assertEqual(pet["mutations_witnessed"], 1)
            pet["age"] = 14
            pet = store._evolve(pet)
            self.assertEqual(pet["body_pattern"], "sprout")
            self.assertEqual(pet["evolution_level"], 1)
            self.assertEqual(pet["mutations_witnessed"], 1)
            pet["age"] = 15
            pet = store._evolve(pet)
            self.assertEqual(pet["body_pattern"], "bloom")
            self.assertEqual(pet["evolution_level"], 2)
            self.assertEqual(pet["mutations_witnessed"], 2)
            pet["age"] = 34
            pet = store._evolve(pet)
            self.assertEqual(pet["body_pattern"], "bloom")
            self.assertEqual(pet["evolution_level"], 2)
            pet["age"] = 35
            pet = store._evolve(pet)
            self.assertEqual(pet["body_pattern"], "mystic")
            self.assertEqual(pet["evolution_level"], 3)
            self.assertEqual(pet["mutations_witnessed"], 3)
            pet["age"] = 60
            pet = store._evolve(pet)
            self.assertEqual(pet["body_pattern"], "mystic")
            self.assertEqual(pet["evolution_level"], 3)

    def test_evolve_mutations_scale_with_scans(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            store = Pet(nix_dir)
            cases = [
                (5, 8, "sprout", 1, 2),
                (5, 40, "sprout", 1, 3),
                (15, 40, "bloom", 2, 5),
                (35, 8, "mystic", 3, 4),
                (35, 40, "mystic", 3, 7),
            ]
            for age, scans, pattern, ev_level, mutations in cases:
                pet = store.create("X")
                pet["age"] = age
                pet["scans"] = scans
                pet = store._evolve(pet)
                self.assertEqual(pet["body_pattern"], pattern)
                self.assertEqual(pet["evolution_level"], ev_level)
                self.assertEqual(pet["mutations_witnessed"], mutations)

    def test_evolve_unchanged_stage_does_not_recalc(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            store = Pet(nix_dir)
            pet = store.create("X")
            pet["age"] = 5
            pet = store._evolve(pet)
            self.assertEqual(pet["body_pattern"], "sprout")
            self.assertEqual(pet["mutations_witnessed"], 1)
            pet["age"] = 14
            pet["scans"] = 40
            pet = store._evolve(pet)
            self.assertEqual(pet["body_pattern"], "sprout")
            self.assertEqual(pet["evolution_level"], 1)
            self.assertEqual(pet["mutations_witnessed"], 1)

    def test_update_mood_level_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            store = Pet(nix_dir)
            for mood in ("curious", "thoughtful", "determined", "alert"):
                pet = store.create("X")
                pet["mood"] = mood
                pet = store.update_mood(pet, "level_up")
                self.assertEqual(pet["mood"], "happy")
                self.assertEqual(pet["energy"], 100)
                self.assertEqual(pet["age"], 1)

    def test_update_mood_failure_drains_energy(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            store = Pet(nix_dir)
            pet = store.create("X")
            pet = store.update_mood(pet, "failure")
            self.assertEqual(pet["mood"], "thoughtful")
            self.assertEqual(pet["energy"], 97)
            self.assertEqual(pet["age"], 1)

    def test_update_mood_failure_energy_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            store = Pet(nix_dir)
            pet = store.create("X")
            pet["mood"] = "happy"
            pet["energy"] = 2
            pet = store.update_mood(pet, "failure")
            self.assertEqual(pet["mood"], "determined")
            self.assertEqual(pet["energy"], 0)

    def test_update_mood_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            store = Pet(nix_dir)
            pet = store.create("X")
            pet["energy"] = 90
            pet = store.update_mood(pet, "success")
            self.assertEqual(pet["mood"], "happy")
            self.assertEqual(pet["energy"], 95)
            pet = store.create("X")
            pet["mood"] = "happy"
            pet["energy"] = 98
            pet = store.update_mood(pet, "success")
            self.assertEqual(pet["mood"], "happy")
            self.assertEqual(pet["energy"], 100)
            pet = store.create("X")
            pet["mood"] = "tired"
            pet = store.update_mood(pet, "success")
            self.assertEqual(pet["mood"], "content")
            pet = store.create("X")
            pet["mood"] = "anxious"
            pet = store.update_mood(pet, "success")
            self.assertEqual(pet["mood"], "relieved")
            self.assertEqual(pet["age"], 1)

    def test_update_mood_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            nix_dir = Path(tmp) / ".nix"
            nix_dir.mkdir()
            store = Pet(nix_dir)
            pet = store.create("X")
            pet = store.update_mood(pet, "scan")
            self.assertEqual(pet["mood"], "focused")
            self.assertEqual(pet["scans"], 1)
            self.assertEqual(pet["age"], 1)
            self.assertEqual(pet["energy"], 100)


if __name__ == "__main__":
    unittest.main()
