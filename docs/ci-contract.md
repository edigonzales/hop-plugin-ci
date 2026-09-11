# CI and test contract

This is the shared CI contract for Apache Hop plugins and Maven libraries using
`edigonzales/hop-plugin-ci`. Read it before changing pipelines or test setup.
Caller repositories keep their concrete commands and prerequisites in `AGENTS.md`.

## Authority and versions

This document describes the workflows in the same revision of this repository.
The [plugin verify](../.github/workflows/plugin-verify.yml),
[plugin publish](../.github/workflows/plugin-publish.yml),
[library verify](../.github/workflows/maven-library-verify.yml), and
[library publish](../.github/workflows/maven-library-publish.yml) files define
exact `workflow_call` inputs, defaults and outputs.

The shared documentation link follows `main`; it does not upgrade callers.
For a pinned caller, inspect its `uses` revision and helper `ci-ref` before using
an interface described here. Keep those references aligned when deliberately
upgrading. Existing callers use both commit pins and `main`; this documentation
introduces no pinning migration.

## Build and test responsibilities

The caller selects the Java/OS matrix and supplies project-specific preparation,
Maven arguments, package checks and applicable E2E tests. Both reusable verify
workflows require the canonical OS and Java version to be present in the matrix.
Only that cell uploads the publishable bundle as `<artifact-name-prefix>-canonical`
and exposes that name through `canonical-artifact-name`. Other cells run the
compatibility goals, without uploading competing publication bundles.

| Setting | Plugin default | Library default |
| --- | --- | --- |
| Canonical OS / Java | `ubuntu-latest` / `21` | `ubuntu-latest` / `21` |
| Working directory | `.` | `.` |
| Maven options | `-U -B -ntp` | `-U -B -ntp` |
| Canonical goals | `clean verify` | `clean package` |
| Compatibility goals | `clean test` | `clean test` |

These are configurable defaults, not a fixed organization-wide matrix or a
requirement that libraries use `verify`. Current callers generally test Java 21
and 25 on Linux, macOS and Windows, with different runner labels. Both workflows
retain Surefire/Failsafe reports, including after failures. Linux library builds
use `xvfb-run`; plugin builds use it when available.

Plugin `validation-commands` is a JSON array of caller-owned commands, run in the
Maven working directory after the canonical build and before manifest creation.
It defaults to an empty array. The library workflow has no equivalent input.
A failing build or validation command fails verification.

Installed-plugin tests belong to the caller. For separate E2E jobs, download the
exact canonical artifact and install it into an isolated test environment; do not
rebuild the candidate. Publication must depend on successful verification and the
caller's applicable E2E jobs. Some callers run packaged-plugin E2E directly in
`validation-commands`; they test the ZIPs subsequently bundled by the workflow.

## Plugin bundles

With empty `zip-descriptors` (the default), the legacy single-ZIP contract uses
`zip-glob`, `artifact-id` and `plugin-root`. Exactly one ZIP must match. The
schema-version 1 manifest records ZIP identity, provenance and SHA-256; publication
checks the ZIP and its expected repository, commit, version and installation root.

With `zip-descriptors`, pass a JSON array of objects containing `artifactId`,
`zipGlob` and `pluginRoot`, plus the shared `group-id` and `hop-version` inputs.
This also supports a one-element array. Each descriptor identifies one ZIP.
The schema-version 2 bundle contains a generated, coordinate-matching
`packaging=zip` POM for each ZIP, with ZIP and POM hashes. Pass matching descriptors
to publication, which validates the bundle before deploying it.

`additional-verified-files` copies explicitly declared files, such as a parent
POM, into the legacy upload using their basenames. It cannot be combined with
nonempty `zip-descriptors`. Despite the input name, these extra files are not
covered by the legacy ZIP manifest's hash. Avoid basename collisions.

`extra-maven-artifacts` on plugin publication accepts already-built files using
`file`, `pom-file` and `packaging`. The caller must make those paths available in
the downloaded bundle or checkout. They are deployed before the ZIP, without a
build; they do not gain library-style manifest validation through this input.
Legacy ZIP deployment uses the caller's `pom-file`, whereas schema-version 2 uses
the generated POMs in the verified bundle.

After multi-ZIP publication, the workflow resolves each base Maven ZIP coordinate
into a fresh local repository and compares downloaded bytes with the bundle.
This post-publication check is not performed by the legacy single-ZIP path.

## Maven library bundles

Libraries without installable Hop ZIPs use the library workflow pair. The caller
passes matching `artifact-descriptors` to verify and publish: main file glob,
POM, Maven coordinates, packaging, and optional classifier files. The canonical
bundle collects the declared parent POMs, JARs, POMs and classifiers with SHA-256
hashes. Publication validates the manifest and declared artifacts against the
caller repository, commit, version and Hop version, then deploys the collected
files with `deploy-file`, without rebuilding.

