"""Refuse a public snapshot that carries anything it should not.

This runs against the built snapshot before the owner's first commit, and it is
meant to fail rather than to reassure. Everything it looks for is declared in
``release/snapshot-contract-v1.0.0.json`` plus the gitignored
``.private-identifiers`` list, which stays on this machine so the check does not
have to publish the strings it is defending.

It refuses to report success if it cannot read that list. A privacy check that
degrades to "nothing found" when its inputs are missing is worse than no check,
because it produces a clean report either way.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from release.build_snapshot import checksum_pinned, selected_files

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = REPOSITORY_ROOT / "release" / "snapshot-contract-v1.0.0.json"
IDENTIFIERS = REPOSITORY_ROOT / ".private-identifiers"
DEFAULT_DESTINATION = REPOSITORY_ROOT.parent / "evidence-guarded-speech"


class VerificationError(RuntimeError):
    """Raised when the verifier cannot run, which is never a pass."""


def private_tokens():
    if not IDENTIFIERS.is_file():
        raise VerificationError(
            f"{IDENTIFIERS} is missing. The verifier cannot confirm that private "
            "identifiers are absent without the list of them, and reporting a "
            "pass in that state would be worse than reporting nothing."
        )
    tokens = []
    for line in IDENTIFIERS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            tokens.append(line.casefold())
    if not tokens:
        raise VerificationError(f"{IDENTIFIERS} lists no identifiers")
    return tokens


def _walk(root):
    """Every file git would actually publish, which is the staged set.

    Walking the filesystem instead was wrong in a way worth recording. Running
    the test suite inside a built snapshot leaves ``__pycache__`` behind, and a
    compiled Python file embeds the absolute path of its source, so the walk
    reported 125 findings for a home directory that git was never going to
    publish because .gitignore excludes those files. Scanning the staged set
    checks the thing that leaves the machine, and it does not depend on whether
    anybody happened to run the tests first.
    """
    staged = subprocess.run(
        ["git", "ls-files", "--cached", "-z"],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout.split("\0")
    for name in sorted(filter(None, staged)):
        path = root / name
        if path.is_file():
            yield path


def _flatten(text):
    """Collapse every run of whitespace to one space.

    A line wrap inside a private string used to defeat this check completely,
    because it compares literal substrings. A place name inside a quoted command
    in a committed document was wrapped across two lines by an ordinary text
    reflow, and this check reported private content clean for six consecutive
    releases while the name sat in the public repository. Found 2026-08-28. The
    substitution engine in build_snapshot is literal in the same way and did not
    replace it either, which is why the finding tells a reader to rewrap the
    source rather than expecting the builder to cope: rewriting somebody's prose
    layout so a replacement fits is worse than refusing to publish.

    The string that escaped is deliberately not quoted here. It is on the
    deny list this module reads, and a defect note that repeats the private
    value republishes it, which is the same mistake in a new place.
    """
    return " ".join(text.split())


def scan_content(root, contract, tokens):
    """Refuse forbidden content, allowing only what the contract declares.

    A checksum pinned record cannot be edited without breaking every record that
    pins it, so the contract may declare specific tokens acceptable inside one.
    That allowance is narrow on purpose: it applies only to a file the builder
    identified as pinned, only to a token the contract names, and never to
    anything credential shaped.
    """
    forbidden = contract["forbidden_after_build"]
    literals = tokens + [t.casefold() for t in forbidden["additional_tokens"]]
    patterns = [re.compile(p) for p in forbidden["additional_patterns"]]
    exemptions = {
        entry["token"].casefold()
        for entry in forbidden.get("pinned_file_exemptions", {}).get(
            "permitted_tokens", []
        )
    }
    kept, _, _ = selected_files(contract)
    pinned = checksum_pinned(kept)

    findings, allowed = [], []
    for path in _walk(root):
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="ignore")
        lowered = text.casefold()
        flattened = _flatten(lowered)
        relative = path.relative_to(root).as_posix()
        for token in literals:
            wrapped = token not in lowered
            if wrapped and _flatten(token) not in flattened:
                continue
            if relative in pinned and token in exemptions:
                allowed.append(
                    f"{relative} keeps {token!r}, declared acceptable because the "
                    "record is checksum pinned"
                )
            elif wrapped:
                findings.append(
                    f"{relative} contains the forbidden string {token!r} with a "
                    "line break inside it. Rewrap the line in the private source "
                    "so the string is contiguous, then rebuild: a substitution "
                    "rule cannot match across a line break either, so the "
                    "builder did not replace it."
                )
            else:
                findings.append(f"{relative} contains the forbidden string {token!r}")
        for pattern in patterns:
            if pattern.search(text):
                findings.append(
                    f"{relative} matches the credential shaped pattern "
                    f"{pattern.pattern!r}"
                )
    return findings, allowed


def scan_structure(root):
    findings = []
    if (root / "audio").exists():
        findings.append("audio/ exists in the snapshot")
    if (root / "output").exists():
        findings.append("output/ exists in the snapshot")
    for name in ("history.json", "progress.md", ".env", ".private-identifiers"):
        if (root / name).exists():
            findings.append(f"{name} exists in the snapshot")
    for name in ("LICENSE", "NOTICE.md", "CITATION.cff", "README-SNAPSHOT.md"):
        if not (root / name).is_file():
            findings.append(f"{name} is missing from the snapshot")
    licence = root / "LICENSE"
    if licence.is_file():
        head = licence.read_text(encoding="utf-8")[:200]
        if "GNU GENERAL PUBLIC LICENSE" not in head or "Version 3" not in head:
            findings.append("LICENSE is not the GNU General Public License version 3")
    return findings


def scan_fixtures(root):
    findings = []
    for name in ("conversation", "solo"):
        truth = root / "regression" / "truth" / f"fixture_{name}.json"
        if not truth.is_file():
            findings.append(f"fixture_{name} truth record is missing")
            continue
        record = json.loads(truth.read_text(encoding="utf-8"))
        audio = root / record["audio"]["path"]
        if not audio.is_file():
            findings.append(f"{record['audio']['path']} is missing")
            continue
        digest = hashlib.sha256(audio.read_bytes()).hexdigest()
        if digest != record["audio"]["sha256"]:
            findings.append(f"{record['audio']['path']} does not match its truth hash")
    return findings


def scan_evidence_bundle(root):
    findings = []
    bundle = root / "speech_sound_patterns" / "variety-probe-evidence"
    manifest_path = bundle / "bundle-manifest.json"
    if not manifest_path.is_file():
        return ["the probe evidence bundle manifest is missing"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = sorted(p for p in bundle.glob("*/*.json"))
    if len(paths) != manifest["records"]:
        findings.append(
            f"the bundle holds {len(paths)} records against {manifest['records']} declared"
        )
    running = hashlib.sha256()
    for path in paths:
        running.update(path.relative_to(bundle).as_posix().encode("utf-8"))
        running.update(path.read_bytes())
    if running.hexdigest() != manifest["composite_sha256"]:
        findings.append("the bundle does not match its declared composite hash")
    # A Common Voice client_id is 128 hex characters. Nothing derived from one
    # should survive into a published record.
    identifier = re.compile(r"\b[0-9a-f]{64,}\b")
    for path in paths[:] :
        if identifier.search(path.read_text(encoding="utf-8")):
            findings.append(f"{path.name} carries a contributor shaped identifier")
            break
    return findings


def scan_git(root):
    findings = []
    if not (root / ".git").is_dir():
        return ["the snapshot is not a git repository"]
    remotes = subprocess.run(["git", "remote"], cwd=root,
                             capture_output=True, text=True).stdout.strip()
    if remotes:
        findings.append(f"the snapshot already has a remote: {remotes}")
    committed = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=root,
                               capture_output=True, text=True)
    if committed.returncode == 0:
        findings.append(
            "the snapshot already has a commit. The builder must never commit; "
            "the first commit is the owner's."
        )
    staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=root,
                            capture_output=True, text=True).stdout.split()
    if not staged:
        findings.append("nothing is staged in the snapshot")
    unstaged = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"], cwd=root,
        capture_output=True, text=True).stdout.split()
    if unstaged:
        findings.append(
            f"{len(unstaged)} files are present but not staged, so the verifier "
            f"has not checked them, starting with {unstaged[0]}"
        )
    return findings


def verify(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise VerificationError(f"{root} does not exist")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    tokens = private_tokens()
    content, allowed = scan_content(root, contract, tokens)
    sections = {
        "private content": content,
        "structure": scan_structure(root),
        "fixtures": scan_fixtures(root),
        "evidence bundle": scan_evidence_bundle(root),
        "git": scan_git(root),
    }
    return sections, allowed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    arguments = parser.parse_args()
    sections, allowed = verify(arguments.destination)
    for note in allowed:
        print(f"declared exemption: {note}")
    total = sum(len(findings) for findings in sections.values())
    for name, findings in sections.items():
        status = "clean" if not findings else f"{len(findings)} FINDINGS"
        print(f"{name}: {status}")
        for finding in findings:
            print(f"    {finding}")
    if total:
        raise SystemExit(f"\nSNAPSHOT REFUSED: {total} findings")
    print("\nSnapshot verified. It is staged and uncommitted, ready for review.")


if __name__ == "__main__":
    main()
