from __future__ import annotations

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from download_maven_artifact import artifact_coordinate  # noqa: E402


class MavenArtifactDownloaderTest(unittest.TestCase):
    def test_builds_zip_coordinate(self) -> None:
        self.assertEqual(
            artifact_coordinate(
                "ch.so.agi",
                "hop-geometry-type-plugin",
                "0.2.0-SNAPSHOT",
                "zip",
            ),
            "ch.so.agi:hop-geometry-type-plugin:0.2.0-SNAPSHOT:zip",
        )

    def test_builds_classified_coordinate(self) -> None:
        self.assertEqual(
            artifact_coordinate("g", "a", "1-SNAPSHOT", "jar", "tests"),
            "g:a:1-SNAPSHOT:tests:jar",
        )


if __name__ == "__main__":
    unittest.main()