The library publish workflow currently supports **snapshots only** and requires
a `-SNAPSHOT` POM version. `post-publish-commands` is an optional JSON command
array run from the caller checkout after deployment. These commands validate
published artifacts; they are not ordinary local pre-publication tests.

## Maven resolution and publication

Verify builds use generated settings from
[`write_maven_settings.py`](../scripts/write_maven_settings.py), enabling Maven
Central, `https://jars.interlis.ch/` and
`https://jars.interlis.guru/snapshots/`. Build options default to `-U -B -ntp`;
helper metadata queries do not all use the same flags.

Snapshot consumers declare normal base `-SNAPSHOT` coordinates in their POMs.
Maven resolves the current timestamped version through repository metadata.
For ZIP consumers, [`download_maven_artifact.py`](../scripts/download_maven_artifact.py)
uses Maven resolution and copies the artifact to a caller-selected path.
[`resolve_maven_snapshot.py`](../scripts/resolve_maven_snapshot.py) remains an
explicit lock-file/distribution tool, not the default dependency mechanism.
The plugin workflow can also install a declared dependency JAR from a downloaded
ZIP into its local Maven repository before building.

Plugin publication supports snapshots at `https://jars.interlis.guru/snapshots/`
and releases at `https://jars.interlis.guru/releases/`. Snapshot publication
requires a `-SNAPSHOT` version; release publication requires a non-snapshot version
and matching version tag, with configurable prefix `v` by default.

Both publish workflows reject pull-request events and require `MAVEN_USERNAME`
and `MAVEN_PASSWORD` secrets. Callers map their protected repository secrets to
these names. The caller's event filters and job conditions restrict publication
to its intended branch/tag: the shared publish job alone does not enforce `main`.
Existing snapshot callers include main pushes and, in some repos, manual runs on
main. Separate release callers use version tags. Preserve each caller's current
event gates and verification dependencies.

## Existing caller differences

- INTERLIS and Vector/Raster use a pinned single-ZIP workflow and separate real
  Hop E2E jobs; their compatibility goals are `test`.
- Geometry Type has a custom canonical build with PostGIS, script tests and
  distribution validation, plus a separate compatibility matrix. It uses pinned
  helpers and plugin publication, carrying shared Geometry JAR/POM files too.
- Commons uses pinned library workflows, `clean package`, and Ubuntu 24.04 as its
  canonical runner, followed by a public snapshot consumer check.
- ili2db and ilivalidator use `main`, action/transform ZIP descriptors, and package
  checks plus E2E scripts inside canonical validation.
- Geometry Inspector uses `main` and a one-element ZIP descriptor array. It builds
  its Geometry dependency separately and tests installed plugin classloaders in
  a separate Maven job; that is distinct from executing pipelines via `hop-run`.

These describe the current local caller setups, including ongoing caller work;
they are not requirements to migrate other repos. Consult the caller workflows
and its root instructions for exact revisions, commands and prerequisites.

## Local use and onboarding

To reproduce a verify build, use the caller's JDK, goals and extra arguments.
Set `HOP_CI_DIR` to an absolute checkout path of `hop-plugin-ci` at the caller's
helper revision (CI checks it out under `.ci/hop-plugin-ci`). From the caller
repository root, prepare a temporary settings file:

```bash
CI_TEST_TMP="$(mktemp -d)"
export MAVEN_SETTINGS="$CI_TEST_TMP/maven-settings.xml"
python3 "$HOP_CI_DIR/scripts/write_maven_settings.py" --output "$MAVEN_SETTINGS"
```

Then run the commands in that caller's `AGENTS.md`. Use Python 3, Maven and the
selected JDK; on headless Linux use a virtual display for SWT tests. Use disposable
Hop installations for scripts that install ZIPs. Local builds exercise local
outputs; a CI publication candidate must still use the canonical CI artifact.

Copy and complete this entry in a new caller's root `AGENTS.md`:

```md
## CI and tests

Before changing pipelines or test setup, read the
[shared CI contract](https://github.com/edigonzales/hop-plugin-ci/blob/main/docs/ci-contract.md).
Use the interfaces at this repo's workflow and helper revisions; the documentation
link follows main and does not upgrade those revisions.

Run commands from the repository root. Document here:
- JDK/tool/service prerequisites and Maven settings preparation;
- exact canonical and compatibility test commands;
- package checks and any installed-plugin tests, including ZIP paths and variables;
- the local workflow entrypoints and any post-publication checks.
```

When changing shared behavior, update this contract with the workflow change.
Publish the central document before rolling out remote links in caller repos.
