#!/usr/bin/env python3
"""Install one Java library extracted from a verified plugin ZIP."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
from xml.sax.saxutils import escape


def find_jar(archive: zipfile.ZipFile, pattern: str) -> str:
    matches = sorted(
        name
        for name in archive.namelist()
        if not name.endswith("/") and PurePosixPath(name).match(pattern)
    )
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one JAR matching {pattern!r}, found {matches}")
    return matches[0]


def write_pom(path: Path, group_id: str, artifact_id: str, version: str) -> None:
    """Write standalone metadata so Maven cannot inherit the caller project version."""
    path.write_text(
        """<project xmlns=\"http://maven.apache.org/POM/4.0.0\"
  xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"
  xsi:schemaLocation=\"http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd\">
  <modelVersion>4.0.0</modelVersion>
  <groupId>{group_id}</groupId>
  <artifactId>{artifact_id}</artifactId>
  <version>{version}</version>
  <packaging>jar</packaging>
</project>
""".format(
            group_id=escape(group_id),
            artifact_id=escape(artifact_id),
            version=escape(version),
        ),
        encoding="utf-8",
    )


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
            temporary_path = Path(temporary)
            jar_path = temporary_path / Path(jar_name).name
            with archive.open(jar_name) as source, jar_path.open("wb") as target:
                target.write(source.read())
            pom_path = temporary_path / "dependency.pom"
            write_pom(pom_path, args.group_id, args.artifact_id, args.version)
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
                    f"-DpomFile={pom_path}",
                ],
                check=True,
                # Running outside the caller's Maven project prevents the
                # install-file goal from inheriting its project version.
                cwd=temporary,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
