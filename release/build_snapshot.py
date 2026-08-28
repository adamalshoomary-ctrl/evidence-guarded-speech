"""Build the sanitized public snapshot from this private working repository.

The snapshot is a separate repository with its own history. **This repository is
never made public**, because its working tree and its git history both carry the
owner's recordings and transcripts derived from them, and deleting a file from
the tree does not remove it from history. A history rewrite was rejected: it
changes every commit hash anyway, so it preserves nothing worth keeping, and it
cannot prove completeness.

Everything this module does is declared in
``release/snapshot-contract-v1.0.0.json`` rather than written into the code, so
what leaves this machine can be reviewed before it leaves. Files are read from
the git index rather than the working tree, so an untracked file cannot be
published by accident.

It stages the result and stops. **It never commits**, because the owner makes
every commit himself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = REPOSITORY_ROOT / "release" / "snapshot-contract-v1.0.0.json"
DEFAULT_DESTINATION = REPOSITORY_ROOT.parent / "evidence-guarded-speech"

TEXT_SUFFIXES = {
    ".md", ".py", ".json", ".txt", ".cff", ".yml", ".yaml", ".toml", ".cfg",
    ".sh", ".ini", ".csv", ".tsv",
}


class SnapshotError(RuntimeError):
    """Raised when the snapshot cannot be built as the contract describes."""


def load_contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _git(*arguments):
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True,
    )
    return [name for name in result.stdout.split("\0") if name]


def candidate_files():
    """Tracked files, plus new work git would let you commit.

    Reading the index alone would silently omit everything added since the last
    commit, which on the run that built this was the licence, the notices, the
    fixtures, the evidence bundle and this module. Reading the working tree
    blindly would publish anything lying about. The middle is what ``git status``
    would offer: tracked files plus untracked files that .gitignore does not
    exclude, which is what keeps the credentials file and the research data out.
    The untracked set is returned separately so the build can print it and a
    person can look at it before anything is published.
    """
    tracked = _git("ls-files", "-z")
    untracked = _git("ls-files", "--others", "--exclude-standard", "-z")
    return tracked, untracked


def selected_files(contract):
    selection = contract["source_selection"]
    prefixes = tuple(selection["excluded_prefixes"])
    excluded = set(selection["excluded_paths"])
    tracked, untracked = candidate_files()
    kept, dropped = [], []
    for name in sorted(set(tracked) | set(untracked)):
        if name.startswith(prefixes) or name in excluded:
            dropped.append(name)
        else:
            kept.append(name)
    missing = [name for name in kept if not (REPOSITORY_ROOT / name).exists()]
    if missing:
        raise SnapshotError(
            "these files are in the git index but not on disk, so the build "
            "cannot know whether they were meant to be published or deleted: "
            + ", ".join(missing)
            + ". Stage the deletion and build again. Before this check the "
            "build died on a FileNotFoundError halfway through writing a "
            "snapshot, which left a half built directory behind."
        )
    return kept, dropped, sorted(set(untracked) - set(dropped))


def checksum_pinned(names):
    """Tracked files whose sha256 another tracked file records.

    These are frozen evidence records that verify each other. Substituting a
    string inside one changes its hash and breaks every record that pins it, and
    a published repository whose own integrity checks fail is worse than one
    that carries a cloud resource name. So they are copied byte for byte, and
    any substitution that would have fired inside one is reported rather than
    applied, for a person to decide about.

    This is computed rather than listed, because a hand written exemption list
    goes stale the first time a new record is frozen.
    """
    digests = {}
    for name in names:
        path = REPOSITORY_ROOT / name
        if path.is_file():
            digests.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), name)
    pinned = set()
    for name in names:
        path = REPOSITORY_ROOT / name
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for digest in re.findall(r"\b[0-9a-f]{64}\b", text):
            target = digests.get(digest)
            if target and target != name:
                pinned.add(target)
    return pinned


def _apply(text, contract, relative_path):
    applied = []
    for rule in contract["substitutions"]:
        restriction = rule.get("files")
        if restriction and relative_path not in restriction:
            continue
        if "literal" in rule:
            count = text.count(rule["literal"])
            if count:
                text = text.replace(rule["literal"], rule["replacement"])
        else:
            text, count = re.subn(rule["pattern"], rule["replacement"], text)
        if count:
            applied.append((rule["id"], count))
    return text, applied


def _check_overlays(contract):
    """Refuse the build when a private source has moved under its overlay.

    An overlay is a document written for the public repository in place of one
    or more private ones. It is not generated from them, so nothing but this
    check keeps the two in step. The failure it exists to prevent has already
    happened once: on 2026-08-27 the published status document still said the
    honest account was unpublished, in a repository that contained it.

    Each overlay declares every private file it was written against, with that
    file's hash. Changing any of them fails the next build until somebody
    revisits the overlay, which is the intended cost.
    """
    for overlay in contract["overlays"]:
        for source in overlay["sources"]:
            path = REPOSITORY_ROOT / source["path"]
            recorded = source["sha256"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if recorded != actual:
                raise SnapshotError(
                    f"{source['path']} has changed since the overlay at "
                    f"{overlay['overlay']} was written. The overlay was "
                    f"authored against {recorded} and the file is now {actual}. "
                    "Revisit the overlay, then record the new hash in the "
                    "contract. An overlay that silently falls behind its "
                    "sources is how a public document starts lying about a "
                    "private one."
                )


def build(destination, force=False):
    contract = load_contract()
    _check_overlays(contract)

    destination = Path(destination).resolve()
    if destination == REPOSITORY_ROOT:
        raise SnapshotError("the snapshot cannot be built over the source repository")
    if destination.exists() and any(destination.iterdir()):
        if not force:
            raise SnapshotError(
                f"{destination} is not empty. Pass --force to replace it."
            )
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    kept, dropped, untracked = selected_files(contract)
    pinned = checksum_pinned(kept)
    substitution_counts = {}
    withheld_substitutions = {}
    binaries = 0
    for name in kept:
        source = REPOSITORY_ROOT / name
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() in TEXT_SUFFIXES:
            text = source.read_text(encoding="utf-8")
            replaced, applied = _apply(text, contract, name)
            if name in pinned:
                for rule_id, count in applied:
                    withheld_substitutions.setdefault(name, []).append((rule_id, count))
                target.write_text(text, encoding="utf-8")
            else:
                for rule_id, count in applied:
                    substitution_counts[rule_id] = (
                        substitution_counts.get(rule_id, 0) + count
                    )
                target.write_text(replaced, encoding="utf-8")
        else:
            shutil.copy2(source, target)
            binaries += 1

    for overlay in contract["overlays"]:
        target = destination / overlay["publish_as"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPOSITORY_ROOT / overlay["overlay"], target)

    _write_snapshot_readme(destination, contract, kept, dropped)
    _write_provenance(destination, contract, kept, dropped, substitution_counts,
                      pinned, withheld_substitutions)
    _initialise_git(destination)
    return {
        "destination": destination,
        "copied": len(kept),
        "binaries": binaries,
        "dropped": dropped,
        "untracked": untracked,
        "substitutions": substitution_counts,
        "pinned": sorted(pinned),
        "withheld_substitutions": withheld_substitutions,
    }


def _write_snapshot_readme(destination, contract, kept, dropped):
    text = f"""# About this repository

