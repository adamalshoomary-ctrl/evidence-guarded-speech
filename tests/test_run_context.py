import json
import argparse
import tempfile
import unittest
from pathlib import Path

from pipeline.run_context import (
    RunContext,
    atomic_write_json,
    create_manifest,
    resolve_audio,
    update_manifest,
)


class RunContextTests(unittest.TestCase):
    def test_explicit_audio_wins_over_default_directory_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio_dir = root / "audio"
            audio_dir.mkdir()
            (audio_dir / "a.wav").write_bytes(b"default")
            explicit = root / "chosen.m4a"
            explicit.write_bytes(b"chosen")

            self.assertEqual(resolve_audio(explicit, audio_dir), explicit.resolve())

    def test_default_audio_requires_selection_when_multiple_files_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_dir = Path(temp_dir) / "audio"
            audio_dir.mkdir()
            (audio_dir / "first.wav").write_bytes(b"first")
            (audio_dir / "second.m4a").write_bytes(b"second")

            with self.assertRaisesRegex(SystemExit, "Select one with --audio"):
                resolve_audio(None, audio_dir)

    def test_missing_audio_directory_explains_itself_instead_of_crashing(self):
        """A fresh copy of this repository has no audio/ and publishes none.

        Every documented command that omits --audio used to die on a raw
        FileNotFoundError from iterdir, before any of this project's error
        handling ran. Found 2026-08-28 by running the published documentation.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            absent = Path(temp_dir) / "audio"

            with self.assertRaisesRegex(SystemExit, "no audio/ directory"):
                resolve_audio(None, absent)

    def test_missing_audio_directory_names_a_file_the_reader_can_use(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            absent = Path(temp_dir) / "audio"

            with self.assertRaisesRegex(SystemExit, "regression/fixtures/solo.wav"):
                resolve_audio(None, absent)

    def test_empty_audio_directory_names_a_file_the_reader_can_use(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_dir = Path(temp_dir) / "audio"
            audio_dir.mkdir()

            with self.assertRaisesRegex(SystemExit, "regression/fixtures/solo.wav"):
                resolve_audio(None, audio_dir)

    def test_manifest_rejects_a_planted_file_until_current_run_declares_it(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "artifacts"
            output_dir.mkdir()
            planted = output_dir / "transcript.json"
            planted.write_text('{"stale": true}', encoding="utf-8")
            manifest_path = create_manifest(
                output_dir, "current_run", root / "input.wav", ["transcript.json"]
            )
            context = RunContext(root, output_dir, "current_run", root / "input.wav")

            with self.assertRaisesRegex(
                SystemExit, "transcript.json was not produced by the current run"
            ):
                context.output_path("transcript.json", required=True)

            atomic_write_json(planted, {"stale": False})
            update_manifest(
                manifest_path, completed_outputs=["transcript.json"]
            )
            self.assertEqual(
                json.loads(context.output_path("transcript.json", required=True).read_text()),
                {"stale": False},
            )

    def test_atomic_write_replaces_the_file_and_leaves_no_temporary_sibling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            target = output_dir / "result.json"
            target.write_text('{"old": true}', encoding="utf-8")
            old_inode = target.stat().st_ino

            atomic_write_json(target, {"old": False})

            self.assertNotEqual(target.stat().st_ino, old_inode)
            self.assertEqual(json.loads(target.read_text()), {"old": False})
            self.assertEqual(
                [path for path in output_dir.iterdir() if path.name.startswith(".")],
                [],
            )

    def test_context_from_args_resolves_optional_session_context(self):
        from pipeline.run_context import context_from_args

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "audio").mkdir()
            session_context = root / "context.json"
            session_context.write_text("{}", encoding="utf-8")
            args = argparse.Namespace(
                audio=None,
                output_dir=root / "artifacts",
                run_id="run_001",
                session_context=session_context,
            )

            context = context_from_args(args, root)

            self.assertEqual(
                context.session_context_path, session_context.resolve()
            )


if __name__ == "__main__":
    unittest.main()
