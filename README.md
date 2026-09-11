# hop-plugin-ci

Reusable GitHub Actions workflows for Apache Hop plugins and Maven libraries.

Read the [CI and test contract](docs/ci-contract.md) for shared build rules,
canonical artifacts, test responsibilities, Maven resolution and publication.
It also contains local setup instructions and an `AGENTS.md` onboarding template.
Caller repositories document their concrete test commands in their root
`AGENTS.md`.

## Workflows

- Plugins: [verify](.github/workflows/plugin-verify.yml) and
  [publish](.github/workflows/plugin-publish.yml).
- Maven libraries: [verify](.github/workflows/maven-library-verify.yml) and
  [publish](.github/workflows/maven-library-publish.yml).
- This repository: [self-test](.github/workflows/self-test.yml).

The workflow files define the exact callable interfaces. Consult the revision
used by the caller when working with pinned workflows.
