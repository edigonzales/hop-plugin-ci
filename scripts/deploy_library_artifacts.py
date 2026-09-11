#!/usr/bin/env python3
"""Deploy the exact files from a validated Maven library bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess


DEPLOY = "org.apache.maven.plugins:maven-deploy-plugin:3.1.4:deploy-file"


def deploy(args: argparse.Namespace) -> None:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    bundle = Path(args.bundle_dir)
    for artifact in manifest["artifacts"]:
        files = artifact["files"]
        main = next(item for item in files if item["role"] == "main")
        pom = next(item for item in files if item["role"] == "pom")
        classifiers = [item for item in files if item["role"] == "classifier"]
        command = [
            "mvn",
            *shlex.split(args.maven_options),
            "-s",
            str(args.settings),
            DEPLOY,
            f"-DgroupId={artifact['groupId']}",
            f"-DartifactId={artifact['artifactId']}",
            f"-Dversion={artifact['version']}",
            f"-Dfile={bundle / main['bundleFile']}",
            f"-DpomFile={bundle / pom['bundleFile']}",
            f"-Dpackaging={artifact['packaging']}",
            f"-DrepositoryId={args.repository_id}",
            f"-Durl={args.repository_url}",
        ]
        if classifiers:
            command.extend(
                [
                    "-Dfiles=" + ",".join(str(bundle / item["bundleFile"]) for item in classifiers),
                    "-Dclassifiers=" + ",".join(item["classifier"] for item in classifiers),
                    "-Dtypes=" + ",".join(item.get("type", "jar") for item in classifiers),
                ]
            )
        subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--settings", required=True, type=Path)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--maven-options", default="-U -B -ntp")
    args = parser.parse_args()
    deploy(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
