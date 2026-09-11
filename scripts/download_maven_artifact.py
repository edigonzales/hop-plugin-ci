#!/usr/bin/env python3
"""Download the current Maven artifact for a declared coordinate.

Maven resolves ``-SNAPSHOT`` versions through repository metadata.  This helper
uses Maven itself instead of selecting and propagating a timestamped snapshot
version, then copies the resolved artifact to the caller-provided path.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path


DEPENDENCY_PLUGIN = "org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy"


def artifact_coordinate(
    group_id: str,
    artifact_id: str,
    version: str,
    extension: str,
    classifier: str = "",
) -> str:
    """Return Maven's dependency-plugin coordinate notation."""
    parts = [group_id, artifact_id, version]
    if classifier:
        parts.append(classifier)
    parts.append(extension)
    return ":".join(parts)


def download_artifact(
    *,
    group_id: str,
    artifact_id: str,
    version: str,
    extension: str,
    classifier: str,
    maven_settings: Path,
    output: Path,
    maven_options: str,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    coordinate = artifact_coordinate(group_id, artifact_id, version, extension, classifier)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        temporary_path = Path(temporary)
        command = [
            "mvn",
            *shlex.split(maven_options),
            "-s",
            str(maven_settings),
            DEPENDENCY_PLUGIN,
            f"-Dartifact={coordinate}",
            f"-DoutputDirectory={temporary_path}",
            "-Dmdep.stripVersion=true",
            "-Dmdep.overWriteIfNewer=true",
        ]
        subprocess.run(command, check=True)
        matches = sorted(temporary_path.glob(f"*.{extension}"))
        if len(matches) != 1:
            raise RuntimeError(
                f"Expected exactly one downloaded .{extension} artifact for {coordinate}, "
                f"found {matches}"
            )
        shutil.copyfile(matches[0], output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", dest="group_id", required=True)
    parser.add_argument("--artifact", dest="artifact_id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--extension", default="zip")
    parser.add_argument("--classifier", default="")
    parser.add_argument("--maven-settings", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--maven-options", default="-U -B -ntp")
    args = parser.parse_args()

    download_artifact(
        group_id=args.group_id,
        artifact_id=args.artifact_id,
        version=args.version,
        extension=args.extension,
        classifier=args.classifier,
        maven_settings=args.maven_settings,
        output=args.output,
        maven_options=args.maven_options,
    )
    print(f"Downloaded current Maven artifact {args.group_id}:{args.artifact_id}:{args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
