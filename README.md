# hop-plugin-ci

Reusable GitHub Actions for Maven builds and publication of Apache Hop plugin
ZIPs, libraries and parent POMs.

- [Verify](.github/workflows/verify.yml) builds and tests the requested matrix and
  uploads the canonical cell's publication files.
- [Publish](.github/workflows/publish.yml) deploys those files through Maven.
- [CI contract](docs/ci-contract.md) covers caller inputs and installed tests.
