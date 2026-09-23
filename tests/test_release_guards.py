"""The release tools must tell a first publication from an update.

`build_snapshot --force` deleted the public repository's .git on 2026-08-26, and
`verify_snapshot` failed every update after the first. These tests build small
git repositories in a temporary directory and check both tools against each
case.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from release import build_snapshot
from release.verify_snapshot import (
    PUBLIC_REMOTE, _walk, publication_kind, scan_git,
)


def git(root, *arguments):
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
         *arguments],
        cwd=root, check=True, capture_output=True,
    )


def repository(root, remote=None, commit=False):
    git(root, "init", "--quiet")
    (root / "README.md").write_text("snapshot\n", encoding="utf-8")
    git(root, "add", "-A")
    if commit:
        git(root, "commit", "--quiet", "-m", "first")
    if remote:
        git(root, "remote", "add", "origin", remote)
    return root


class ForceRefusesPublishedHistory(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def build_with_force(self):
        with mock.patch.object(build_snapshot, "_check_overlays"):
            return build_snapshot.build(self.root, force=True)

    def test_a_directory_with_a_remote_and_a_commit_is_refused(self):
        repository(self.root, remote=PUBLIC_REMOTE, commit=True)
        with self.assertRaises(build_snapshot.SnapshotError) as raised:
            self.build_with_force()
        self.assertIn("would delete that history", str(raised.exception))
        self.assertTrue((self.root / ".git").is_dir())

    def test_a_commit_alone_is_enough_to_refuse(self):
        repository(self.root, commit=True)
        with self.assertRaises(build_snapshot.SnapshotError):
            self.build_with_force()
        self.assertTrue((self.root / ".git").is_dir())

    def test_a_remote_alone_is_enough_to_refuse(self):
        repository(self.root, remote=PUBLIC_REMOTE)
        self.assertIsNotNone(build_snapshot.published_history(self.root))

    def test_an_earlier_scratch_build_may_be_replaced(self):
        repository(self.root)
        self.assertIsNone(build_snapshot.published_history(self.root))

    def test_a_directory_without_git_may_be_replaced(self):
        (self.root / "leftover.txt").write_text("x", encoding="utf-8")
        self.assertIsNone(build_snapshot.published_history(self.root))


class VerifierKnowsBothPublications(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_a_fresh_build_is_a_first_publication_and_passes(self):
        repository(self.root)
        self.assertEqual(publication_kind(self.root), "first")
        self.assertEqual(scan_git(self.root), [])

    def test_the_public_repository_is_an_update_and_passes(self):
        repository(self.root, remote=PUBLIC_REMOTE, commit=True)
        self.assertEqual(publication_kind(self.root), "update")
        self.assertEqual(scan_git(self.root), [])

    def test_an_update_pointing_anywhere_else_fails(self):
        repository(self.root, remote="https://example.invalid/fork.git", commit=True)
        self.assertEqual(len(scan_git(self.root)), 1)

    def test_a_commit_without_a_remote_fits_neither_and_fails(self):
        repository(self.root, commit=True)
        self.assertIsNone(publication_kind(self.root))
        self.assertEqual(len(scan_git(self.root)), 1)

    def test_a_fresh_build_with_unstaged_files_still_fails(self):
        repository(self.root)
        (self.root / "late.txt").write_text("x", encoding="utf-8")
        self.assertEqual(len(scan_git(self.root)), 1)

    def test_an_update_scans_the_files_the_rsync_added(self):
        repository(self.root, remote=PUBLIC_REMOTE, commit=True)
        (self.root / "added.txt").write_text("x", encoding="utf-8")
        (self.root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (self.root / "ignored.txt").write_text("x", encoding="utf-8")
        scanned = {path.name for path in _walk(self.root)}
        self.assertIn("added.txt", scanned)
        self.assertNotIn("ignored.txt", scanned)


if __name__ == "__main__":
    unittest.main()
