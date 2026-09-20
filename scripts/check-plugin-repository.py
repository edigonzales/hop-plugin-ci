#!/usr/bin/env python3
"""Validate the versioned repository contract for an Apache Hop plugin."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse


PROFILES = {"standard-plugin", "desktop-plugin", "multi-module-suite"}
REQUIRED_ROOT_FILES = ("README.md", "LICENSE", "AGENTS.md", "pom.xml")
REQUIRED_README_SECTIONS = (
    "Features",
    "Requirements",
    "Install",
    "Documentation",
    "Build and development",
    "Modules and artifacts",
    "CI and publication",
    "License",
)
LOCAL_LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ASCIIDOC_TARGET_RE = re.compile(r"(?:(?:include|image)::|xref:)([^\[\s]+)\[")
MIT_LICENSE_MARKER = "MIT License"
PARENT_ARTIFACT = "hop-plugin-parent"


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    return next((node for node in element if _strip_namespace(node.tag) == name), None)


def _text(element: ET.Element | None, name: str) -> str:
    if element is None:
        return ""
    node = _child(element, name)
    return (node.text or "").strip() if node is not None else ""


def _all_pom_parents(root: Path) -> list[tuple[Path, str, str]]:
    result = []
    for path in sorted(root.rglob("pom.xml")):
        try:
            document = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        parent = _child(document, "parent")
        if parent is not None:
            result.append((path, _text(parent, "groupId"), _text(parent, "artifactId")))
    return result


def _readme_sections(text: str) -> tuple[list[str], list[tuple[str, int]]]:
    headings = []
    level_two = []
    for index, line in enumerate(text.splitlines(), start=1):
        match = HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip().rstrip("#").strip()
        headings.append(title)
        if level == 2:
            level_two.append((title, index))
    return headings, level_two


def _check_local_links(root: Path, source: Path, text: str, errors: list[str]) -> None:
    for raw_target in LOCAL_LINK_RE.findall(text):
        target = raw_target.strip().strip("<>").split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:", "#", "data:")):
            continue
        parsed = urlparse(target)
        if parsed.scheme or target.startswith("/"):
            continue
        resolved = (source.parent / target).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{source.name}: local link escapes repository: {target}")
            continue
        if not resolved.exists():
            errors.append(f"{source.name}: broken local link: {target}")


def _check_documentation_links(root: Path, errors: list[str]) -> None:
    """Check source-relative Markdown and AsciiDoc references.

    Biblios may generate download files at build time, so ordinary AsciiDoc
    ``link:`` targets are intentionally left to the documentation build. The
    source-composition references (include/xref/image) and Markdown links are
    stable checkout links and are checked here.
    """
    docs = root / "docs"
    if not docs.is_dir():
        return
    for source in sorted(path for path in docs.rglob("*") if path.is_file()):
        text = source.read_text(encoding="utf-8", errors="replace")
        if source.suffix.lower() in {".md", ".markdown"}:
            _check_local_links(root, source, text, errors)
        if source.suffix.lower() == ".adoc":
            for target in ASCIIDOC_TARGET_RE.findall(text):
                target = target.split("#", 1)[0]
                if not target or target.startswith(("http://", "https://", "#", "{")):
                    continue
                resolved = (source.parent / target).resolve()
                try:
                    resolved.relative_to(root.resolve())
                except ValueError:
                    errors.append(f"{source}: documentation link escapes repository: {target}")
                    continue
                if not resolved.exists():
                    errors.append(f"{source}: broken documentation link: {target}")


def _check_pom(root: Path, profile: str, errors: list[str]) -> None:
    path = root / "pom.xml"
    try:
        document = ET.parse(path).getroot()
    except ET.ParseError as exc:
        errors.append(f"pom.xml is not valid XML: {exc}")
        return

    licenses = _child(document, "licenses")
    license_nodes = [] if licenses is None else [node for node in licenses if _strip_namespace(node.tag) == "license"]
    if not any("mit" in _text(node, "name").lower() for node in license_nodes):
        errors.append("pom.xml must declare the MIT license in <licenses>")

    parent = _child(document, "parent")
    if profile in {"standard-plugin", "desktop-plugin"}:
        if parent is None or _text(parent, "artifactId") != PARENT_ARTIFACT:
            errors.append("pom.xml must use the common hop-plugin-parent")
        return

    # A suite can be its own aggregator parent. Require a real aggregator and
    # module POMs with that parent instead of imposing a single-parent layout.
    packaging = _text(document, "packaging") or "jar"
    modules = _child(document, "modules")
    if packaging != "pom" or modules is None:
        errors.append("multi-module-suite root pom.xml must be a module aggregator")
    module_parents = _all_pom_parents(root)
    if not any(path != root / "pom.xml" for path, _, _ in module_parents):
        errors.append("multi-module-suite must contain module POMs with parent metadata")


def _check_docs(root: Path, profile: str, errors: list[str]) -> None:
    standard = (root / "docs/index.adoc", root / "docs/master.adoc", root / "docs/biblios.yml")
    nested = (
        root / "docs/biblios/biblios.yml",
        root / "docs/biblios/user/master.adoc",
        root / "docs/biblios/README.md",
    )
    if profile == "multi-module-suite":
        if not all(path.exists() for path in standard) and not all(path.exists() for path in nested):
            errors.append("multi-module-suite needs standard or nested Biblios entry points")
    elif not all(path.exists() for path in standard):
        errors.append("docs/index.adoc, docs/master.adoc and docs/biblios.yml are required")


def validate(root: Path, profile: str) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    if profile not in PROFILES:
        return [f"unknown profile {profile!r}; choose one of {', '.join(sorted(PROFILES))}"]

    for name in REQUIRED_ROOT_FILES:
        path = root / name
        if not path.is_file():
            errors.append(f"missing required root file: {name}")

    license_path = root / "LICENSE"
    if license_path.is_file():
        content = license_path.read_text(encoding="utf-8").strip()
        if not content:
            errors.append("LICENSE must not be empty")
        elif MIT_LICENSE_MARKER not in content[:80]:
            errors.append("LICENSE must contain the standard MIT License heading")

    readme = root / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        headings, level_two = _readme_sections(text)
        if not headings or headings[0] != root.name:
            errors.append(f"README.md must start with '# {root.name}'")
        first_body = text.split("\n", 1)[1] if "\n" in text else ""
        if not first_body.strip() or (level_two and not first_body.split("\n## ", 1)[0].strip()):
            errors.append("README.md needs a short description below its title")
        positions = []
        for section in REQUIRED_README_SECTIONS:
            matches = [line for title, line in level_two if title == section]
            if not matches:
                errors.append(f"README.md is missing required section: ## {section}")
            else:
                positions.append((section, matches[0]))
        if len(positions) == len(REQUIRED_README_SECTIONS):
            lines = [line for _, line in positions]
            if lines != sorted(lines):
                errors.append("README.md required sections are not in contract order")
            license_line = dict(positions)["License"]
            if any(line > license_line for _, line in level_two):
                errors.append("README.md License must be the final level-two section")
        if not re.search(r"\[[^\]]*LICENSE[^\]]*\]\(LICENSE(?:#[^)]*)?\)", text, re.IGNORECASE):
            errors.append("README.md must link to LICENSE with a working relative link")
        _check_local_links(root, readme, text, errors)

    agents = root / "AGENTS.md"
    if agents.is_file():
        agents_text = agents.read_text(encoding="utf-8")
        if "hop-plugin-ci/blob/main/docs/ci-contract.md" not in agents_text:
            errors.append("AGENTS.md must link to the shared CI contract")
        if "hop-plugin-ci/blob/main/docs/plugin-repository-contract.md" not in agents_text:
            errors.append("AGENTS.md must link to the plugin repository contract")

    _check_pom(root, profile, errors) if (root / "pom.xml").is_file() else None

    for directory in ("scripts", "assemblies"):
        if not (root / directory).is_dir():
            errors.append(f"missing required directory: {directory}/")
    examples = root / "examples"
    if examples.is_dir() and not (examples / "README.md").is_file():
        errors.append("examples/README.md is required when examples/ exists")
    if profile in {"standard-plugin", "desktop-plugin"} and not (root / "e2e").is_dir():
        errors.append("e2e/ is required for standard-plugin and desktop-plugin profiles")
    if profile == "multi-module-suite" and not (
        (root / "e2e").is_dir()
        or (root / "scripts/run-installed-e2e.py").is_file()
        or (root / "scripts/prepare-installed-e2e.py").is_file()
    ):
        errors.append("multi-module-suite needs e2e/ or a documented installed-E2E script")

    _check_docs(root, profile, errors)
    _check_documentation_links(root, errors)
    workflows = root / ".github/workflows"
    for name in ("verify.yml", "ci.yml", "biblios-docs.yml"):
        if not (workflows / name).is_file():
            errors.append(f"missing required workflow: .github/workflows/{name}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: cwd)")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="standard-plugin")
    args = parser.parse_args(argv)
    errors = validate(args.root, args.profile)
    if errors:
        print(f"Plugin repository contract failed for {args.root.resolve()}:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Plugin repository contract v1 OK: {args.root.resolve()} ({args.profile})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
