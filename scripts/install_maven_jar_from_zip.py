#!/usr/bin/env python3
"""Install one Java library extracted from a verified plugin ZIP."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
import zipfile
from pathlib import Path
from pathlib import PurePosixPath


def find_jar(archive: zipfile.ZipFile, pattern: str) -> str:
    matches = sorted(
        name
        for name in archive.namelist()
        if not name.endswith("/") and PurePosixPath(name).match(pattern)
    )
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one JAR matching {pattern!r}, found {matches}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--jar-glob", required=True)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--maven-settings", required=True, type=Path)
    args = parser.parse_args()

    with zipfile.ZipFile(args.zip) as archive:
        jar_name = find_jar(archive, args.jar_glob)
        with tempfile.TemporaryDirectory() as temporary:
            jar_path = Path(temporary) / Path(jar_name).name
            with archive.open(jar_name) as source, jar_path.open("wb") as target:
                target.write(source.read())
            subprocess.run(
                [
                    "mvn",
                    "-s",
                    str(args.maven_settings),
                    "-U",
                    "-B",
                    "-ntp",
                    "install:install-file",
                    f"-Dfile={jar_path}",
                    f"-DgroupId={args.group_id}",
                    f"-DartifactId={args.artifact_id}",
                    f"-Dversion={args.version}",
                    "-Dpackaging=jar",
                    "-DgeneratePom=true",
                ],
                check=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
