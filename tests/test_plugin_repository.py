from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check-plugin-repository.py"
SCAFFOLDER = ROOT / "scripts/scaffold-plugin-repository.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("plugin_repository_checker", CHECKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fixture(root: Path, *, nested_docs: bool = False) -> None:
    (root / ".github/workflows").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "assemblies").mkdir()
    (root / "examples").mkdir()
    (root / "e2e").mkdir()
    (root / "examples/README.md").write_text("# Examples\n", encoding="utf-8")
    (root / "LICENSE").write_text("MIT License\n\nCopyright (c) 2026 Stefan Ziegler\n", encoding="utf-8")
    (root / "AGENTS.md").write_text(
        "https://github.com/edigonzales/hop-plugin-ci/blob/main/docs/ci-contract.md\n"
        "https://github.com/edigonzales/hop-plugin-ci/blob/main/docs/plugin-repository-contract.md\n",
        encoding="utf-8",
    )
    (root / "pom.xml").write_text(
        """<project xmlns=\"http://maven.apache.org/POM/4.0.0\"><modelVersion>4.0.0</modelVersion>
<parent><groupId>ch.so.agi</groupId><artifactId>hop-plugin-parent</artifactId><version>1</version></parent>
<artifactId>fixture</artifactId><licenses><license><name>MIT License</name></license></licenses></project>""",
        encoding="utf-8",
    )
    for name in ("verify.yml", "ci.yml", "biblios-docs.yml"):
        (root / ".github/workflows" / name).write_text("name: test\n", encoding="utf-8")
    if nested_docs:
        (root / "docs/biblios/user").mkdir(parents=True)
        (root / "docs/biblios/biblios.yml").write_text("title: fixture\n", encoding="utf-8")
        (root / "docs/biblios/user/master.adoc").write_text("= Fixture\n", encoding="utf-8")
        (root / "docs/biblios/README.md").write_text("# Docs\n", encoding="utf-8")
    else:
        (root / "docs").mkdir()
        for name in ("index.adoc", "master.adoc", "biblios.yml"):
            (root / "docs" / name).write_text("fixture\n", encoding="utf-8")

    documentation_link = "docs/biblios/user/master.adoc" if nested_docs else "docs/master.adoc"
    (root / "README.md").write_text(
        f"""# {root.name}

Fixture plugin.

## Features

Feature.

## Requirements

Requirements.

## Install

Install.

## Documentation

[Docs]({documentation_link})

## Build and development

Build.

## Modules and artifacts

Modules.

## CI and publication

CI.

## License

See [LICENSE](LICENSE).
""",
        encoding="utf-8",
    )


class PluginRepositoryContractTest(unittest.TestCase):
    def test_standard_fixture_passes(self):
        checker = load_checker()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture-plugin"
            root.mkdir()
            write_fixture(root)
            self.assertEqual([], checker.validate(root, "standard-plugin"))

    def test_suite_accepts_nested_documentation_and_installed_e2e(self):
        checker = load_checker()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "suite-plugin"
            root.mkdir()
            write_fixture(root, nested_docs=True)
            (root / "e2e").rmdir()
            (root / "scripts/run-installed-e2e.py").write_text("# test\n", encoding="utf-8")
            pom = (root / "pom.xml").read_text(encoding="utf-8")
            pom = pom.replace(
                "<parent><groupId>ch.so.agi</groupId><artifactId>hop-plugin-parent</artifactId><version>1</version></parent>",
                "<packaging>pom</packaging><modules><module>assemblies</module></modules>",
            )
            (root / "pom.xml").write_text(pom, encoding="utf-8")
            (root / "assemblies/pom.xml").write_text(
                "<project><parent><artifactId>suite-plugin</artifactId></parent></project>", encoding="utf-8"
            )
            self.assertEqual([], checker.validate(root, "multi-module-suite"))

    def test_missing_license_link_fails(self):
        checker = load_checker()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture-plugin"
            root.mkdir()
            write_fixture(root)
            readme = (root / "README.md").read_text(encoding="utf-8").replace("See [LICENSE](LICENSE).", "MIT")
            (root / "README.md").write_text(readme, encoding="utf-8")
            errors = checker.validate(root, "standard-plugin")
            self.assertTrue(any("link to LICENSE" in error for error in errors))

    def test_broken_documentation_reference_fails(self):
        checker = load_checker()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture-plugin"
            root.mkdir()
            write_fixture(root)
            (root / "docs/master.adoc").write_text("include::missing.adoc[]\n", encoding="utf-8")
            errors = checker.validate(root, "standard-plugin")
            self.assertTrue(any("broken documentation link" in error for error in errors))

    def test_gui_mockup_contract(self):
        checker = load_checker()
        css = (ROOT / "templates/plugin-repository/docs/site.css").read_text()
        cases = [
            ("valid", "[.gui-mockup]\n----\n| Dialog |\n----\n", css, None),
            ("no GUI", "= Handbook\n", None, None),
            ("ordinary listing", "----\n[.gui-mockup]\n----\n", None, None),
            ("missing CSS", "[.gui-mockup]\n----\nGUI\n----\n", None, "missing gui-mockup stylesheet"),
            ("wrong size", "[.gui-mockup]\n----\nGUI\n----\n", css.replace("0.75em", "1em"), "font-size"),
            ("wrong spacing", "[.gui-mockup]\n----\nGUI\n----\n", css.replace("1.25", "2"), "line-height"),
            ("missing selector", "[.gui-mockup]\n----\nGUI\n----\n", css.replace("pre.gui-mockup", "pre.other"), "pre.gui-mockup"),
            ("comment only", "[.gui-mockup]\n----\nGUI\n----\n", "/* " + css[css.index(".listingblock"):] + " */", "font-size"),
            ("not closed", "[.gui-mockup]\n----\nGUI\n", css, "not closed"),
            ("no listing", "[.gui-mockup]\nGUI\n", css, "followed by"),
        ]
        for nested in (False, True):
            for name, text, styles, expected in cases:
                with self.subTest(nested=nested, case=name), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    write_fixture(root, nested_docs=nested)
                    docs = root / ("docs/biblios" if nested else "docs")
                    source = docs / ("user/master.adoc" if nested else "master.adoc")
                    source.write_text(text)
                    if styles is not None:
                        (docs / "site.css").write_text(styles)
                    errors = []
                    checker._check_gui_mockups(root, errors)
                    if expected is None:
                        self.assertEqual([], errors)
                    else:
                        self.assertTrue(any(expected in error for error in errors), errors)

    def test_scaffold_passes_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "my-plugin"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCAFFOLDER),
                    "--output",
                    str(destination),
                    "--repository-name",
                    "my-plugin",
                    "--description",
                    "A fixture plugin.",
                    "--group-id",
                    "example.org",
                    "--plugin-id",
                    "my-plugin",
                    "--plugin-root",
                    "plugins/transforms/my-plugin",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            check = subprocess.run(
                [
                    sys.executable,
                    str(CHECKER),
                    "--root",
                    str(destination),
                    "--profile",
                    "standard-plugin",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, check.returncode, check.stderr)


if __name__ == "__main__":
    unittest.main()
