from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_manifest.py"
VALIDATE = ROOT / "scripts" / "validate_manifest.py"


class ManifestTest(unittest.TestCase):
    def make_zip(self, directory: Path, name: str = "hop-demo-plugin-1.2.3.zip") -> Path:
        path = directory / name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("plugins/transforms/demo/plugin.jar", b"demo")
        return path

    def build_manifest(self, directory: Path, zip_path: Path, version: str = "1.2.3") -> Path:
        manifest = directory / "manifest.json"
        subprocess.run(
            [
                "python3",
                str(BUILD),
                "--zip-glob",
                zip_path.name,
                "--version",
                version,
                "--repository",
                "example/demo",
                "--commit-sha",
                "abc123",
                "--group-id",
                "ch.so.agi",
                "--artifact-id",
                "hop-demo-plugin",
                "--hop-version",
                "2.18.1",
                "--plugin-root",
                "plugins/transforms/demo",
                "--output",
                str(manifest),
            ],
            cwd=directory,
            check=True,
            capture_output=True,
            text=True,
        )
        return manifest

    def test_build_and_validate_release_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            zip_path = self.make_zip(directory)
            manifest = self.build_manifest(directory, zip_path)
            subprocess.run(
                [
                    "python3",
                    str(VALIDATE),
                    "--manifest",
                    str(manifest),
                    "--zip",
                    str(zip_path),
                    "--repository",
                    "example/demo",
                    "--commit-sha",
                    "abc123",
                    "--artifact-id",
                    "hop-demo-plugin",
                    "--version",
                    "1.2.3",
                    "--plugin-root",
                    "plugins/transforms/demo",
                    "--repository-kind",
                    "release",
                    "--tag-prefix",
                    "v",
                    "--git-ref",
                    "refs/tags/v1.2.3",
                ],
                cwd=directory,
                check=True,
                capture_output=True,
                text=True,
            )

    def test_validate_rejects_changed_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            zip_path = self.make_zip(directory)
            manifest = self.build_manifest(directory, zip_path)
            with zipfile.ZipFile(zip_path, "a") as archive:
                archive.writestr("plugins/transforms/demo/changed.txt", b"changed")
            result = subprocess.run(
                [
                    "python3",
                    str(VALIDATE),
                    "--manifest",
                    str(manifest),
                    "--zip",
                    str(zip_path),
                    "--repository",
                    "example/demo",
                    "--commit-sha",
                    "abc123",
                    "--artifact-id",
                    "hop-demo-plugin",
                    "--version",
                    "1.2.3",
                    "--plugin-root",
                    "plugins/transforms/demo",
                    "--repository-kind",
                    "release",
                    "--tag-prefix",
                    "v",
                    "--git-ref",
                    "refs/tags/v1.2.3",
                ],
                cwd=directory,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_snapshot_requires_snapshot_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            zip_path = self.make_zip(directory, "hop-demo-plugin-1.2.3-SNAPSHOT.zip")
            manifest = self.build_manifest(directory, zip_path, "1.2.3-SNAPSHOT")
            result = subprocess.run(
                [
                    "python3",
                    str(VALIDATE),
                    "--manifest",
                    str(manifest),
                    "--zip",
                    str(zip_path),
                    "--repository",
                    "example/demo",
                    "--commit-sha",
                    "abc123",
                    "--artifact-id",
                    "hop-demo-plugin",
                    "--version",
                    "1.2.3-SNAPSHOT",
                    "--plugin-root",
                    "plugins/transforms/demo",
                    "--repository-kind",
                    "release",
                    "--tag-prefix",
                    "v",
                    "--git-ref",
                    "refs/tags/v1.2.3",
                ],
                cwd=directory,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_build_rejects_wrong_zip_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            zip_path = self.make_zip(directory, "hop-demo-plugin-1.2.3-renamed.zip")
            result = subprocess.run(
                [
                    "python3",
                    str(BUILD),
                    "--zip-glob",
                    zip_path.name,
                    "--version",
                    "1.2.3",
                    "--repository",
                    "example/demo",
                    "--commit-sha",
                    "abc123",
                    "--group-id",
                    "ch.so.agi",
                    "--artifact-id",
                    "hop-demo-plugin",
                    "--hop-version",
                    "2.18.1",
                    "--plugin-root",
                    "plugins/transforms/demo",
                    "--output",
                    str(directory / "manifest.json"),
                ],
                cwd=directory,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
