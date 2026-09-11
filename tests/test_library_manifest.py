from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_library_manifest.py"
VALIDATE = ROOT / "scripts" / "validate_library_manifest.py"


class LibraryManifestTest(unittest.TestCase):
    def test_builds_and_validates_parent_jar_and_classifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "module/target").mkdir(parents=True)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            (root / "module/pom.xml").write_text("<project/>", encoding="utf-8")
            for name in (
                "module-0.1.0-SNAPSHOT.jar",
                "module-0.1.0-SNAPSHOT-sources.jar",
                "module-0.1.0-SNAPSHOT-javadoc.jar",
            ):
                (root / "module/target" / name).write_bytes(name.encode())
            descriptors = json.dumps(
                [
                    {
                        "groupId": "ch.so.agi",
                        "artifactId": "parent",
                        "packaging": "pom",
                        "fileGlob": "pom.xml",
                        "pomFile": "pom.xml",
                    },
                    {
                        "groupId": "ch.so.agi",
                        "artifactId": "module",
                        "packaging": "jar",
                        "fileGlob": "module/target/*-SNAPSHOT.jar",
                        "pomFile": "module/pom.xml",
                        "classifiers": [
                            {"classifier": "sources", "fileGlob": "module/target/*-SNAPSHOT-sources.jar"},
                            {"classifier": "javadoc", "fileGlob": "module/target/*-SNAPSHOT-javadoc.jar"},
                        ],
                    },
                ]
            )
            bundle = root / "bundle"
            manifest = root / "manifest.json"
            subprocess.run(
                [
                    "python3",
                    str(BUILD),
                    "--artifacts-json",
                    descriptors,
                    "--root",
                    str(root),
                    "--bundle-dir",
                    str(bundle),
                    "--version",
                    "0.1.0-SNAPSHOT",
                    "--repository",
                    "example/repo",
                    "--commit-sha",
                    "abc123",
                    "--hop-version",
                    "2.19.0",
                    "--output",
                    str(manifest),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    "python3",
                    str(VALIDATE),
                    "--manifest",
                    str(manifest),
                    "--bundle-dir",
                    str(bundle),
                    "--artifacts-json",
                    descriptors,
                    "--repository",
                    "example/repo",
                    "--commit-sha",
                    "abc123",
                    "--version",
                    "0.1.0-SNAPSHOT",
                    "--hop-version",
                    "2.19.0",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

    def test_rejects_changed_bundle_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "target").mkdir()
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            (root / "target/module.jar").write_bytes(b"before")
            descriptors = json.dumps(
                [
                    {
                        "groupId": "ch.so.agi",
                        "artifactId": "module",
                        "packaging": "jar",
                        "fileGlob": "target/module.jar",
                        "pomFile": "pom.xml",
                    }
                ]
            )
            bundle = root / "bundle"
            manifest = root / "manifest.json"
            subprocess.run(
                [
                    "python3",
                    str(BUILD),
                    "--artifacts-json",
                    descriptors,
                    "--root",
                    str(root),
                    "--bundle-dir",
                    str(bundle),
                    "--version",
                    "0.1.0-SNAPSHOT",
                    "--repository",
                    "example/repo",
                    "--commit-sha",
                    "abc123",
                    "--hop-version",
                    "2.19.0",
                    "--output",
                    str(manifest),
                ],
                check=True,
            )
            (bundle / "artifacts/module/main").write_bytes(b"after")
            result = subprocess.run(
                [
                    "python3",
                    str(VALIDATE),
                    "--manifest",
                    str(manifest),
                    "--bundle-dir",
                    str(bundle),
                    "--artifacts-json",
                    descriptors,
                    "--repository",
                    "example/repo",
                    "--commit-sha",
                    "abc123",
                    "--version",
                    "0.1.0-SNAPSHOT",
                    "--hop-version",
                    "2.19.0",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
