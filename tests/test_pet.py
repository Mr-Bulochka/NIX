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


if __name__ == "__main__":
    unittest.main()
