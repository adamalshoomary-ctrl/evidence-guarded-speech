"""Checkpoint 22E7 acquisition of the openly licensed reference stack.

This module downloads and proves data. It selects nothing, scores nothing and
changes no pipeline behaviour.

Every acquired file is written into the gitignored private research root, proved,
and recorded beside a captured licence snapshot. Proof means three things that
must all hold: the finished file is exactly the size the publisher declares, its
SHA256 is recomputed here by re-reading it from disk rather than trusting
anything the network reported, and where the publisher states a digest that
digest matches. A file failing any of them is deleted rather than kept, because
a plausible-looking truncated corpus is worse than a missing one.

Large downloads resume. The American subset dropped at 7.75 of 10.39 gigabytes
on its first attempt, and a ten gigabyte transfer that restarts from zero every
time a connection blinks never completes. Each retry asks for a fresh URL,
because a presigned link expires while the earlier attempt is still running.

Mozilla Data Collective downloads authenticate with ``MDC_API_KEY`` from the
gitignored ``.env``. The key is read into a request header and is never printed,
logged or written to any record this module produces.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from functools import partial
from pathlib import Path

from dotenv import load_dotenv

from .corpus_manifest import REPOSITORY_ROOT

PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
CORPUS_ROOT = PRIVATE_ROOT / "corpora"
LICENCE_ROOT = PRIVATE_ROOT / "licence_snapshots"
RECORD_ROOT = PRIVATE_ROOT / "acquisition"

USER_AGENT = "tempdoubleaa-speech-sound-research/1.0"
BLOCK_BYTES = 1024 * 1024
NETWORK_TIMEOUT_SECONDS = 120

# Free space kept back so an acquisition can never be the reason this machine
# runs out of disk. The 22E8 measurement still has to extract clips afterwards.
FREE_SPACE_MARGIN_BYTES = 3 * 1024**3

# WikiPron publishes a continuously updated scrape, so the branch tip is not a
# version. This is the exact commit that last touched the British broad file,
# and that commit fixed the English dialect selectors, which is precisely the
# kind of change that would silently alter a reference nobody had pinned.
WIKIPRON_COMMIT = "d282e848a211ea31cfd730f0ced8bc8cdab9e83d"
WIKIPRON_RAW = f"https://raw.githubusercontent.com/CUNY-CL/wikipron/{WIKIPRON_COMMIT}"

MFA_RELEASE = "https://github.com/MontrealCorpusTools/mfa-models/releases/download"


class AcquisitionError(RuntimeError):
    """Raised when an acquisition cannot be proved and must not be kept."""


def _plain_file(filename, url):
    return {
        "filename": filename,
        "url": url,
        "auth": "none",
        "upstream_checksum": {"algorithm": "none", "value": None},
    }


def _mdc_file(filename, dataset_id):
    return {
        "filename": filename,
        "url": f"https://mozilladatacollective.com/api/datasets/{dataset_id}/download",
        "auth": "mdc",
        "dataset_id": dataset_id,
        "upstream_checksum": {"algorithm": "sha256", "value": None},
    }


ACQUISITION_PLAN = {
    "wikipron_eng_latn_uk_broad": {
        "storage": "wikipron_eng_latn_uk_broad",
        "files": [
            _plain_file(
                "eng_latn_uk_broad.tsv",
                f"{WIKIPRON_RAW}/data/scrape/tsv/eng_latn_uk_broad.tsv",
            )
        ],
        "licence_snapshots": [
            ("wikipron_license.txt", f"{WIKIPRON_RAW}/LICENSE.txt"),
            ("wikipron_readme.md", f"{WIKIPRON_RAW}/README.md"),
            (
                "wiktionary_copyrights.html",
                "https://en.wiktionary.org/wiki/Wiktionary:Copyrights",
            ),
        ],
    },
    "wikipron_eng_latn_us_broad": {
        "storage": "wikipron_eng_latn_us_broad",
        "files": [
            _plain_file(
                "eng_latn_us_broad.tsv",
                f"{WIKIPRON_RAW}/data/scrape/tsv/eng_latn_us_broad.tsv",
            )
        ],
        "licence_snapshots": [
            ("wikipron_license.txt", f"{WIKIPRON_RAW}/LICENSE.txt"),
            ("wikipron_readme.md", f"{WIKIPRON_RAW}/README.md"),
            (
                "wiktionary_copyrights.html",
                "https://en.wiktionary.org/wiki/Wiktionary:Copyrights",
            ),
        ],
    },
    "wiktionary_australian_kaikki": {
        "storage": "wiktionary_australian_kaikki",
        "files": [
            _plain_file(
                "kaikki.org-dictionary-English.jsonl.gz",
                "https://kaikki.org/dictionary/English/"
                "kaikki.org-dictionary-English.jsonl.gz",
            )
        ],
        "licence_snapshots": [
            ("kaikki_rawdata.html", "https://kaikki.org/dictionary/rawdata.html"),
            ("kaikki_english_index.html", "https://kaikki.org/dictionary/English/"),
            (
                "wiktionary_copyrights.html",
                "https://en.wiktionary.org/wiki/Wiktionary:Copyrights",
            ),
        ],
    },
    "mfa_english_dictionary": {
        "storage": "mfa_english_dictionary",
        "files": [
            _plain_file(
                "english_uk_mfa.dict",
                f"{MFA_RELEASE}/dictionary-english_uk_mfa-v3.1.0/english_uk_mfa.dict",
            ),
            _plain_file(
                "english_us_mfa.dict",
                f"{MFA_RELEASE}/dictionary-english_us_mfa-v3.1.0/english_us_mfa.dict",
            ),
            _plain_file(
                "english_mfa.dict",
                f"{MFA_RELEASE}/dictionary-english_mfa-v3.1.0/english_mfa.dict",
            ),
        ],
        "licence_snapshots": [
            (
                "english_uk_mfa_v3_1_0.html",
                "https://mfa-models.readthedocs.io/en/latest/dictionary/English/"
                "English%20(UK)%20MFA%20dictionary%20v3_1_0.html",
            ),
            (
                "english_us_mfa_v3_1_0.html",
                "https://mfa-models.readthedocs.io/en/latest/dictionary/English/"
                "English%20(US)%20MFA%20dictionary%20v3_1_0.html",
            ),
            (
                "english_mfa_v3_1_0.html",
                "https://mfa-models.readthedocs.io/en/latest/dictionary/English/"
                "English%20MFA%20dictionary%20v3_1_0.html",
            ),
        ],
    },
    "common_voice_26_british_english": {
        "storage": "common_voice_26_gb",
        "files": [
            _mdc_file(
                "common-voice-scripted-speech-26-0-britis-0fe481c3.tar.gz",
                "cmrt6zrob000zmm07yqwjlpwi",
            )
        ],
        "licence_snapshots": [
            (
                "mdc_consumer_terms.html",
                "https://mozilladatacollective.com/terms/consumers",
            )
        ],
    },
    "common_voice_26_american_english_male": {
        "storage": "common_voice_26_us_male",
        "files": [
            _mdc_file(
                "common-voice-scripted-speech-26-0-americ-34c3c133.tar.gz",
                "cmrt6zbgx000vmm07hfuefigk",
            )
        ],
        "licence_snapshots": [
            (
                "mdc_consumer_terms.html",
                "https://mozilladatacollective.com/terms/consumers",
            )
        ],
    },
    "common_voice_26_american_english_female": {
        "storage": "common_voice_26_us_female",
        "files": [
            _mdc_file(
                "common-voice-scripted-speech-26-0-americ-079c33be.tar.gz",
                "cmrt70j4z001qmm07nvfsmgmr",
            )
        ],
        "licence_snapshots": [
            (
                "mdc_consumer_terms.html",
                "https://mozilladatacollective.com/terms/consumers",
            )
        ],
    },
}


def _mdc_key():
    load_dotenv(REPOSITORY_ROOT / ".env")
    key = (os.environ.get("MDC_API_KEY") or "").strip()
    if not key:
        raise AcquisitionError(
            "MDC_API_KEY is missing from .env, so no Mozilla Data Collective "
            "source can be acquired"
        )
    return key


def _fixed_url(url):
    """A URL factory for sources whose link does not expire between attempts."""
    return url


def _open(url, headers=None, method="GET", timeout=NETWORK_TIMEOUT_SECONDS):
    request = urllib.request.Request(url, method=method)
    request.add_header("User-Agent", USER_AGENT)
    for name, value in (headers or {}).items():
        request.add_header(name, value)
    return urllib.request.urlopen(request, timeout=timeout)


def _redact(text, key):
    """Never let a credential reach a message, a log line or a record."""
    return text.replace(key, "<MDC_API_KEY>") if key else text


def mdc_dataset_metadata(dataset_id, key=None):
    """Return the published dataset record, including its checksum and size."""
    key = key or _mdc_key()
    url = f"https://mozilladatacollective.com/api/datasets/{dataset_id}"
    try:
        with _open(url, {"Authorization": f"Bearer {key}", "Accept": "application/json"}) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise AcquisitionError(
            f"Mozilla Data Collective metadata for {dataset_id} failed with "
            f"HTTP {error.code}"
        ) from None


def _mdc_presigned_url(dataset_id, key):
    url = f"https://mozilladatacollective.com/api/datasets/{dataset_id}/download"
    try:
        with _open(
            url,
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        ) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise AcquisitionError(
            f"Mozilla Data Collective download for {dataset_id} failed with "
            f"HTTP {error.code}"
        ) from None
    presigned = body.get("downloadUrl")
    if not presigned:
        raise AcquisitionError(
            f"Mozilla Data Collective returned no download URL for {dataset_id}"
        )
    return presigned


def sha256_file(path):
    """Re-read a finished file from disk and hash it independently."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(BLOCK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def _stream_once(url, temporary, offset, headers):
    """Append one connection's worth of bytes, starting at offset."""
    request_headers = dict(headers or {})
    if offset:
        request_headers["Range"] = f"bytes={offset}-"
    with _open(url, request_headers) as response:
        if offset and response.status != 206:
            # The server ignored the range and restarted the body, so the
            # existing bytes are not a prefix of what is arriving now.
            temporary.unlink(missing_ok=True)
            offset = 0
        declared = response.headers.get("Content-Length")
        expected = offset + int(declared) if declared and declared.isdigit() else None
        with temporary.open("ab" if offset else "wb") as handle:
            for block in iter(lambda: response.read(BLOCK_BYTES), b""):
                handle.write(block)
    return temporary.stat().st_size, expected


