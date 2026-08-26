"""Skip conditions for tests whose inputs cannot be published.

Item 22's closure tests verify committed records against two things that do not
travel: the private research corpora under ``.research_data``, about 24 GB of
licensed audio, model snapshots and derived evidence, and the working
repository's own git history.

Neither absence is a defect and neither may be turned into a pass. Without these
inputs the affected tests report themselves skipped, with the reason, in the same
way the pipeline declares a measurement unavailable rather than returning a zero.
In the working repository the inputs are present and nothing here skips anything.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DATA_ROOT = REPOSITORY_ROOT / ".research_data"

HAVE_RESEARCH_DATA = (
    RESEARCH_DATA_ROOT.is_dir()
    and (RESEARCH_DATA_ROOT / "speech_sound_patterns" / "corpora").is_dir()
)


def _have_history():
    result = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "rev-list", "--count", "HEAD"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return False
    return int(result.stdout.strip() or 0) > 1


HAVE_REPOSITORY_HISTORY = _have_history()

needs_research_data = unittest.skipUnless(
    HAVE_RESEARCH_DATA,
    "needs the private research corpora under .research_data, which are "
    "licensed for local use and are not redistributable, so they are absent "
    "from the public snapshot. This is not checked here.",
)

needs_repository_history = unittest.skipUnless(
    HAVE_REPOSITORY_HISTORY,
    "needs the working repository's own git history, which the public snapshot "
    "deliberately does not carry because that history contains personal "
    "recordings. This is not checked here.",
)
