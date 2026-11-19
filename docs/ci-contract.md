# Shared CI for Hop plugins and Maven libraries

Pin the reusable workflow to a commit. It checks out the helpers from that
same commit using the GitHub Actions job context.

## Verify

The caller chooses the Java and OS matrix. Include the canonical Java and
runner in it. The canonical cell runs `clean verify` by default. The other
cells run `clean test`. Use `maven-goals` and `compatibility-goals` to select
the project's lifecycle goals.

`pom-file` points to a reactor or module POM with the publication version.
`artifacts` is a JSON array. Paths are relative to the Maven working directory
and each file pattern must match one file. Use one entry per Maven coordinate.

- `{"file":"assemblies/target/example-*.zip"}` uses the project group and
  version and the ZIP name `<artifactId>-<version>.zip`. The workflow supplies
  a minimal Maven POM.
- `{"file":"assemblies/target/example-*.zip","pom":"assemblies/pom.xml"}`
  publishes the ZIP together with its existing Maven POM.
- `{"pom":"pom.xml"}` publishes a parent POM.
- `{"file":"core/target/core-*-SNAPSHOT.jar","pom":"core/pom.xml","classifiers":["sources","javadoc"]}`
  publishes a library JAR and its attached JARs. They must be beside the main
  JAR and use the corresponding `-sources.jar` and `-javadoc.jar` suffixes.

Use literal Maven versions and keep a publication set at one version. The
uploaded artifact contains the canonical ZIPs, JARs and POMs. Its name is
available as `canonical-artifact-name`. Separate installed tests download
that artifact from the same run and install the ZIP into a disposable Hop
distribution. For checks inside the canonical cell, set `validation-command`
to the Bash commands that verify the package after Maven runs.

For local reproduction with the repositories used by CI, run
`python3 "$HOP_CI_DIR/scripts/write_maven_settings.py" --output "$MAVEN_SETTINGS"`
and pass `-s "$MAVEN_SETTINGS"` to Maven. Set `HOP_CI_DIR` to the helper checkout
and `MAVEN_SETTINGS` to a temporary file. Follow the caller's JDK, service and
test setup. A caller can supply a dependency artifact from an earlier job.
Geometry Calculator and Inspector install the shared Geometry JAR from the
downloaded plugin ZIP before compiling, so their build sees the same version
as their installed tests.

## Publish

Set the publish job to depend on verification and all applicable installed
tests. Pass the verified artifact name and the Maven secrets
`MAVEN_USERNAME` and `MAVEN_PASSWORD`. The publish workflow downloads the
artifact from the current run and uses Maven `deploy-file` directly with the
caller’s Maven configuration. It publishes parent POMs before ZIPs and JARs.

Snapshots require a `-SNAPSHOT` version and a main-branch push or manual run.
Releases require a non-snapshot version and a matching tag (default
`v<version>`). Only push and manual events can publish. The caller is
responsible for its own event filters and test dependencies.
