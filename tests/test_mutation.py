import os
import tempfile
import unittest
from pathlib import Path

from nix.app import NixApp
from nix.checkpoints import KIND_TEMP
from nix.mutation import LAW_BUDGET, LAW_PROTECTED


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


class TestMutation(unittest.TestCase):
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


class LawTests(TestMutation):
    def test_protected_basename(self):
        app = self._make_app()
        self.assertEqual(
            app.mutations.check_laws("pyproject.toml"), LAW_PROTECTED)

    def test_protected_subpath(self):
        app = self._make_app()
        self.assertEqual(
            app.mutations.check_laws("sub/pyproject.toml"), LAW_PROTECTED)

    def test_protected_windows_path(self):
        app = self._make_app()
        self.assertEqual(
            app.mutations.check_laws(Path(r"win\dir\pyproject.toml")),
            LAW_PROTECTED)

    def test_unprotected_path_is_free(self):
        app = self._make_app()
        self.assertIsNone(app.mutations.check_laws("src/app.py"))

    def test_zero_budget_blocks(self):
        app = self._make_app()
        app.config.mutation_budget = 0
        self.assertEqual(
            app.mutations.check_laws("src/app.py"), LAW_BUDGET)

    def test_protected_wins_over_budget(self):
        app = self._make_app()
        app.config.mutation_budget = 0
        self.assertEqual(
            app.mutations.check_laws("pyproject.toml"), LAW_PROTECTED)

    def test_budget_exhausted_after_records(self):
        app = self._make_app()
        app.config.mutation_budget = 1
        app.config.checkpoint_on_mutate = False
        app.mutations.record("mut", "src/app.py", "backup")
        self.assertEqual(
            app.mutations.check_laws("src/app.py"), LAW_BUDGET)


class BudgetTests(TestMutation):
    def test_records_increment_count(self):
        app = self._make_app(with_pet=False)
        app.config.checkpoint_on_mutate = False
        app.mutations.record("mut", "src/app.py", "backup")
        app.mutations.record("mut", "src/other.py", "backup2")
        self.assertEqual(app.mutations.count, 2)
        self.assertEqual(app.mutations.remaining(), 8)

    def test_record_entry_fields(self):
        app = self._make_app(with_pet=False)
        app.config.checkpoint_on_mutate = False
        app.mutations.record("mut", "src/app.py", "backup")
        entry = app.mutations.records[-1]
        self.assertEqual(entry["kind"], "mut")
        self.assertEqual(entry["target"], "src/app.py")
        self.assertEqual(entry["backup"], "backup")
        self.assertEqual(entry["status"], "ok")
        self.assertIn("ts", entry)

    def test_reset_budget(self):
        app = self._make_app(with_pet=False)
        app.config.checkpoint_on_mutate = False
        app.mutations.record("mut", "src/app.py", "backup")
        self.assertEqual(app.mutations.count, 1)
        app.mutations.reset_budget()
        self.assertEqual(app.mutations.count, 0)


class RecordTests(TestMutation):
    def test_record_rewards_pet_xp(self):
        app = self._make_app({"src/app.py": "x = 1\n"})
        app.mutations.record("mut", "src/app.py", "backup")
        self.assertEqual(app.pet["xp"], 25)
        self.assertEqual(app.pet["level"], 1)
        self.assertEqual(app.pet["mutations_witnessed"], 1)

    def test_record_resets_budget(self):
        app = self._make_app({"src/app.py": "x = 1\n"})
        app.mutations.record("mut", "src/app.py", "backup")
        self.assertEqual(app.mutations.count, 0)

    def test_record_writes_journal_entry(self):
        app = self._make_app({"src/app.py": "x = 1\n"}, with_pet=False)
        app.config.checkpoint_on_mutate = False
        app.mutations.record("mut", "src/app.py", "backup")
        messages = [e["message"] for e in app.journal.read_today()
                    if e["kind"] == "MUTATION"]
        self.assertTrue(any("mut recorded for src/app.py" in m
                            for m in messages))

    def test_record_creates_auto_checkpoint(self):
        app = self._make_app({"src/app.py": "x = 1\n"}, with_pet=False)
        app.mutations.record("mut", "src/app.py", "backup")
        cp = self._cp_dir(app, KIND_TEMP) / "auto-mut"
        self.assertTrue(cp.is_dir())
        self.assertTrue((cp / "manifest.json").is_file())

    def test_record_without_pet_is_safe(self):
        app = self._make_app({"src/app.py": "x = 1\n"}, with_pet=False)
        app.config.checkpoint_on_mutate = False
        app.mutations.record("mut", "src/app.py", "backup")
        self.assertEqual(app.mutations.count, 1)
        self.assertIsNone(app.pet)


class AutoCommitTests(TestMutation):
    def _git_init(self, app):
        from nix.git import Git

        git = Git(app.root)
        if git.is_repo():
            return git
        self.run_git = git
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=str(app.root), check=True)
        subprocess.run(["git", "config", "user.email", "t@t.t"],
                       cwd=str(app.root), check=True)
        subprocess.run(["git", "config", "user.name", "T"],
                       cwd=str(app.root), check=True)
        return git

    def _committed_paths(self, git):
        result = git._run("show", "--name-only", "--format=", "HEAD")
        return {line.strip() for line in result.lines if line.strip()}

    def test_disabled_by_default_no_commit(self):
        app = self._make_app({"src/app.py": "x = 1\n"}, with_pet=False)
        app.config.checkpoint_on_mutate = False
        git = self._git_init(app)
        app.mutations.record("mut", "src/app.py", "backup")
        self.assertEqual(git.log(1), [])

    def test_commits_only_mutated_file(self):
        app = self._make_app({
            "src/app.py": "x = 1\n",
            "src/other.py": "y = 2\n",
        }, with_pet=False)
        app.config.checkpoint_on_mutate = False
        app.config.git_auto_commit = True
        git = self._git_init(app)
        app.mutations.record("mut", "src/app.py", "backup")
        (app.root / "src" / "other.py").write_text("y = 3\n",
                                                   encoding="utf-8")
        git.add_file(app.root / "src" / "app.py")
        git.commit("seed")
        app.mutations.record("mut", "src/app.py", "backup2")
        self.assertEqual(self._committed_paths(git), {"src/app.py"})

    def test_commit_message_includes_kind_and_path(self):
        app = self._make_app({"src/app.py": "x = 1\n"}, with_pet=False)
        app.config.checkpoint_on_mutate = False
        app.config.git_auto_commit = True
        git = self._git_init(app)
        app.mutations.record("mut", "src/app.py", "backup")
        self.assertTrue(git.log(1)[0].endswith("nix: mut src/app.py"))

    def test_non_git_root_is_journaled_not_raised(self):
        app = self._make_app({"src/app.py": "x = 1\n"}, with_pet=False)
        app.config.checkpoint_on_mutate = False
        app.config.git_auto_commit = True
        app.mutations.record("mut", "src/app.py", "backup")
        messages = [e["message"] for e in app.journal.read_today()
                    if e["kind"] == "GIT"]
        self.assertTrue(any("not a git repo" in m for m in messages))

    def test_nix_state_not_committed(self):
        app = self._make_app({"src/app.py": "x = 1\n"}, with_pet=False)
        app.config.checkpoint_on_mutate = False
        app.config.git_auto_commit = True
        git = self._git_init(app)
        app.mutations.record("mut", "src/app.py", "backup")
        self.assertEqual(self._committed_paths(git), {"src/app.py"})
        self.assertEqual(git._run("diff", "--cached", "--name-only").lines, [])


if __name__ == "__main__":
    unittest.main()