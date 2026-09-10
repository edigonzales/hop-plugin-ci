# hop-plugin-ci

Reusable GitHub Actions workflows for Apache Hop plugins.

## Contract

The caller repository keeps plugin-specific preparation and installed-Hop E2E
tests. This repository provides the common build contract:

1. `plugin-verify.yml` runs the requested Java/OS matrix, validates exactly one
   packaged ZIP, and uploads it with a SHA-256 manifest. The Ubuntu/Java 21
   matrix cell is the canonical build; compatibility cells run tests without
   creating competing ZIPs.
2. A caller-specific E2E job consumes that exact artifact.
3. `plugin-publish.yml` downloads the same artifact, validates the manifest and
   version/tag relationship, and publishes the ZIP without rebuilding.
   Callers may additionally pass already-built Maven JAR/POM files when the
   plugin has a shared runtime library that downstream plugins compile against.

All verification Maven invocations use `-U -B -ntp` and the generated settings
file. It enables the shared Maven Central, `jars.interlis.ch`, and
`jars.interlis.guru/snapshots` repositories. Snapshot consumers should use
`scripts/resolve_maven_snapshot.py` when an exact timestamped ZIP must be
installed into a later E2E job.

The Maven repositories are:

- snapshots: `https://jars.interlis.guru/snapshots/`
- releases: `https://jars.interlis.guru/releases/`

The publish workflow expects the caller to pass `MAVEN_USERNAME` and
`MAVEN_PASSWORD` as protected secrets. Pull requests must only call the verify
workflow; publication is reserved for main pushes and version tags.

See `.github/workflows/plugin-verify.yml` and
`.github/workflows/plugin-publish.yml` for the complete `workflow_call`
interface.