This is the public form of a private research repository. It carries the code,
the contracts, the evidence and the record of what was decided. It does not
carry the recordings that project was built on, or anything derived from them.

Start with `findings.md` for what was measured and what could not be
established, `PROJECT-STATUS.md` for where the work stands and what was
deliberately not done, `project-purpose.md` for what this project claims and
refuses, and `README.md` for how to run it.

Some of the older documents here point at `current-state.md` and
`improvement-plan.md`, the private repository's internal status page and
roadmap. Neither is published. `PROJECT-STATUS.md` carries what they said that
matters to a reader.

## Why a separate repository rather than a cleaned one

The working repository tracks the owner's own recordings, a two speaker
conversation involving another person, and full transcripts and evaluations
derived from them, in its working tree **and in its git history**. Deleting a
file from a tree does not remove it from history. A history rewrite was
considered and rejected: it changes every commit hash anyway, so it preserves
nothing worth keeping, and it cannot prove completeness. This repository was
built fresh instead, so its history has one origin and nothing behind it.

## What was removed

{len(dropped)} of {len(kept) + len(dropped)} tracked files were left behind.

| Removed | Why |
|---|---|
""" + "\n".join(
        f"| `{path}` | {reason} |"
        for path, reason in contract["source_selection"]["why_excluded"].items()
    ) + """

A small number of strings were also replaced across the surviving files: a place
name, some machine local paths, a cloud resource name, a run identifier and a
few third party email addresses. Every replacement, and its reason, is listed in
`release/snapshot-provenance.json`, together with how many times each one fired
when this snapshot was built. The strings themselves are not listed, for the
obvious reason: a list of the private strings that were removed would be a list
of the private strings.

## What the removals cost you

- **The regression records pinned to the owner's recordings are gone.**
  `regression/fixtures/` holds openly licensed replacements assembled from
  LibriSpeech. They prove the pipeline runs. They validate nothing: they are read
  audiobook speech taking turns, with no overlap, no interruption and no
  disfluency.
- **`speech_sound_patterns/accent_contrast.py` cannot run**, because its whole
  design is holding one speaker constant across two accent targets. The frozen
  result of the single run that was made is committed and readable.
