import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from nix.commands import get_command


def _fire(app_rec, name, args):
    get_command(name).handler(app_rec, args)


class _Rec:
    def __init__(self):
        self.seen = []
        self.ui = _UI(self)
        self.t = _T().t
        self.state = _State()
        self.journal = _Journal()
        self.pet = None
        self.pet_store = _PetStore()
        self.brain = MagicMock()
        self.root = Path(tempfile.mkdtemp())
        self.brain.ensure.return_value = (self._index(), {})
        self.brain.load.return_value = (self._index(), {})

    def _index(self):
        return {"symbols": [
            {"file": "core.py", "kind": "function", "name": "parse_item"},
            {"file": "main.py", "kind": "function", "name": "main"},
        ]}


class _UI:
    def __init__(self, rec):
        self.rec = rec

    def show_message(self, kind, text):
        self.rec.seen.append(("message", kind, text))

    def show_block(self, title, rows):
        self.rec.seen.append(("block", title, rows))

    def show_code(self, title, lines):
        self.rec.seen.append(("code", title, list(lines)))

    def show_tree(self, *a):
        pass

    def _refresh_pet(self):
        pass

    def show_help(self, *a):
        pass

    def show_status(self, **kw):
        pass

    def show_scan(self, *a):
        pass

    def show_pet(self, *a):
        pass

    def show_logs(self, *a):
        pass

    def show_history(self, *a):
        pass

    def show_error(self, *a):
        pass

    def clear_log(self):
        pass


class _State:
    def __init__(self):
        tmp = Path(tempfile.mkdtemp())
        self.nix = tmp / ".nix"


class _T:
    def t(self, key, **kw):
        from nix.i18n import t
        return t("en", key, **kw)


class _Journal:
    def write(self, *a):
        pass


class _PetStore:
    def update_mood(self, *a):
        pass

    def save(self, *a):
        pass


class TestGenWrite(unittest.TestCase):
    def setUp(self):
        self.p = _Rec()
        self.p.root = Path(tempfile.mkdtemp())

    def test_gen_no_into_previews(self):
        _fire(self.p, "gen", ["function", "parse_item", "--lang", "python"])
        self.assertTrue(any(kind == "code" for kind, *_ in self.p.seen))
        self.assertFalse(any(kind == "message"
                             for kind, *_ in self.p.seen))

    def test_gen_writes_into_file_with_apply(self):
        target = self.p.root / "core.py"
        target.write_text("def helper():\n    pass\n", encoding="utf-8")
        _fire(self.p, "gen", [
            "function", "feature",
            "--into", "core.py", "--at", "1",
            "--apply", "--doc", "a feature",
        ])
        text = target.read_text(encoding="utf-8")
        self.assertIn("def feature()", text)
        self.assertTrue(list((self.p.state.nix / "brain" / "backups").glob("*-gen-*")))

    def test_gen_end_insert_before_main_guard(self):
        target = self.p.root / "core.py"
        target.write_text('def main():\n    pass\n\n\nif __name__ == "__main__":\n    main()\n',
                          encoding="utf-8")
        _fire(self.p, "gen", [
            "function", "bootstrap", "--into", "core.py",
            "--apply", "--doc", "entry",
        ])
        text = target.read_text(encoding="utf-8")
        guard = text.index('if __name__ == "__main__":')
        fn = text.index("def bootstrap()")
        self.assertLess(fn, guard)  # must land before the main guard
        compile(text, "core.py", "exec")  # and stay valid Python

    def test_gen_multi_word_params(self):
        target = self.p.root / "core.py"
        target.write_text("x = 1\n", encoding="utf-8")
        _fire(self.p, "gen", [
            "function", "divmod2", "--into", "core.py", "--apply",
            "--params", "a", "b", "--ret", "tuple", "--doc", "returns pair",
        ])
        text = target.read_text(encoding="utf-8")
        self.assertIn("def divmod2(a, b) -> tuple:", text)
        self.assertIn('"""returns pair"""', text)
        compile(text, "core.py", "exec")


