#!/usr/bin/env python3
"""Validate that a downloaded ZIP is the artifact produced by the verified job."""

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--plugin-root", required=True)
    parser.add_argument("--repository-kind", choices=("snapshot", "release"), required=True)
    parser.add_argument("--tag-prefix", required=True)
    parser.add_argument("--git-ref", required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    expected = {
        "schemaVersion": 1,
        "repository": args.repository,
        "commitSha": args.commit_sha,
        "artifactId": args.artifact_id,
        "version": args.version,
        "pluginRoot": args.plugin_root.rstrip("/"),
        "zipFile": args.zip.name,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise SystemExit(f"Manifest mismatch for {key}: {manifest.get(key)!r} != {value!r}")
    actual_sha = sha256(args.zip)
    if manifest.get("sha256") != actual_sha:
        raise SystemExit(f"ZIP SHA-256 mismatch: {manifest.get('sha256')} != {actual_sha}")
    root = args.plugin_root.rstrip("/") + "/"
    with zipfile.ZipFile(args.zip) as archive:
        if archive.testzip() is not None:
            raise SystemExit("Downloaded ZIP is corrupt")
        if not any(name.startswith(root) for name in archive.namelist()):
            raise SystemExit(f"Downloaded ZIP lacks required plugin root {root}")

    is_snapshot = args.version.endswith("-SNAPSHOT")
    if (args.repository_kind == "snapshot") != is_snapshot:
        raise SystemExit("Repository kind does not match Maven version")
    if args.repository_kind == "release":
        if not args.git_ref.startswith(f"refs/tags/{args.tag_prefix}"):
            raise SystemExit("Release publication requires a version tag")
        tag_version = args.git_ref.removeprefix(f"refs/tags/{args.tag_prefix}")
        if tag_version != args.version:
            raise SystemExit(f"Tag version {tag_version} does not match POM version {args.version}")
    print(f"Verified {args.zip} ({actual_sha})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
