#!/usr/bin/env python3
"""Collect and describe the exact Maven artifacts produced by a verified build."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_one(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one artifact for {pattern!r}, found {len(matches)}: {matches}")
    path = matches[0]
    if not path.is_file():
        raise SystemExit(f"Artifact is not a file: {path}")
    return path


def copy_file(source: Path, bundle: Path, artifact_id: str, role: str) -> tuple[str, str]:
    target = bundle / "artifacts" / artifact_id / role
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target.relative_to(bundle).as_posix(), sha256(source)


def collect(args: argparse.Namespace) -> dict[str, Any]:
    descriptors = json.loads(args.artifacts_json)
    if not isinstance(descriptors, list) or not descriptors:
        raise SystemExit("artifacts-json must be a non-empty JSON array")

    root = Path(args.root).resolve()
    bundle = Path(args.bundle_dir).resolve()
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir(parents=True)

    artifacts: list[dict[str, Any]] = []
    seen_coordinates: set[tuple[str, str]] = set()
    for descriptor in descriptors:
        group_id = descriptor["groupId"]
        artifact_id = descriptor["artifactId"]
        coordinate = (group_id, artifact_id)
        if coordinate in seen_coordinates:
            raise SystemExit(f"Duplicate Maven coordinate: {group_id}:{artifact_id}")
        seen_coordinates.add(coordinate)

        main = find_one(root, descriptor["fileGlob"])
        pom = find_one(root, descriptor["pomFile"])
        files: list[dict[str, str]] = []
        bundle_file, digest = copy_file(main, bundle, artifact_id, "main")
        files.append({"role": "main", "bundleFile": bundle_file, "sha256": digest})

        pom_bundle_file, pom_digest = copy_file(pom, bundle, artifact_id, "pom.xml")
        files.append({"role": "pom", "bundleFile": pom_bundle_file, "sha256": pom_digest})

        classifiers = descriptor.get("classifiers", [])
        if not isinstance(classifiers, list):
            raise SystemExit(f"classifiers must be a JSON array for {artifact_id}")
        seen_classifiers: set[str] = set()
        for classifier in classifiers:
            name = classifier["classifier"]
            if name in seen_classifiers:
                raise SystemExit(f"Duplicate classifier {name!r} for {artifact_id}")
            seen_classifiers.add(name)
            classified = find_one(root, classifier["fileGlob"])
            classified_bundle_file, classified_digest = copy_file(
                classified, bundle, artifact_id, name
            )
            files.append(
                {
                    "role": "classifier",
                    "classifier": name,
                    "type": classifier.get("type", "jar"),
                    "bundleFile": classified_bundle_file,
                    "sha256": classified_digest,
                }
            )

        artifacts.append(
            {
                "groupId": group_id,
                "artifactId": artifact_id,
                "packaging": descriptor["packaging"],
                "version": args.version,
                "files": files,
            }
        )

    return {
        "schemaVersion": 1,
        "repository": args.repository,
        "commitSha": args.commit_sha,
        "version": args.version,
        "hopVersion": args.hop_version,
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-json", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--hop-version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = collect(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
