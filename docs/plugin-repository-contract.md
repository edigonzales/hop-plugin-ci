# Plugin Repository Contract v1

This document defines the repository-level standard for Apache Hop plugin
repositories that use `edigonzales/hop-plugin-ci`. It complements the
[CI and test contract](ci-contract.md): this document governs repository
shape, documentation entry points and metadata, while the CI contract governs
workflow interfaces and verification responsibilities.

## Required root files

Every plugin repository has these files at its root:

- `README.md`
- `LICENSE` (exactly this spelling)
- `AGENTS.md`
- `pom.xml`

The root README is the short orientation document. Detailed user and developer
material belongs in the documentation tree.

## Standard repository structure

The conventional directories are:

```text
docs/       Biblios sources and developer documentation
examples/   Runnable or directly openable user examples
e2e/        Installed-plugin and end-to-end scenarios
scripts/    Repository validation, packaging and local-development helpers
assemblies/ Maven modules that create installable plugin ZIPs
```

`examples/` and `e2e/` may be omitted only when the plugin genuinely has no
examples or installed-plugin scenarios. If `examples/` exists, it must contain
`examples/README.md`. A suite may keep an intentionally different internal
layout when its profile documents the equivalent entry points.

## README contract

The README uses this order. The short description follows the title; the
required headings must remain in this order, although project-specific
subsections may appear within a section.

```text
# repository-name
Short description
## Features
## Requirements
## Install
## Documentation
## Build and development
## Modules and artifacts
## CI and publication
## License
```

The title is the repository name, not a product slogan. The License section is
the final level-two section and contains a working relative link to `LICENSE`.
All other relative README and documentation links must resolve in the checkout.

## Documentation and Biblios

The standard documentation entry points are:

- `docs/index.adoc`
- `docs/master.adoc`
- `docs/biblios.yml`

The Biblios workflow builds the exact checkout, validates documentation and
publishes the configured site only from the repository's publication branch.
The README links to the rendered handbook, the canonical source entry point,
examples and the local documentation build command.

The `multi-module-suite` profile may retain a nested layout such as
`docs/biblios/biblios.yml` and `docs/biblios/user/master.adoc`. The repository
must still expose those paths in its README and provide a documentation
workflow. This is a supported variant, not an excuse to omit documentation
entry points.

## Profiles

The reusable checker supports these profiles:

- `standard-plugin`: a normal transform or library-backed plugin with the
  standard root Biblios layout and the common Hop plugin parent.
- `desktop-plugin`: a desktop/SWT plugin. It follows the same root contract,
  but may document installed UI and classloader tests in `e2e/` or its
  integration-test module.
- `multi-module-suite`: a suite with an aggregator POM, several feature
  modules, or a nested documentation tree. The aggregator may be the suite's
  own parent; module structure, license metadata and the suite's documented
  documentation entry points are checked instead.

Profiles change only structural allowances. They do not weaken the README,
license, AGENTS, workflow or link requirements.

## License and Maven metadata

The repository uses an MIT license. `LICENSE` must be non-empty and begin with
the standard `MIT License` notice, including the project copyright line. The
README uses `See [LICENSE](LICENSE).` (or equivalent wording with that working
link). The root POM declares the MIT license in `<licenses>` so published Maven
metadata carries the same information.

## Build, package and E2E requirements

The repository provides:

- a `verify.yml` workflow that invokes the shared verification contract;
- a `ci.yml` workflow for pull requests and the main branch;
- a Biblios documentation workflow;
- Maven verification and package checks appropriate to the plugin;
- installed-plugin or end-to-end checks when the plugin produces an installable
  ZIP or has runtime integration behavior.

Caller workflows keep their existing `uses` and `ci-ref` revisions until a
deliberate shared-CI upgrade. The contract check is added as a
`validation-commands` command and therefore runs in the canonical verification
cell without silently changing those pins. If a pinned helper revision predates
the checker, the caller may use a dedicated contract job that checks out the
central checker at its documented contract revision; this keeps the build pin
unchanged while still enforcing the repository contract.

The check is run from the repository root, for example:

```bash
python3 .ci/hop-plugin-ci/scripts/check-plugin-repository.py \
  --profile standard-plugin
```

## AGENTS.md onboarding

`AGENTS.md` names both this repository contract and the shared CI contract. It
records the actual workflow/helper revision, prerequisites, Maven settings,
canonical package checks, compatibility commands, installed-plugin tests and
documentation commands. New repositories should start from the versioned
scaffold in `templates/plugin-repository/` and then replace its placeholders.

## Versioning

This document is **Plugin Repository Contract v1**. Changes that tighten
required files or section order require a new contract version or an explicit
migration note. Project-specific profiles may add requirements, but may not
remove the common root, README, license, AGENTS, workflow or link guarantees.
