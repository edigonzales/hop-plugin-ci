# hop-plugin-ci

Reusable GitHub Actions workflows for Apache Hop plugins and Maven libraries.

Read the [CI and test contract](docs/ci-contract.md) for shared build rules,
canonical artifacts, test responsibilities, Maven resolution and publication.
The [plugin repository contract](docs/plugin-repository-contract.md) defines the
common repository, README, license and documentation shape. The CI contract also
contains local setup instructions and an `AGENTS.md` onboarding template.
Caller repositories document their concrete test commands in their root
`AGENTS.md`.

Use `templates/plugin-repository/` and
`scripts/scaffold-plugin-repository.py` for a new plugin. The scaffold creates
the contract files, Biblios entry points, example/E2E directories and workflow
skeletons; replace its placeholders with the plugin's implementation details.

## Workflows

- Plugins: [verify](.github/workflows/plugin-verify.yml) and
  [publish](.github/workflows/plugin-publish.yml).
- Maven libraries: [verify](.github/workflows/maven-library-verify.yml) and
  [publish](.github/workflows/maven-library-publish.yml).
- This repository: [self-test](.github/workflows/self-test.yml).

The workflow files define the exact callable interfaces. Consult the revision
used by the caller when working with pinned workflows.
