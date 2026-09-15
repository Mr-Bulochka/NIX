import tempfile
import unittest
from pathlib import Path
from nix.pet import Pet


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


if __name__ == "__main__":
    unittest.main()
