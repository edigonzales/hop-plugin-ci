#!/usr/bin/env python3
"""Validate a downloaded multi-ZIP Apache Hop plugin bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_zip(path: Path, plugin_root: str) -> None:
    root = plugin_root.rstrip("/") + "/"
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise SystemExit(f"Downloaded ZIP is corrupt: {path}")
        entries = archive.namelist()
        if not any(name.startswith(root) for name in entries):
            raise SystemExit(f"Downloaded ZIP lacks required plugin root {root}: {path}")
        for name in entries:
            path_name = Path(name)
            if path_name.is_absolute() or ".." in path_name.parts:
                raise SystemExit(f"Downloaded ZIP contains an unsafe path: {path}")


def pom_value(root: ET.Element, name: str) -> str | None:
    return root.findtext(f"{{http://maven.apache.org/POM/4.0.0}}{name}") or root.findtext(name)


def validate_pom(path: Path, group_id: str, artifact_id: str, version: str) -> None:
    root = ET.parse(path).getroot()
    values = {
        "groupId": pom_value(root, "groupId"),
        "artifactId": pom_value(root, "artifactId"),
        "version": pom_value(root, "version"),
        "packaging": pom_value(root, "packaging") or "jar",
    }
    expected = {
        "groupId": group_id,
        "artifactId": artifact_id,
        "version": version,
        "packaging": "zip",
    }
    if values != expected:
        raise SystemExit(f"Publication POM mismatch for {path}: {values!r} != {expected!r}")


def validate(args: argparse.Namespace) -> dict:
    bundle = Path(args.bundle_dir)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    expected_header = {
        "schemaVersion": 2,
        "repository": args.repository,
        "commitSha": args.commit_sha,
        "version": args.version,
        "hopVersion": args.hop_version,
    }
    for key, value in expected_header.items():
        if manifest.get(key) != value:
            raise SystemExit(f"Manifest mismatch for {key}: {manifest.get(key)!r} != {value!r}")

    descriptors = json.loads(args.artifacts_json)
    if not isinstance(descriptors, list) or not descriptors:
        raise SystemExit("artifacts-json must be a non-empty JSON array")
    expected = {
        descriptor["artifactId"]: descriptor for descriptor in descriptors
    }
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise SystemExit("Manifest contains no artifacts")
    if {item.get("artifactId") for item in artifacts} != set(expected):
        raise SystemExit("Manifest artifact IDs differ from workflow contract")

    manifest_relative = Path(args.manifest).resolve().relative_to(bundle.resolve()).as_posix()
    listed: set[str] = {"manifest.json", manifest_relative}
    for artifact in artifacts:
        artifact_id = artifact.get("artifactId")
        descriptor = expected[artifact_id]
        expected_root = descriptor["pluginRoot"].rstrip("/")
        expected_zip = f"{artifact_id}-{args.version}.zip"
        expected_values = {
            "groupId": args.group_id,
            "artifactId": artifact_id,
            "version": args.version,
            "packaging": "zip",
            "pluginRoot": expected_root,
            "zipFile": f"artifacts/{artifact_id}/{expected_zip}",
            "pomFile": f"artifacts/{artifact_id}/{artifact_id}.pom",
        }
        for key, value in expected_values.items():
            if artifact.get(key) != value:
                raise SystemExit(f"Manifest mismatch for {artifact_id} field {key}")

        for key in ("zipFile", "pomFile"):
            relative = artifact[key]
            path = bundle / relative
            if not path.is_file():
                raise SystemExit(f"Missing bundle file: {path}")
            if relative in listed:
                raise SystemExit(f"Duplicate bundle file: {relative}")
            listed.add(relative)
            digest_key = "sha256" if key == "zipFile" else "pomSha256"
            if sha256(path) != artifact.get(digest_key):
                raise SystemExit(f"SHA-256 mismatch for {relative}")
        zip_path = bundle / artifact["zipFile"]
        validate_zip(zip_path, expected_root)
        validate_pom(bundle / artifact["pomFile"], args.group_id, artifact_id, args.version)

    actual_files = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file()
    }
    if actual_files != listed:
        raise SystemExit(f"Bundle contains unexpected files: {sorted(actual_files - listed)}")

    is_snapshot = args.version.endswith("-SNAPSHOT")
    if (args.repository_kind == "snapshot") != is_snapshot:
        raise SystemExit("Repository kind does not match Maven version")
    if args.repository_kind == "release":
        expected_ref = f"refs/tags/{args.tag_prefix}{args.version}"
        if args.git_ref != expected_ref:
            raise SystemExit(f"Release publication requires exact tag {expected_ref}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--artifacts-json", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--hop-version", required=True)
    parser.add_argument("--repository-kind", choices=("snapshot", "release"), required=True)
    parser.add_argument("--tag-prefix", required=True)
    parser.add_argument("--git-ref", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
