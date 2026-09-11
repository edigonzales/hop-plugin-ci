#!/usr/bin/env python3
"""Deploy every ZIP and its verified publication POM from a plugin bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--settings", required=True, type=Path)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--repository-url", required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        command = [
            "mvn",
            "-s",
            str(args.settings),
            "-U",
            "-B",
            "-ntp",
            "org.apache.maven.plugins:maven-deploy-plugin:3.1.4:deploy-file",
            f"-Dfile={args.bundle_dir / artifact['zipFile']}",
            f"-DpomFile={args.bundle_dir / artifact['pomFile']}",
            "-Dpackaging=zip",
            f"-DrepositoryId={args.repository_id}",
            f"-Durl={args.repository_url}",
        ]
        subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
