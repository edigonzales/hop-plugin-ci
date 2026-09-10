#!/usr/bin/env python3
"""Run trusted validation commands supplied by a caller workflow."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commands-json", required=True)
    args = parser.parse_args()
    commands = json.loads(args.commands_json)
    if not isinstance(commands, list) or not all(isinstance(command, str) for command in commands):
        raise SystemExit("validation-commands must be a JSON array of strings")
    for command in commands:
        print(f"==> {command}", flush=True)
        subprocess.run(command, shell=True, check=True, cwd=Path.cwd(), env=os.environ.copy())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
