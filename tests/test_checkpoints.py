import os
import tempfile
import unittest
from pathlib import Path

from nix.app import NixApp
from nix.checkpoints import KIND_PERM, KIND_TEMP


class _StubUI:
    def show_message(self, kind, text):
        pass

    def show_block(self, *args):
        pass

    def show_tree(self, *args):
        pass

    def _refresh_pet(self):
        pass

    def show_help(self, *args):
        pass

    def show_status(self, **kwargs):
        pass

    def show_scan(self, *args):
        pass

    def show_pet(self, *args):
        pass

    def show_logs(self, *args):
        pass

    def show_code(self, *args):
        pass

    def show_history(self, *args):
        pass

    def show_error(self, *args):
        pass

    def clear_log(self):
        pass


class _RecordingUI(_StubUI):
    def __init__(self):
        self.records = []

    def show_message(self, kind, text):
        self.records.append((kind, text))


class TestCheckpoints(unittest.TestCase):
    def _make_app(self, files=None, with_pet=True):
        tmp = tempfile.TemporaryDirectory()
        old = os.getcwd()
        os.chdir(tmp.name)
        root = Path(tmp.name)
        for rel, content in (files or {}).items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        app = NixApp()
        app.ui = _RecordingUI()
        if with_pet:
            app.pet = app.pet_store.create("Tester")
        self.addCleanup(tmp.cleanup)
        self.addCleanup(lambda: os.chdir(old))
        return app

    def _cp_dir(self, app, kind):
        return app.state.nix / "checkpoints" / kind

    def test_create_saves_files_and_manifest(self):
        app = self._make_app({
            "app.py": "print('hello')\n",
            "util.py": "def f(): pass\n",
        })
        app.checkpoints.create("first")
        cp = self._cp_dir(app, KIND_TEMP) / "first"
        self.assertTrue(cp.is_dir())
        self.assertTrue((cp / "manifest.json").is_file())
        self.assertEqual((cp / "app.py").read_text(encoding="utf-8"),
                         "print('hello')\n")
        self.assertEqual((cp / "util.py").read_text(encoding="utf-8"),
                         "def f(): pass\n")
        manifest = app.checkpoints.info("first")
        self.assertEqual(manifest["name"], "first")
        self.assertEqual(manifest["kind"], KIND_TEMP)
        self.assertIn("created_at", manifest)
        self.assertIn("app.py", manifest["files"])
        self.assertIn("util.py", manifest["files"])
        self.assertGreater(manifest["size"], 0)

    def test_create_returns_none_and_rewards_pet_xp(self):
        app = self._make_app({"app.py": "x = 1\n"})
        result = app.checkpoints.create("first")
        self.assertIsNone(result)
        self.assertEqual(app.pet["xp"], 10)
        self.assertEqual(app.pet["level"], 1)
        self.assertEqual([r[0] for r in app.ui.records], ["SYSTEM"])
        self.assertIn("checkpoint created", app.ui.records[0][1])

    def test_create_without_pet_is_safe(self):
        app = self._make_app({"app.py": "x = 1\n"}, with_pet=False)
        self.assertIsNone(app.checkpoints.create("second"))
        cp = self._cp_dir(app, KIND_TEMP) / "second"
        self.assertTrue((cp / "manifest.json").is_file())

    def test_create_writes_journal_entry(self):
        app = self._make_app({"app.py": "x = 1\n"}, with_pet=False)
        app.checkpoints.create("named")
        kinds = [e["kind"] for e in app.journal.read_today()]
        self.assertIn("CHECKPOINT", kinds)
        messages = [e["message"] for e in app.journal.read_today()
                    if e["kind"] == "CHECKPOINT"]
        self.assertTrue(any("created named" in m for m in messages))

    def test_list_sorts_temporary_then_permanent(self):
        app = self._make_app({"app.py": "x = 1\n"}, with_pet=False)
        app.checkpoints.create("beta")
        app.checkpoints.create("alpha")
        app.checkpoints.promote("beta")
        rows = app.checkpoints.list()
        names = [name for name, _kind in rows]
        self.assertEqual(names, ["alpha", "beta"])

    def test_promote_moves_to_permanent(self):
        app = self._make_app({"app.py": "x = 1\n"}, with_pet=False)
        app.checkpoints.create("alpha")
        msg = app.checkpoints.promote("alpha")
        self.assertTrue(msg)
        self.assertFalse((self._cp_dir(app, KIND_TEMP) / "alpha").exists())
        self.assertTrue((self._cp_dir(app, KIND_PERM) / "alpha").is_dir())
        info = app.checkpoints.info("alpha")
        self.assertEqual(info["kind"], KIND_PERM)

    def test_delete_removes_checkpoint(self):
        app = self._make_app({"app.py": "x = 1\n"}, with_pet=False)
        app.checkpoints.create("alpha")
        self.assertTrue((self._cp_dir(app, KIND_TEMP) / "alpha").exists())
        msg = app.checkpoints.delete("alpha")
        self.assertTrue(msg)
        self.assertFalse((self._cp_dir(app, KIND_TEMP) / "alpha").exists())

    def test_restore_dry_run_reports_file_count(self):
        app = self._make_app({
            "app.py": "print('v1')\n",
            "util.py": "def f(): pass\n",
        }, with_pet=False)
        app.checkpoints.create("snap")
        Path(app.root, "app.py").write_text("print('v2')\n", encoding="utf-8")
        msg = app.checkpoints.restore("snap", dry=True)
        self.assertTrue(msg)
        self.assertIn("[dry run]", msg)
        self.assertIn("2", msg)
        self.assertEqual(Path(app.root, "app.py").read_text(encoding="utf-8"),
                         "print('v2')\n")
        self.assertFalse((self._cp_dir(app, KIND_PERM) / "snap").exists())

    def test_restore_protected_needs_force(self):
        app = self._make_app({
            "pyproject.toml": "version = '1'\n",
            "util.py": "def f(): pass\n",
        }, with_pet=False)
        app.checkpoints.create("snap")
        blocked = app.checkpoints.restore("snap")
        self.assertTrue(blocked)
        self.assertIn("protected", blocked)
        self.assertEqual(
            Path(app.root, "pyproject.toml").read_text(encoding="utf-8"),
            "version = '1'\n")
        forced = app.checkpoints.restore("snap", force=True)
        self.assertTrue(forced)
        self.assertIn("restored", forced)

    def test_restore_recovers_modified_file(self):
        app = self._make_app({
            "app.py": "print('original')\n",
            "notes.txt": "keep\n",
        }, with_pet=False)
        app.checkpoints.create("snap")
        Path(app.root, "app.py").write_text("print('changed')\n",
                                            encoding="utf-8")
        msg = app.checkpoints.restore("snap")
        self.assertTrue(msg)
        self.assertIn("restored", msg)
        self.assertEqual(
            Path(app.root, "app.py").read_text(encoding="utf-8"),
            "print('original')\n")
        self.assertEqual(Path(app.root, "notes.txt").read_text(encoding="utf-8"),
                         "keep\n")

    def test_restore_with_backup_creates_safety_backup(self):
        app = self._make_app({"app.py": "x = 1\n"}, with_pet=False)
        app.checkpoints.create("snap")
        Path(app.root, "app.py").write_text("x = 2\n", encoding="utf-8")
        msg = app.checkpoints.restore("snap")
        self.assertIn("safety backup created", msg)
        backups = list((self._cp_dir(app, KIND_PERM)).glob("snap_pre-restore_*"))
        self.assertEqual(len(backups), 1)
        backup = backups[0]
        self.assertEqual(
            (backup / "app.py").read_text(encoding="utf-8"), "x = 2\n")
        self.assertTrue((backup / "manifest.json").is_file())
        self.assertEqual(Path(app.root, "app.py").read_text(encoding="utf-8"),
                         "x = 1\n")


if __name__ == "__main__":
    unittest.main()