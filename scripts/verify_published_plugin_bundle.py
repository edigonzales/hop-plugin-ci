#!/usr/bin/env python3
"""Resolve published plugin ZIPs through Maven and compare their bytes."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

from download_maven_artifact import download_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--settings", required=True, type=Path)
    parser.add_argument("--local-repository", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    import json

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 2:
        raise SystemExit("Public Maven verification requires a multi-artifact manifest")
    if args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True)

    for artifact in manifest["artifacts"]:
        output = args.output_dir / f"{artifact['artifactId']}.zip"
        download_artifact(
            group_id=artifact["groupId"],
            artifact_id=artifact["artifactId"],
            version=artifact["version"],
            extension="zip",
            classifier="",
            maven_settings=args.settings,
            output=output,
            maven_options="-U -B -ntp",
            local_repository=args.local_repository,
        )
        expected = args.bundle_dir / artifact["zipFile"]
        if expected.read_bytes() != output.read_bytes():
            raise SystemExit(f"Published ZIP differs from verified ZIP: {artifact['artifactId']}")
        print(f"Verified public Maven snapshot: {artifact['groupId']}:{artifact['artifactId']}:{artifact['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
