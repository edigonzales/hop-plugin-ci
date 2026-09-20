# __REPOSITORY_NAME__

__DESCRIPTION__

## Features

- Describe the user-visible plugin features.

## Requirements

- Apache Hop and Java versions.
- Required companion plugins or services.

## Install

Download the plugin ZIP from the project publication repository and extract it
into the Apache Hop installation. Document the exact installation path:
`__PLUGIN_ROOT__`.

## Documentation

- Rendered handbook: add the published URL.
- Canonical source: [`docs/master.adoc`](docs/master.adoc)
- Examples: [`examples/README.md`](examples/README.md)
- Local Biblios configuration: [`docs/biblios.yml`](docs/biblios.yml)

## Build and development

See [`AGENTS.md`](AGENTS.md) for the pinned CI helper revision, Maven settings,
verification commands, package checks and end-to-end prerequisites.

## Modules and artifacts

Describe the Maven modules and the installable artifact produced under
`assemblies/`.

## CI and publication

Pull requests run verification. Publication uses the canonical artifact from
the shared `hop-plugin-ci` workflows after package and applicable E2E checks
pass.

## License

See [LICENSE](LICENSE).
