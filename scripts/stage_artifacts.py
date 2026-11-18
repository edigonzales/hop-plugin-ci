#!/usr/bin/env python3
"""Collect built files and their Maven POMs for an Actions artifact."""

import argparse
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET


NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def read_pom(pom):
    project = ET.parse(pom).getroot()
    values = [
        project.findtext(f"m:{key}", namespaces=NS)
        or project.findtext(f"m:parent/m:{key}", namespaces=NS)
        for key in ("groupId", "artifactId", "version")
    ]
    if not all(value and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", value) for value in values):
        raise ValueError(f"Expected literal Maven coordinates in {pom}")
    if project.find("m:artifactId", NS) is None:
        raise ValueError(f"Missing artifactId in {pom}")
    return *values, project.findtext("m:packaging", "jar", NS)


def stage(project_pom, artifacts, output):
    group, _, version, _ = read_pom(project_pom)
    output.mkdir(parents=True, exist_ok=False)
    if not artifacts:
        raise ValueError("Declare at least one publication artifact")
    seen = set()
    for entry in artifacts:
        pom = Path(entry["pom"]) if "pom" in entry else None
        path = None
        if "file" in entry:
            matches = [path for path in Path.cwd().glob(entry["file"]) if path.is_file()]
            if len(matches) != 1:
                raise ValueError(f"Expected one file for {entry['file']!r}: {matches}")
            path = matches[0]

        if pom is not None:
            _, artifact, pom_version, packaging = read_pom(pom)
            if pom_version != version:
                raise ValueError(f"{pom} uses {pom_version}, expected {version}")
            if path is None and packaging != "pom":
                raise ValueError(f"Missing publication file for {pom} ({packaging})")
        else:
            ending = f"-{version}.zip"
            if path is None or not path.name.endswith(ending):
                raise ValueError(f"A ZIP without a POM must be named <artifactId>{ending}: {path}")
            artifact = path.name.removesuffix(ending)
            if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", artifact):
                raise ValueError(f"Invalid ZIP artifactId: {artifact!r}")

        if artifact in seen:
            raise ValueError(f"Duplicate publication artifactId: {artifact}")
        seen.add(artifact)
        stem = f"{artifact}-{version}"
        staged_pom = output / (stem + ".pom")
        if pom is None:
            staged_pom.write_text(
                '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
                '  <modelVersion>4.0.0</modelVersion>\n'
                f'  <groupId>{group}</groupId>\n'
                f'  <artifactId>{artifact}</artifactId>\n'
                f'  <version>{version}</version>\n'
                '  <packaging>zip</packaging>\n</project>\n',
                encoding="utf-8",
            )
        else:
            shutil.copyfile(pom, staged_pom)
        if path is not None:
            if path.suffix not in (".jar", ".zip"):
                raise ValueError(f"Expected a JAR or ZIP: {path}")
            if path.suffix == ".zip" and path.name != stem + ".zip":
                raise ValueError(f"ZIP file name does not match Maven coordinates: {path}")
            shutil.copyfile(path, output / (stem + path.suffix))
        for classifier in entry.get("classifiers", []):
            if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", classifier):
                raise ValueError(f"Invalid classifier: {classifier!r}")
            if path is None or path.suffix != ".jar":
                raise ValueError("Classifiers require a main JAR")
            attached = path.with_name(f"{path.stem}-{classifier}.jar")
            shutil.copyfile(attached, output / f"{stem}-{classifier}.jar")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pom", type=Path, required=True)
    parser.add_argument("--artifacts", type=json.loads, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    stage(args.pom, args.artifacts, args.output)
