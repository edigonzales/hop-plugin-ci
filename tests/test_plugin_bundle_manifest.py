from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_plugin_bundle_manifest.py"
VALIDATE = ROOT / "scripts" / "validate_plugin_bundle_manifest.py"


class PluginBundleManifestTest(unittest.TestCase):
    descriptors = [
        {
            "artifactId": "hop-action-demo",
            "zipGlob": "action/hop-action-demo-1.2.3-SNAPSHOT.zip",
            "pluginRoot": "plugins/actions/demo",
        },
        {
            "artifactId": "hop-transform-demo",
            "zipGlob": "transform/hop-transform-demo-1.2.3-SNAPSHOT.zip",
            "pluginRoot": "plugins/transforms/demo",
        },
    ]

    def make_zip(self, directory: Path, relative: str, root: str) -> Path:
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(f"{root}/plugin.jar", b"plugin")
        return path

    def run_builder(self, directory: Path, descriptors: list[dict]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(BUILD),
                "--artifacts-json",
                json.dumps(descriptors),
                "--root",
                str(directory),
                "--bundle-dir",
                str(directory / "bundle"),
                "--version",
                "1.2.3-SNAPSHOT",
                "--repository",
                "example/demo",
                "--commit-sha",
                "abc123",
                "--group-id",
                "ch.so.agi",
                "--hop-version",
                "2.19.0",
                "--output",
                str(directory / "manifest.json"),
            ],
            capture_output=True,
            text=True,
        )

    def build(self, directory: Path, descriptors: list[dict] | None = None) -> Path:
        descriptors = descriptors or self.descriptors
        for descriptor in descriptors:
            self.make_zip(directory, descriptor["zipGlob"], descriptor["pluginRoot"])
        bundle = directory / "bundle"
        result = self.run_builder(directory, descriptors)
        self.assertEqual(result.returncode, 0, result.stderr)
        shutil.copy2(bundle / "manifest.json", bundle / "demo-canonical.manifest.json")
        return bundle

    def validate(self, bundle: Path, kind: str = "snapshot") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(VALIDATE),
                "--manifest",
                str(bundle / "demo-canonical.manifest.json"),
                "--bundle-dir",
                str(bundle),
                "--artifacts-json",
                json.dumps(self.descriptors),
                "--repository",
                "example/demo",
                "--commit-sha",
                "abc123",
                "--group-id",
                "ch.so.agi",
                "--version",
                "1.2.3-SNAPSHOT",
                "--hop-version",
                "2.19.0",
                "--repository-kind",
                kind,
                "--tag-prefix",
                "v",
                "--git-ref",
                "refs/heads/main",
            ],
            capture_output=True,
            text=True,
        )

    def test_build_and_validate_two_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = self.build(Path(temp))
            result = self.validate(bundle)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((bundle / "manifest.json").read_text())
            self.assertEqual(manifest["schemaVersion"], 2)
            self.assertEqual(len(manifest["artifacts"]), 2)
            self.assertTrue((bundle / "artifacts/hop-action-demo/hop-action-demo.pom").is_file())

    def test_validation_rejects_changed_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = self.build(Path(temp))
            zip_path = bundle / "artifacts/hop-action-demo/hop-action-demo-1.2.3-SNAPSHOT.zip"
            with zipfile.ZipFile(zip_path, "a") as archive:
                archive.writestr("plugins/actions/demo/changed.txt", b"changed")
            result = self.validate(bundle)
            self.assertNotEqual(result.returncode, 0)

    def test_snapshot_cannot_publish_to_release_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = self.build(Path(temp))
            result = self.validate(bundle, kind="release")
            self.assertNotEqual(result.returncode, 0)

    def test_build_rejects_wrong_zip_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            descriptor = {
                "artifactId": "hop-action-demo",
                "zipGlob": "action/wrong-name.zip",
                "pluginRoot": "plugins/actions/demo",
            }
            self.make_zip(directory, descriptor["zipGlob"], descriptor["pluginRoot"])
            result = self.run_builder(directory, [descriptor])
            self.assertNotEqual(result.returncode, 0)

    def test_build_rejects_missing_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            descriptor = {
                "artifactId": "hop-action-demo",
                "zipGlob": "action/hop-action-demo-1.2.3-SNAPSHOT.zip",
                "pluginRoot": "plugins/actions/demo",
            }
            result = self.run_builder(Path(temp), [descriptor])
            self.assertNotEqual(result.returncode, 0)

    def test_build_rejects_duplicate_zip_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            descriptor = {
                "artifactId": "hop-action-demo",
                "zipGlob": "action/hop-action-demo-1.2.3-SNAPSHOT*.zip",
                "pluginRoot": "plugins/actions/demo",
            }
            self.make_zip(directory, "action/hop-action-demo-1.2.3-SNAPSHOT.zip", descriptor["pluginRoot"])
            self.make_zip(directory, "action/hop-action-demo-1.2.3-SNAPSHOT-extra.zip", descriptor["pluginRoot"])
            result = self.run_builder(directory, [descriptor])
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