def _stream_to_file(url_factory, destination, headers=None, attempts=5, expected_size=None):
    """Stream a URL to a temporary file, resuming after a dropped connection.

    A ten gigabyte download that restarts from zero every time the connection
    blinks never finishes. This resumes from whatever arrived, and asks the
    caller for a fresh URL each attempt because a presigned link expires.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".partial")
    target = expected_size
    last_error = None
    for attempt in range(1, attempts + 1):
        offset = temporary.stat().st_size if temporary.is_file() else 0
        if target is not None and offset == target:
            break
        try:
            written, declared_total = _stream_once(
                url_factory(), temporary, offset, headers
            )
        except Exception as error:  # noqa: BLE001
            last_error = error
            if attempt == attempts:
                break
            continue
        target = target if target is not None else declared_total
        if target is None or written == target:
            break
        last_error = AcquisitionError(
            f"{destination.name} stopped at {written} of {target} bytes"
        )
    final = temporary.stat().st_size if temporary.is_file() else 0
    if target is not None and final != target:
        raise AcquisitionError(
            f"{destination.name} arrived truncated: {final} of {target} bytes"
            + (f" ({last_error})" if last_error else "")
        )
    if not final:
        raise AcquisitionError(f"{destination.name} downloaded nothing: {last_error}")
    temporary.replace(destination)
    return final


def _require_free_space(needed_bytes):
    free = shutil.disk_usage(REPOSITORY_ROOT).free
    if free < needed_bytes + FREE_SPACE_MARGIN_BYTES:
        raise AcquisitionError(
            "not enough free disk space: "
            f"{needed_bytes / 1e9:.2f} GB needed plus a "
            f"{FREE_SPACE_MARGIN_BYTES / 1e9:.2f} GB margin, "
            f"{free / 1e9:.2f} GB free"
        )


def capture_licence_snapshots(source_id, snapshots):
    """Save the licence and terms pages exactly as they read on acquisition day."""
    captured = []
    directory = LICENCE_ROOT / source_id
    for name, url in snapshots:
        path = directory / name
        size = _stream_to_file(partial(_fixed_url, url), path)
        captured.append(
            {
                "name": name,
                "url": url,
                "size_bytes": size,
                "sha256": sha256_file(path),
                "captured_at": date.today().isoformat(),
            }
        )
    return captured


def acquire_file(source_id, spec, key=None):
    """Acquire one file, prove it twice, and refuse to keep an unproved copy."""
    storage = CORPUS_ROOT / ACQUISITION_PLAN[source_id]["storage"]
    destination = storage / spec["filename"]
    upstream = dict(spec["upstream_checksum"])
    url = spec["url"]
    headers = None

    if spec["auth"] == "mdc":
        key = key or _mdc_key()
        metadata = mdc_dataset_metadata(spec["dataset_id"], key)
        upstream = {"algorithm": "sha256", "value": metadata.get("checksum")}
        expected_size = metadata.get("sizeBytes")
        if not upstream["value"]:
            raise AcquisitionError(
                f"{source_id} publishes no checksum, so its download cannot be proved"
            )
    else:
        expected_size = None

    if destination.is_file():
        local = sha256_file(destination)
        size = destination.stat().st_size
    else:
        if expected_size:
            _require_free_space(expected_size)
        if spec["auth"] == "mdc":
            url_factory = partial(_mdc_presigned_url, spec["dataset_id"], key)
        else:
            url_factory = partial(_fixed_url, url)
        size = _stream_to_file(
            url_factory, destination, headers, expected_size=expected_size
        )
        local = sha256_file(destination)

    if upstream["algorithm"] == "sha256" and upstream["value"] != local:
        destination.unlink(missing_ok=True)
        raise AcquisitionError(
            f"{source_id} file {spec['filename']} does not match its published checksum"
        )
    if expected_size and size != expected_size:
        raise AcquisitionError(
            f"{source_id} file {spec['filename']} is {size} bytes, "
            f"published as {expected_size}"
        )
    return {
        "filename": spec["filename"],
        "canonical_download_url": spec["url"],
        "size_bytes": size,
        "local_sha256": local,
        "upstream_checksum": upstream,
        "local_verification_status": "verified",
        "retrieved_at": date.today().isoformat(),
    }


def acquire_source(source_id, capture_licences=True):
    """Acquire every file for one source and write its private record."""
    if source_id not in ACQUISITION_PLAN:
        raise AcquisitionError(f"{source_id} is not part of the checkpoint 22E7 plan")
    plan = ACQUISITION_PLAN[source_id]
    key = _mdc_key() if any(item["auth"] == "mdc" for item in plan["files"]) else None
    archives = [acquire_file(source_id, spec, key) for spec in plan["files"]]
    licences = (
        capture_licence_snapshots(source_id, plan["licence_snapshots"])
        if capture_licences
        else []
    )
    record = {
        "schema_version": "1.0.0",
        "source_id": source_id,
        "checkpoint": "22E7",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "local_storage": str(
            (CORPUS_ROOT / plan["storage"]).relative_to(REPOSITORY_ROOT)
        ),
        "archives": archives,
        "licence_snapshots": licences,
    }
    RECORD_ROOT.mkdir(parents=True, exist_ok=True)
    path = RECORD_ROOT / f"{source_id}.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        action="append",
        choices=sorted(ACQUISITION_PLAN),
        help="acquire one source; repeat the flag for several",
    )
    parser.add_argument(
        "--all", action="store_true", help="acquire every source in the plan"
    )
    parser.add_argument(
        "--skip-licence-capture",
        action="store_true",
        help="reverify archives without refetching licence pages",
    )
    args = parser.parse_args()
    selected = sorted(ACQUISITION_PLAN) if args.all else (args.source or [])
    if not selected:
        parser.error("choose --all or at least one --source")
    key = None
    for source_id in selected:
        print(f"{source_id}: acquiring")
        try:
            record = acquire_source(
                source_id, capture_licences=not args.skip_licence_capture
            )
        except AcquisitionError as error:
            key = key or (os.environ.get("MDC_API_KEY") or "").strip()
            print(f"{source_id}: FAILED {_redact(str(error), key)}")
            raise SystemExit(1)
        for archive in record["archives"]:
            print(
                f"  {archive['filename']} "
                f"{archive['size_bytes'] / 1e6:.2f} MB "
                f"sha256 {archive['local_sha256'][:16]}..."
            )
        for licence in record["licence_snapshots"]:
            print(f"  licence snapshot {licence['name']} sha256 {licence['sha256'][:16]}...")
    print("Acquisition complete. Nothing was measured, scored or selected.")


if __name__ == "__main__":
    main()
