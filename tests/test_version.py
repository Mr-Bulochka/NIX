"""Guards against version drift between the release metadata sources.

The version is duplicated in three places on purpose (static literals keep
`uv` and stale egg-info metadata working), so every bump must touch all of
them. This test fails the suite when one is forgotten.
"""

import re
import unittest
from pathlib import Path

import nix

REPO_ROOT = Path(__file__).resolve().parent.parent

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _read_version_file() -> str:
    return (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _read_pyproject_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        raise AssertionError("pyproject.toml has no top-level project version")
    return match.group(1)


class TestVersionConsistency(unittest.TestCase):
    def test_version_file_is_exact(self):
        version = _read_version_file()
        self.assertRegex(version, VERSION_RE)

    def test_pyproject_version_is_exact(self):
        version = _read_pyproject_version()
        self.assertRegex(version, VERSION_RE)

    def test_sources_agree(self):
        self.assertEqual(nix.__version__, _read_version_file())
        self.assertEqual(nix.__version__, _read_pyproject_version())
