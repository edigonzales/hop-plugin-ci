from __future__ import annotations

from pathlib import Path
import sys
import unittest
from io import BytesIO
from tempfile import TemporaryDirectory
from zipfile import ZipFile


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from resolve_maven_snapshot import coordinate_url, resolve_version  # noqa: E402
from install_maven_jar_from_zip import (  # noqa: E402
    find_jar,
    install_in_local_repository,
    write_pom,
)


class SnapshotResolverTest(unittest.TestCase):
    def metadata(self, values: str) -> bytes:
        return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<metadata>
  <groupId>ch.so.agi</groupId>
  <artifactId>hop-demo-plugin</artifactId>
  <version>1.2.3-SNAPSHOT</version>
  <versioning><snapshotVersions>{values}</snapshotVersions></versioning>
</metadata>""".encode()

    def test_resolves_one_unclassified_zip(self) -> None:
        metadata = self.metadata(
            "<snapshotVersion><extension>zip</extension>"
            "<value>1.2.3-20260910.120000-4</value></snapshotVersion>"
        )
        self.assertEqual(
            resolve_version(metadata, "ch.so.agi", "hop-demo-plugin", "1.2.3-SNAPSHOT", "zip"),
            "1.2.3-20260910.120000-4",
        )

    def test_rejects_multiple_unclassified_zips(self) -> None:
        metadata = self.metadata(
            "<snapshotVersion><extension>zip</extension><value>a</value></snapshotVersion>"
            "<snapshotVersion><extension>zip</extension><value>b</value></snapshotVersion>"
        )
        with self.assertRaises(ValueError):
            resolve_version(metadata, "ch.so.agi", "hop-demo-plugin", "1.2.3-SNAPSHOT", "zip")

    def test_rejects_classified_zip(self) -> None:
        metadata = self.metadata(
            "<snapshotVersion><extension>zip</extension><classifier>sources</classifier>"
            "<value>1.2.3-20260910.120000-4</value></snapshotVersion>"
        )
        with self.assertRaises(ValueError):
            resolve_version(metadata, "ch.so.agi", "hop-demo-plugin", "1.2.3-SNAPSHOT", "zip")

    def test_builds_maven_coordinate_url(self) -> None:
        self.assertEqual(
            coordinate_url(
                "https://jars.interlis.guru/snapshots",
                "ch.so.agi",
                "hop-geometry-type",
                "0.2.0-SNAPSHOT",
            ),
            "https://jars.interlis.guru/snapshots/ch/so/agi/hop-geometry-type/0.2.0-SNAPSHOT",
        )

    def test_requires_one_runtime_jar(self) -> None:
        buffer = BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr("plugins/misc/hop-geometry-type/hop-geometry-type.jar", b"jar")
        with ZipFile(BytesIO(buffer.getvalue())) as archive:
            self.assertEqual(
                find_jar(archive, "plugins/misc/hop-geometry-type/*.jar"),
                "plugins/misc/hop-geometry-type/hop-geometry-type.jar",
            )

    def test_writes_standalone_exact_version_pom(self) -> None:
        with TemporaryDirectory() as temporary:
            pom = Path(temporary) / "dependency.pom"
            write_pom(pom, "ch.so.agi", "hop-geometry-type", "0.2.0-20260910.194652-5")
            contents = pom.read_text(encoding="utf-8")
            self.assertIn("<groupId>ch.so.agi</groupId>", contents)
            self.assertIn("<artifactId>hop-geometry-type</artifactId>", contents)
            self.assertIn("<version>0.2.0-20260910.194652-5</version>", contents)

    def test_installs_exact_coordinate_without_embedded_snapshot_version(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_jar = root / "hop-geometry-type-0.2.0-SNAPSHOT.jar"
            source_jar.write_bytes(b"jar")
            installed = install_in_local_repository(
                source_jar,
                root / "repository",
                "ch.so.agi",
                "hop-geometry-type",
                "0.2.0-20260910.194652-5",
            )
            self.assertEqual(
                installed,
                root
                / "repository"
                / "ch"
                / "so"
                / "agi"
                / "hop-geometry-type"
                / "0.2.0-20260910.194652-5"
                / "hop-geometry-type-0.2.0-20260910.194652-5.jar",
            )
            self.assertTrue(installed.with_suffix(".pom").is_file())


if __name__ == "__main__":
    unittest.main()
