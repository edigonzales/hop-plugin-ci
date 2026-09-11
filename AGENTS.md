# Repository instructions

## CI and tests

Read [the CI and test contract](docs/ci-contract.md) before changing pipelines,
helper scripts or test setup. Update the contract when shared behavior changes;
keep the README as an overview rather than duplicating the rules.

Run checks from this repository root. The existing self-test workflow uses
Python 3.12 and Actionlint:

```bash
python3 -m unittest discover -s tests -v
actionlint
```

For executable changes, run the relevant existing checks. For documentation-only
changes, verify commands and links against their source files and run
`git diff --check`; no full caller Maven/E2E runs are needed. Report which checks
were actually executed. Caller-specific setup and E2E remain in caller repos.
