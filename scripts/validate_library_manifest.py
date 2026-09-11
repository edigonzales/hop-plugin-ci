#!/usr/bin/env python3
"""Validate a Maven library bundle before publication."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_descriptors(raw: str) -> set[tuple[str, str]]:
    values = json.loads(raw)
    if not isinstance(values, list):
        raise SystemExit("artifacts-json must be a JSON array")
    return {(value["groupId"], value["artifactId"]) for value in values}


def validate(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = Path(args.manifest)
    bundle = Path(args.bundle_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "schemaVersion": 1,
        "repository": args.repository,
        "commitSha": args.commit_sha,
        "version": args.version,
        "hopVersion": args.hop_version,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise SystemExit(f"Manifest mismatch for {key}: {manifest.get(key)!r} != {value!r}")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise SystemExit("Manifest contains no artifacts")
    coordinates = {(item.get("groupId"), item.get("artifactId")) for item in artifacts}
    if coordinates != expected_descriptors(args.artifacts_json):
        raise SystemExit(f"Manifest coordinates differ from workflow contract: {coordinates}")

    listed: set[str] = set()
    for artifact in artifacts:
        for file_info in artifact.get("files", []):
            bundle_file = file_info["bundleFile"]
            if bundle_file in listed:
                raise SystemExit(f"Duplicate bundle file: {bundle_file}")
            listed.add(bundle_file)
            path = bundle / bundle_file
            if not path.is_file():
                raise SystemExit(f"Missing bundle file: {path}")
            actual = sha256(path)
            if actual != file_info["sha256"]:
                raise SystemExit(f"SHA-256 mismatch for {bundle_file}: {actual} != {file_info['sha256']}")

    actual_files = {
        path.relative_to(bundle).as_posix()
        for path in (bundle / "artifacts").rglob("*")
        if path.is_file()
    }
    if actual_files != listed:
        raise SystemExit(f"Bundle contains unexpected files: {sorted(actual_files - listed)}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--artifacts-json", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--hop-version", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
