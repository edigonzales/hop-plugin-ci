#!/usr/bin/env python3
"""Deploy an Actions artifact using Maven, without a build."""

import argparse
from pathlib import Path
import subprocess

from stage_artifacts import read_pom


def publish(bundle, kind, git_ref, tag_prefix, repository_id, url):
    deployments = []
    files = {path for path in bundle.iterdir() if path.is_file()}
    remaining = files.copy()
    poms = sorted(bundle.glob("*.pom"))
    if not poms:
        raise ValueError("The verification artifact contains no Maven POMs")
    for pom in poms:
        _, artifact, version, packaging = read_pom(pom)
        if kind == "snapshot" and not version.endswith("-SNAPSHOT"):
            raise ValueError(f"Expected a SNAPSHOT version in {pom}")
        if kind == "release" and (
            version.endswith("-SNAPSHOT") or git_ref != f"refs/tags/{tag_prefix}{version}"
        ):
            raise ValueError(f"Release tag {git_ref!r} does not match {version}")
        stem = f"{artifact}-{version}"
        if pom.name != stem + ".pom":
            raise ValueError(f"Unexpected POM name: {pom}")
        primary = files.intersection(bundle / (stem + ext) for ext in (".jar", ".zip"))
        if len(primary) > 1:
            raise ValueError(f"Multiple primary artifacts for {pom}")
        main = next(iter(primary), pom)
        if main == pom and packaging != "pom":
            raise ValueError(f"Missing publication file for {pom} ({packaging})")
        classifiers = sorted(bundle.glob(f"{stem}-*.jar"))
        if classifiers and main.suffix != ".jar":
            raise ValueError(f"Classifiers require a main JAR: {pom}")
        deployed_files = {pom, main, *classifiers}
        if not deployed_files <= remaining:
            raise ValueError(f"Files match more than one artifact: {sorted(deployed_files - remaining)}")
        remaining.difference_update(deployed_files)
        deployments.append((pom, main, classifiers))
    if remaining:
        raise ValueError(f"Artifacts without Maven POMs: {sorted(remaining)}")

    # Parent POMs precede any JAR or ZIP that references them.
    for pom, main, classifiers in sorted(deployments, key=lambda deploy: deploy[0] != deploy[1]):
        command = [
            "mvn", "-B", "-ntp", "org.apache.maven.plugins:maven-deploy-plugin:3.1.4:deploy-file",
            f"-Dfile={main}", f"-DpomFile={pom}", f"-Dpackaging={main.suffix[1:]}",
            f"-DrepositoryId={repository_id}", f"-Durl={url}",
        ]
        if classifiers:
            command += [
                "-Dfiles=" + ",".join(map(str, classifiers)),
                "-Dclassifiers=" + ",".join(path.stem.removeprefix(pom.stem + "-") for path in classifiers),
                "-Dtypes=" + ",".join("jar" for _ in classifiers),
            ]
        subprocess.run(command, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--kind", choices=("snapshot", "release"), required=True)
    parser.add_argument("--git-ref", required=True)
    parser.add_argument("--tag-prefix", default="v")
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    publish(args.bundle, args.kind, args.git_ref, args.tag_prefix, args.repository_id, args.url)
