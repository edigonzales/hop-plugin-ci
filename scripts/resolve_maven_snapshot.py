#!/usr/bin/env python3
"""Resolve one immutable timestamped ZIP from a Maven SNAPSHOT repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def fetch(url: str) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise ValueError(f"Cannot download {url}: {error}") from error


def resolve_version(metadata: bytes, group: str, artifact: str, version: str, extension: str) -> str:
    root = ET.fromstring(metadata)
    if root.findtext("groupId") != group or root.findtext("artifactId") != artifact:
        raise ValueError(f"Unexpected Maven coordinates in metadata for {group}:{artifact}")
    if root.findtext("version") != version or not version.endswith("-SNAPSHOT"):
        raise ValueError(f"Expected SNAPSHOT metadata for {group}:{artifact}:{version}")
    values = [
        node.findtext("value")
        for node in root.findall("versioning/snapshotVersions/snapshotVersion")
        if node.findtext("extension") == extension and not node.findtext("classifier")
    ]
    if len(values) != 1 or not values[0]:
        raise ValueError(
            f"Expected exactly one unclassified {extension} snapshot for "
            f"{group}:{artifact}:{version}, found {values}"
        )
    return values[0]


def coordinate_url(repository: str, group: str, artifact: str, version: str) -> str:
    base = repository.rstrip("/") + "/" + group.replace(".", "/")
    return f"{base}/{artifact}/{version}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="https://jars.interlis.guru/snapshots")
    parser.add_argument("--group", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--extension", default="zip")
    parser.add_argument(
        "--verify-artifact",
        action="append",
        default=[],
        metavar="ARTIFACT:EXTENSION",
        help="Require a related artifact to have the same resolved snapshot version",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    try:
        coordinate = coordinate_url(args.repository, args.group, args.artifact, args.version)
        resolved = resolve_version(
            fetch(f"{coordinate}/maven-metadata.xml"),
            args.group,
            args.artifact,
            args.version,
            args.extension,
        )
        for related in args.verify_artifact:
            try:
                related_artifact, related_extension = related.split(":", 1)
            except ValueError as error:
                raise ValueError(
                    f"Related artifact must use ARTIFACT:EXTENSION, got {related!r}"
                ) from error
            related_coordinate = coordinate_url(
                args.repository, args.group, related_artifact, args.version
            )
            related_resolved = resolve_version(
                fetch(f"{related_coordinate}/maven-metadata.xml"),
                args.group,
                related_artifact,
                args.version,
                related_extension,
            )
            if related_resolved != resolved:
                raise ValueError(
                    f"Related artifact {related_artifact}:{related_extension} belongs to "
                    f"snapshot {related_resolved}, expected {resolved}"
                )
            related_url = (
                f"{related_coordinate}/{related_artifact}-{resolved}.{related_extension}"
            )
            fetch(related_url)
        url = f"{coordinate}/{args.artifact}-{resolved}.{args.extension}"
        payload = fetch(url)
        if args.extension == "zip":
            with tempfile.TemporaryDirectory(dir=args.output.parent) as temporary:
                temporary_path = Path(temporary) / args.output.name
                temporary_path.write_bytes(payload)
                with zipfile.ZipFile(temporary_path) as archive:
                    bad_entry = archive.testzip()
                    if bad_entry:
                        raise ValueError(f"Corrupt ZIP entry: {bad_entry}")
                args.output.parent.mkdir(parents=True, exist_ok=True)
                temporary_path.replace(args.output)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        result = {
            "group": args.group,
            "artifact": args.artifact,
            "version": args.version,
            "resolvedVersion": resolved,
            "url": url,
            "sha256": digest,
            "path": str(args.output),
        }
        print(json.dumps(result, sort_keys=True))
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as output:
                output.write(f"resolved_version={resolved}\n")
                output.write(f"sha256={digest}\n")
                output.write(f"path={args.output}\n")
                output.write(f"zip_name={args.output.name}\n")
    except (OSError, ValueError, urllib.error.URLError, ET.ParseError, zipfile.BadZipFile) as error:
        print(f"Maven snapshot resolution failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