class TestRename(unittest.TestCase):
    def setUp(self):
        self.p = _Rec()
        self.p.root = Path(tempfile.mkdtemp())
        (self.p.root / "core.py").write_text(
            "def parse_item(x):\n    return parse_item(x)\n", encoding="utf-8")

    def test_rename_dry_run_no_write(self):
        before = (self.p.root / "core.py").read_text(encoding="utf-8")
        _fire(self.p, "rename", ["parse_item", "parse_row", "--file", "core.py"])
        self.assertEqual(before, (self.p.root / "core.py").read_text(encoding="utf-8"))
        self.assertIn("block", [kind for kind, *_ in self.p.seen])

    def test_rename_apply_write(self):
        _fire(self.p, "rename", ["parse_item", "parse_row", "--file", "core.py",
                                 "--apply"])
        text = (self.p.root / "core.py").read_text(encoding="utf-8")
        self.assertNotIn("parse_item", text)
        self.assertIn("parse_row", text)
        self.assertTrue(list((self.p.state.nix / "brain" / "backups").glob("*-rename-*")))


class TestGit(unittest.TestCase):
    def setUp(self):
        self.p = _Rec()
        self.p.root = Path(tempfile.mkdtemp())

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_git_status_and_commit(self):
        subprocess.run(["git", "init", "-q"], cwd=str(self.p.root), check=True)
        subprocess.run(["git", "config", "user.email", "t@t"],
                       cwd=str(self.p.root), check=True)
        subprocess.run(["git", "config", "user.name", "t"],
                       cwd=str(self.p.root), check=True)
        (self.p.root / "a.py").write_text("x = 1\n", encoding="utf-8")
        _fire(self.p, "git", ["status"])
        _fire(self.p, "git", ["commit", "--apply"])
        self.assertTrue(any(kind == "message" and "committ" in text
                            for kind, _, text in self.p.seen))

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_git_not_repo_message(self):
        _fire(self.p, "git", ["status"])
        self.assertTrue(any(kind == "message" and "not a git" in text
                            for kind, _, text in self.p.seen))


class TestRemote(unittest.TestCase):
    def setUp(self):
        self.p = _Rec()
        self.p.root = Path(tempfile.mkdtemp())

    def test_platform_detection(self):
        from nix.git import platform_for_url
        self.assertEqual(platform_for_url("git@github.com:a/x.git"), "github")
        self.assertEqual(platform_for_url("https://gitlab.com/a/x.git"), "gitlab")
        self.assertEqual(platform_for_url("git@gitlab.example.org:a/x.git"),
                         "gitlab")
        self.assertEqual(platform_for_url("https://example.com/a/x.git"), "other")
        self.assertEqual(platform_for_url(""), "other")

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_remote_info_shows_platform_and_none_when_no_remote(self):
        subprocess.run(["git", "init", "-q"], cwd=str(self.p.root), check=True)
        _fire(self.p, "remote", ["info"])
        self.assertTrue(any(kind == "message" and "no remotes" in text
                            for kind, _, text in self.p.seen))
        subprocess.run(["git", "remote", "add", "origin",
                        "git@github.com:acme/x.git"],
                       cwd=str(self.p.root), check=True)
        _fire(self.p, "remote", ["info"])
        self.assertIn("block", [kind for kind, *_ in self.p.seen])

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_remote_push_dry_run_no_network(self):
        subprocess.run(["git", "init", "-q"], cwd=str(self.p.root), check=True)
        subprocess.run(["git", "remote", "add", "origin",
                        "https://github.com/acme/x.git"],
                       cwd=str(self.p.root), check=True)
        _fire(self.p, "remote", ["push"])
        self.assertTrue(any(kind == "message" and "preview" in text
                            for kind, _, text in self.p.seen))


class TestDiffSummary(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.p = _Rec()
        self.p.root = Path(tempfile.mkdtemp())

    def test_regex_accepts_real_git_stat_lines(self):
        from nix.git import Git
        git = Git(self.p.root)
        git.diff_stat = lambda cached=True: [
            " core.py | 3 ++-",
            " new.py   | 5 +++++",
            " old.py   | 2 --",
            " bin.png  | Bin 0 -> 12 bytes",
        ]
        summary = git.diff_summary()
        by_file = {s["file"]: s for s in summary}
        self.assertEqual(by_file["core.py"]["insertions"], 2)
        self.assertEqual(by_file["core.py"]["deletions"], 1)
        self.assertEqual(by_file["new.py"]["insertions"], 5)
        self.assertEqual(by_file["new.py"]["deletions"], 0)
        self.assertEqual(by_file["old.py"]["insertions"], 0)
        self.assertEqual(by_file["old.py"]["deletions"], 2)
        self.assertTrue(by_file["bin.png"].get("binary"))


if __name__ == "__main__":
    unittest.main()