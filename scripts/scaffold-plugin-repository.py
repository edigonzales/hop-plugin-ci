#!/usr/bin/env python3
"""Create a new repository from the versioned plugin repository template."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


TOKEN_RE = re.compile(r"__([A-Z0-9_]+)__")


def _safe_name(value: str, label: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", value):
        raise SystemExit(f"{label} must use lowercase letters, digits, dots, hyphens or underscores")
    return value


def _render_file(source: Path, destination: Path, values: dict[str, str]) -> None:
    data = source.read_text(encoding="utf-8")
    data = TOKEN_RE.sub(lambda match: values.get(match.group(1), match.group(0)), data)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(data, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="destination directory")
    parser.add_argument("--repository-name", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--group-id", default="ch.so.agi")
    parser.add_argument("--artifact-id")
    parser.add_argument("--plugin-id")
    parser.add_argument("--plugin-root", required=True, help="Hop installation path, e.g. plugins/transforms/example")
    parser.add_argument("--force", action="store_true", help="allow an existing empty destination")
    args = parser.parse_args(argv)

    repository_name = _safe_name(args.repository_name, "repository-name")
    artifact_id = _safe_name(args.artifact_id or repository_name, "artifact-id")
    plugin_id = _safe_name(args.plugin_id or artifact_id, "plugin-id")
    if not args.group_id or any(part == "" for part in args.group_id.split(".")):
        raise SystemExit("group-id must be a non-empty Maven coordinate")
    if not args.description.strip():
        raise SystemExit("description must not be empty")
    if not args.plugin_root.strip() or args.plugin_root.startswith("/"):
        raise SystemExit("plugin-root must be a non-empty relative Hop installation path")

    template = Path(__file__).resolve().parents[1] / "templates/plugin-repository"
    if not template.is_dir():
        raise SystemExit(f"template directory does not exist: {template}")
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"destination is not empty (use a new directory or --force): {output}")
    output.mkdir(parents=True, exist_ok=True)

    values = {
        "REPOSITORY_NAME": repository_name,
        "DESCRIPTION": args.description.strip(),
        "GROUP_ID": args.group_id,
        "ARTIFACT_ID": artifact_id,
        "PLUGIN_ID": plugin_id,
        "PLUGIN_ROOT": args.plugin_root.strip(),
    }
    for source in sorted(path for path in template.rglob("*") if path.is_file()):
        relative = source.relative_to(template)
        _render_file(source, output / relative, values)
    print(f"Created plugin repository scaffold at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
