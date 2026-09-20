# Repository instructions

Before changing pipelines or test setup, read the
[shared CI contract](https://github.com/edigonzales/hop-plugin-ci/blob/main/docs/ci-contract.md)
and the
[plugin repository contract](https://github.com/edigonzales/hop-plugin-ci/blob/main/docs/plugin-repository-contract.md).
Keep the workflow and `ci-ref` revisions documented here aligned with the
repository's actual workflows.

## CI and tests

Run from the repository root with Python 3, Maven and JDK 21. Use the helper
checkout selected by the workflow to create Maven settings, then run the
canonical verify command, package validation and the applicable installed-plugin
or E2E checks. Use JDK 25 for compatibility jobs where configured.

The repository contract check is run by CI with the `standard-plugin` profile.
Update this file with concrete commands and disposable test paths when the
plugin is implemented.
