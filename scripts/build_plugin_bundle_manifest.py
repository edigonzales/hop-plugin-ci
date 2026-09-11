#!/usr/bin/env python3
"""Collect and describe multiple verified Apache Hop plugin ZIPs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any
from xml.sax.saxutils import escape
import zipfile


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_one(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one ZIP for {pattern!r}, found {len(matches)}: {matches}")
    path = matches[0]
    if not path.is_file():
        raise SystemExit(f"ZIP is not a file: {path}")
    return path


def validate_relative_path(value: str, label: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"Unsafe {label}: {value!r}")


def validate_archive(path: Path, plugin_root: str) -> None:
    validate_relative_path(plugin_root, "plugin root")
    root = plugin_root.rstrip("/") + "/"
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise SystemExit(f"Corrupt ZIP archive: {path}")
        entries = [name for name in archive.namelist() if not name.endswith("/")]
        if not any(name.startswith(root) for name in entries):
            raise SystemExit(f"ZIP does not contain required plugin root {root}: {path}")
        for name in entries:
            validate_relative_path(name, "ZIP entry")


def publication_pom(group_id: str, artifact_id: str, version: str, hop_version: str) -> str:
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<project xmlns=\"http://maven.apache.org/POM/4.0.0\"
         xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"
         xsi:schemaLocation=\"http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd\">
  <modelVersion>4.0.0</modelVersion>
  <groupId>{escape(group_id)}</groupId>
  <artifactId>{escape(artifact_id)}</artifactId>
  <version>{escape(version)}</version>
  <packaging>zip</packaging>
  <name>Apache Hop plugin {escape(artifact_id)}</name>
  <description>Verified Apache Hop {escape(hop_version)} plugin ZIP.</description>
</project>
"""


def collect(args: argparse.Namespace) -> dict[str, Any]:
    descriptors = json.loads(args.artifacts_json)
    if not isinstance(descriptors, list) or not descriptors:
        raise SystemExit("artifacts-json must be a non-empty JSON array")

    root = Path(args.root).resolve()
    bundle = Path(args.bundle_dir).resolve()
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "artifacts").mkdir(parents=True)

    artifacts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_zip_names: set[str] = set()
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            raise SystemExit("Every ZIP descriptor must be an object")
        required = {"artifactId", "zipGlob", "pluginRoot"}
        if not required <= descriptor.keys():
            raise SystemExit(f"ZIP descriptor is missing fields: {sorted(required - descriptor.keys())}")

        artifact_id = descriptor["artifactId"]
        zip_glob = descriptor["zipGlob"]
        plugin_root = descriptor["pluginRoot"]
        if not all(isinstance(value, str) and value for value in (artifact_id, zip_glob, plugin_root)):
            raise SystemExit("artifactId, zipGlob and pluginRoot must be non-empty strings")
        if artifact_id in seen_ids:
            raise SystemExit(f"Duplicate ZIP artifactId: {artifact_id}")
        seen_ids.add(artifact_id)

        zip_path = find_one(root, zip_glob)
        expected_name = f"{artifact_id}-{args.version}.zip"
        if zip_path.name != expected_name:
            raise SystemExit(f"Unexpected ZIP filename {zip_path.name!r}; expected {expected_name!r}")
        if zip_path.name in seen_zip_names:
            raise SystemExit(f"Duplicate ZIP filename: {zip_path.name}")
        seen_zip_names.add(zip_path.name)
        validate_archive(zip_path, plugin_root)

        artifact_dir = bundle / "artifacts" / artifact_id
        artifact_dir.mkdir(parents=True)
        bundled_zip = artifact_dir / zip_path.name
        shutil.copy2(zip_path, bundled_zip)
        pom_path = artifact_dir / f"{artifact_id}.pom"
        pom_path.write_text(
            publication_pom(args.group_id, artifact_id, args.version, args.hop_version),
            encoding="utf-8",
        )

        artifacts.append(
            {
                "groupId": args.group_id,
                "artifactId": artifact_id,
                "version": args.version,
                "packaging": "zip",
                "zipFile": bundled_zip.relative_to(bundle).as_posix(),
                "sha256": sha256(bundled_zip),
                "pomFile": pom_path.relative_to(bundle).as_posix(),
                "pomSha256": sha256(pom_path),
                "pluginRoot": plugin_root.rstrip("/"),
            }
        )

    manifest = {
        "schemaVersion": 2,
        "repository": args.repository,
        "commitSha": args.commit_sha,
        "version": args.version,
        "hopVersion": args.hop_version,
        "artifacts": artifacts,
    }
    manifest_path = bundle / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-json", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--hop-version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = collect(args)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
