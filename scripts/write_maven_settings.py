#!/usr/bin/env python3
"""Write the repository-only Maven settings used by plugin CI."""

from __future__ import annotations

import argparse
from pathlib import Path


SETTINGS = """<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0 https://maven.apache.org/xsd/settings-1.0.0.xsd">
{servers}  <profiles>
    <profile>
      <id>hop-plugin-ci-repositories</id>
      <repositories>
        <repository>
          <id>central</id>
          <url>https://repo1.maven.org/maven2/</url>
          <releases><enabled>true</enabled></releases>
          <snapshots><enabled>false</enabled></snapshots>
        </repository>
        <repository>
          <id>sogeo-snapshots</id>
          <url>https://jars.interlis.guru/snapshots/</url>
          <releases><enabled>false</enabled></releases>
          <snapshots><enabled>true</enabled><updatePolicy>always</updatePolicy></snapshots>
        </repository>
        <repository>
          <id>jars-interlis</id>
          <url>https://jars.interlis.ch/</url>
          <releases><enabled>true</enabled></releases>
          <snapshots><enabled>true</enabled></snapshots>
        </repository>
      </repositories>
    </profile>
  </profiles>
  <activeProfiles><activeProfile>hop-plugin-ci-repositories</activeProfile></activeProfiles>
</settings>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--server-id")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    servers = ""
    if args.server_id:
        servers = f"""  <servers>
    <server>
      <id>{args.server_id}</id>
      <username>${{env.MAVEN_USERNAME}}</username>
      <password>${{env.MAVEN_PASSWORD}}</password>
    </server>
  </servers>
"""
    args.output.write_text(SETTINGS.format(servers=servers), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
