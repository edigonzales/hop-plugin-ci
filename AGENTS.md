# Repository instructions

Read the [CI contract](docs/ci-contract.md) before changing the shared
workflows. Check callers at their actual workflow and helper revisions.

Run `actionlint` and `python3 -m unittest discover -s tests -v` locally.
For publication changes, exercise Maven deployment against a temporary
file-based repository and check the resulting coordinates and bytes.
Installed-plugin tests belong in the caller repositories.