- **`.research_data/` was never tracked and is not here.** The part needed to
  reproduce the one published analysis has been extracted and pseudonymised into
  `speech_sound_patterns/variety-probe-evidence/`.
- **No finished pipeline run is committed.** Produce one from a fixture.

## What you can check for yourself

```text
python3 -m speech_sound_patterns.variety_probe_score --output /tmp/report.json
python3 -m speech_sound_patterns.validate_variety_probe /tmp/report.json
```

About two minutes, needing `numpy` and `jsonschema` and nothing else. Checked
by blocking each one in turn on 2026-08-28: `variety_probe_uncertainty.py`
imports numpy and `corpus_manifest.py` imports jsonschema, and the command
stops without either. The result is byte identical to the
committed report. Read the report's uncertainty block before quoting any number
from it: nothing at group level is distinguishable from zero, and the single
result that survives multiple comparison correction carries a lexical confound
that stops it being a claim about British English.

## Licence

GPL 3.0 or later. See `LICENSE`, and `NOTICE.md` for third party attribution.
"""
    (destination / "README-SNAPSHOT.md").write_text(text, encoding="utf-8")


def _write_provenance(destination, contract, kept, dropped, counts, pinned,
                      withheld):
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    provenance = {
        "schema_version": "1.0.0",
        "record_id": "public_snapshot_provenance_v1",
        "contract": "release/snapshot-contract-v1.0.0.json",
        "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        "source_commit": source_commit,
        "source_working_tree_clean": not dirty,
        "files_published": len(kept),
        "files_withheld": len(dropped),
        "withheld": [
            _apply(name, contract, name)[0] for name in sorted(dropped)
        ],
        "why_the_withheld_names_are_rewritten": (
            "The withheld list names the files that were held back, and some of "
            "those filenames are themselves private: one names the place a "
            "private conversation was recorded. The same substitution table that "
            "cleans the published files is applied to the list, so the shape of "
            "what was withheld is visible without the names being republished."
        ),
        "substitutions_applied": [
            {
                "id": rule["id"],
                "reason": rule["reason"],
                "occurrences": counts[rule["id"]],
                "restricted_to": rule.get("files"),
            }
            for rule in contract["substitutions"]
            if rule["id"] in counts
        ],
        "substitution_rules_that_did_not_fire": [
            rule["id"] for rule in contract["substitutions"]
            if rule["id"] not in counts
        ],
        "why_the_replaced_strings_are_not_listed_here": (
            "The rule table names, as literal strings, the private material it "
            "removes. Publishing it would republish all of it. The identifiers "
            "and reasons carry the transparency; the strings stay behind."
        ),
        "checksum_pinned_files_copied_unmodified": len(pinned),
        "substitutions_withheld_from_pinned_files": {
            name: [{"id": rule_id, "occurrences": count} for rule_id, count in rules]
            for name, rules in sorted(withheld.items())
        },
        "why_pinned_files_are_not_substituted": (
            "These records carry each other's checksums. Editing one breaks every "
            "record that pins it, and a published repository whose own integrity "
            "checks fail would be worse than one carrying a cloud resource name "
            "or the filename of a recording that is not published. They are "
            "copied byte for byte and the withheld substitutions are listed above "
            "so the decision is visible rather than silent."
        ),
        "note": (
            "source_working_tree_clean records whether the private repository "
            "had uncommitted changes when this snapshot was built. A snapshot "
            "built from a dirty tree cannot be traced back to a commit, so it "
            "should not be published."
        ),
    }
    (destination / "release" / "snapshot-provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )


def _initialise_git(destination):
    """Initialise and stage. Never commit: the owner makes every commit."""
    subprocess.run(["git", "init", "--quiet"], cwd=destination, check=True)
    subprocess.run(["git", "add", "-A"], cwd=destination, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--force", action="store_true",
                        help="replace a non empty destination")
    arguments = parser.parse_args()
    result = build(arguments.destination, force=arguments.force)
    print(f"Snapshot: {result['destination']}")
    print(f"  published {result['copied']} files, {result['binaries']} binary")
    print(f"  withheld  {len(result['dropped'])} files")
    if result["untracked"]:
        print(f"  {len(result['untracked'])} published files are not yet committed "
              "here. Grouped by directory, look at this before publishing:")
        grouped = {}
        for name in result["untracked"]:
            grouped.setdefault(str(Path(name).parent), []).append(name)
        for directory, names in sorted(grouped.items()):
            if len(names) > 3:
                print(f"      {directory}/  ({len(names)} files)")
            else:
                for name in names:
                    print(f"      {name}")
    for rule_id, count in sorted(result["substitutions"].items()):
        print(f"  substituted {rule_id}: {count}")
    print("  staged, not committed. The first commit is the owner's.")


if __name__ == "__main__":
    main()
