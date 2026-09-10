#!/usr/bin/env python3
"""Validate one packaged plugin ZIP and write its reproducibility manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_zip(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one ZIP for {pattern!r}, found {len(matches)}")
    return matches[0]


def validate_zip_filename(path: Path, artifact_id: str, version: str) -> None:
    expected = f"{artifact_id}-{version}.zip"
    if path.name != expected:
        raise SystemExit(f"Unexpected ZIP filename {path.name!r}; expected {expected!r}")


def validate_archive(path: Path, plugin_root: str) -> None:
    root = plugin_root.rstrip("/") + "/"
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise SystemExit(f"Corrupt ZIP archive: {path}")
        entries = [name for name in archive.namelist() if not name.endswith("/")]
        if not any(name.startswith(root) for name in entries):
            raise SystemExit(f"ZIP does not contain required plugin root {root}: {path}")
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in entries):
            raise SystemExit(f"ZIP contains an unsafe path: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip-glob", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--hop-version", required=True)
    parser.add_argument("--plugin-root", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    zip_path = find_zip(Path.cwd(), args.zip_glob)
    validate_zip_filename(zip_path, args.artifact_id, args.version)
    validate_archive(zip_path, args.plugin_root)
    manifest = {
        "schemaVersion": 1,
        "repository": args.repository,
        "commitSha": args.commit_sha,
        "groupId": args.group_id,
        "artifactId": args.artifact_id,
        "version": args.version,
        "hopVersion": args.hop_version,
        "zipFile": zip_path.name,
        "sha256": sha256(zip_path),
        "pluginRoot": args.plugin_root.rstrip("/"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
