# SailPoint IdentityIQ on Docker

A Docker Compose lab for developing and testing SailPoint IdentityIQ integrations with SQL Server, OpenLDAP and Mailpit. The project includes Services Standard Build (SSB) configuration, example connectors, aggregation tasks and provisioning rules.

**Intended for local development and training.** Obtain IdentityIQ, SSB and their database scripts through authorized SailPoint channels. Product binaries are not distributed in this repository. See [Licensing](#licensing) before preparing the environment.

## Stack

| Component | Version / purpose |
| --- | --- |
| IdentityIQ | 8.5 with patch 8.5p1 |
| SSB | 7.0.2 |
| Application runtime | Tomcat 9 / Eclipse Temurin JDK 21 |
| Database | SQL Server 2022 CU27 |
| Microsoft JDBC driver | 13.6.0.jre11 |
| Directory | OpenLDAP, LDAPS only |
| Test email | Mailpit |

Docker base digests and dependency versions are recorded in the Dockerfiles and Compose configuration. The local stack has passed startup, database, LDAP and JDBC security checks. Complete connector aggregation and provisioning still require functional acceptance in your licensed environment.

The examples comprise a **Human Resources** delimited-file source, a **JDBC** mock application and an **OpenLDAP** application. SQL Server stores the three IIQ databases (`identityiq`, `identityiqPlugin`, `identityiqah`) and the `appMock` database. Mailpit captures outgoing lab email.

## Prerequisites

- Docker with Compose v2 and BuildKit support, using Linux containers compatible with the pinned images.
- Sufficient memory for SQL Server and the JVM. The validated local host provides approximately 8 GB RAM; SQL and IIQ each have a 3 GB container limit. Adjust resources for your workload.
- Authorized access to IdentityIQ 8.5, patch 8.5p1, SSB 7.0.2 and the corresponding SQL Server scripts.
- A trusted local IIQ CLI using the same product version and encryption key to generate encrypted configuration values.
- A JDK `jar` tool or ZIP utility to extract the licensed patch SQL script. Python 3 is needed for the repository validation scripts; sample generation also requires `requirements-dev.txt`.

## Installation

### 1. Get the project

Clone the [project repository](https://github.com/sailpoint-oss/colab-SailPoint-IIQ-on-Docker/):

```bash
git clone https://github.com/sailpoint-oss/colab-SailPoint-IIQ-on-Docker.git
cd colab-SailPoint-IIQ-on-Docker
```

### 2. Supply the licensed artifacts

Download the products through authorized SailPoint channels and place them at these exact paths:

| Artifact | Local destination |
| --- | --- |
| IdentityIQ GA | `tomcat/file_install/ssb/base/ga/identityiq-8.5.zip` |
| IdentityIQ patch | `tomcat/file_install/ssb/base/patch/identityiq-8.5p1.jar` |
| SSB archive, renamed to `ssb.zip` | `tomcat/file_install/ssb.zip` |
| GA SQL Server creation script | `sqlserver_iiq/scripts/1-create_identityiq_tables-8.5.sqlserver` |
| p1 SQL Server patch script | `sqlserver_iiq/scripts/3-upgrade_identityiq_tables-8.5p1.sqlserver` |

Extract the patch SQL from the patch JAR in a temporary directory, inspect its contents, and copy only the matching SQL Server script into the destination above. Use the GA **creation** script for a fresh database. Do not also add the general upgrade-to-8.5 script; existing database upgrades require a separate migration. Licensed artifacts and scripts are ignored by Git.

### 3. Configure credentials and license acceptance

```bash
cp .env.example .env
chmod 600 .env
```

Fill every required empty setting before building. Use a unique password for each SQL login (`sa`, `appMock`, `healthcheck`, `identityiq`, `identityiqPlugin`, `identityiqah`) and for the LDAP administrator. Never commit `.env`.

For the five SQLCMD-substituted passwords (`APP_MOCK_PASSWORD`, `HEALTHCHECK_PASSWORD`, `IIQ_DB_PASSWORD`, `IIQ_PLUGIN_PASSWORD`, `IIQ_AH_PASSWORD`), use 16–128 characters from letters, digits and `_@%+=:,./!?-`, including upper/lowercase letters, numbers and punctuation. Do not put dollar signs in `.env` passwords because Compose interpolates them. Keep secrets out of build arguments, terminal history and command traces.

In the locally supplied GA SQL script, replace the vendor password literals with the following SQLCMD placeholders; keep the surrounding SQL quotes:

| SQL login | Placeholder in licensed creation script |
| --- | --- |
| `identityiq` | `'$(IIQ_DB_PASSWORD)'` |
| `identityiqPlugin` | `'$(IIQ_PLUGIN_PASSWORD)'` |
| `identityiqah` | `'$(IIQ_AH_PASSWORD)'` |

Review the [Microsoft SQL Server EULA](https://go.microsoft.com/fwlink/?linkid=857698) and set `ACCEPT_EULA=Y` yourself only after accepting its terms. The example uses `MSSQL_PID=Developer` for a development/testing lab; select an edition licensed for your intended use.

### 4. Generate encrypted IIQ values

Use `WEB-INF/bin/iiq encrypt` in your trusted local installation, following the help for the licensed version and using the same encryption key as the target IIQ instance. Set these values in `.env`:

| Encrypted setting | Password to encrypt |
| --- | --- |
| `IIQ_DB_PASSWORD_ENCRYPTED` | `IIQ_DB_PASSWORD` |
| `IIQ_PLUGIN_PASSWORD_ENCRYPTED` | `IIQ_PLUGIN_PASSWORD` |
| `IIQ_AH_PASSWORD_ENCRYPTED` | `IIQ_AH_PASSWORD` |
| `LDAP_PASSWORD_ENCRYPTED` | `LDAP_ADMIN_PASSWORD` |
| `JDBC_PASSWORD_ENCRYPTED` | `APP_MOCK_PASSWORD` |

The build renders configuration through a BuildKit secret mount. Encoded values remain secrets, and the resulting local application image contains sensitive configuration. Keep the image and build cache private. When changing build secrets, rebuild with `docker compose build --no-cache server_web_iiq`.

The LDAP examples assume `dc=corp1`. Changing `LDAP_BASE_DN` requires corresponding changes to the bootstrap LDIF, connector configuration and DN rules.

### 5. Build and start

```bash
python3 scripts/validate.py
docker compose up --build -d
docker compose ps -a
```

The first start initializes the SQL schema, imports IIQ configuration and prepares lab certificates. Allow time for initialization. `sql_tls_init` exits successfully after preparing certificates; this is expected. Review logs locally if startup fails, taking care not to publish sensitive configuration.

| Service | Local address |
| --- | --- |
| IdentityIQ | <http://localhost:8080/identityiq/> |
| Mailpit web UI | <http://localhost:8025/> |
| Mailpit SMTP | `localhost:1025` |
| OpenLDAP | `ldaps://localhost:636` |
| SQL Server | Compose network only; no published host port |

### 6. Complete first-login acceptance

Change the built-in IIQ administrator password through IdentityIQ immediately after the first login, then verify that the previous password fails. **This is a manual step.** Service-account configuration in `.env` does not change the administrator's web login password.

Run the functional acceptance checks for HR, JDBC and OpenLDAP: aggregation, correlation, account/group provisioning, lifecycle changes and password reset. Seed accounts use discarded random passwords; assign a new password before testing their authentication.

## Security and configuration

- Published ports bind to `127.0.0.1` by default. SQL Server has no published port; LDAP has no plaintext listener. Port 9009 is not published.
- All four JDBC URLs require `encrypt=true;trustServerCertificate=false`. SQL Server forces TLS and clients validate the public lab CA.
- OpenLDAP requires LDAPS for simple binds. ACLs deny anonymous reads and protect password hashes.
- IIQ runs as UID/GID 10001. Every Compose service has a read-only root filesystem, explicit writable mounts and resource limits. Build tools remain outside the final application image.
- Unused SSB tools and plugin SQL/import execution default to disabled.
- The large custom `UIConfig-Uiconfig.xml` export is excluded. The validated lab starts with the product's standard UI configuration; the export is not a bootstrap requirement.

SQL and LDAP lab server certificates are valid for seven days. SQL's initializer renews its server certificate when fewer than 24 hours remain; it runs on startup, not continuously. The generated SQL CA lasts 365 days. LDAP replacement/renewal requires an explicit operator action. Follow the [certificate and maintenance procedures](docs/operations.md) before expiry.

For remote access, prefer an SSH tunnel. The explicit alternative is to set `BIND_ADDRESS` in `.env` to a selected host interface IP and recreate containers. This also publishes Mailpit's unauthenticated UI on that interface: configure UI authentication and HTTPS before exposing it, and provide an HTTPS proxy for IIQ. No remote setting publishes SQL Server.

Passwords are bootstrap settings. Editing `.env` does not rotate existing SQL/LDAP accounts or migrate persisted IIQ Application objects. See [Operations and maintenance](docs/operations.md) for rotation, targeted imports, optional connectors, custom SQL and host paths.

## Data and lifecycle

Named volumes preserve SQL, LDAP, Mailpit and IIQ state. Stop and resume the lab with:

```bash
docker compose stop
docker compose up -d
```

`docker compose down -v` deletes named volumes. Back up data before any reset. Existing databases require explicit migrations; bootstrap scripts do not run again on initialized volumes.

Sample identities are generated with Faker, pinned in `requirements-dev.txt`. CSV, LDAP and SQL fixtures share consistent IDs, names and relationships, with `example.com` addresses. Regeneration affects bootstrap files, not accounts in existing volumes. See [sample generation](docs/operations.md#validation-samples-and-dependency-updates).

## Validation

```bash
# Audit staged sources and all new Git objects before publication
python3 scripts/audit_sources.py --base origin/main

# Offline configuration, XML/shell syntax and security assertions
python3 scripts/validate.py

# Disposable LDAP runtime tests (Docker required)
python3 scripts/integration.py

# Licensed running lab: DN rules, JDBC binding and authenticated TLS
python3 scripts/check_iiq.py
```

To include disposable SQL tests, explicitly set `ACCEPT_EULA=Y` in the invoking environment after reviewing the Microsoft terms. Development unit tests require installing `requirements-dev.txt`; commands are in the [maintenance guide](docs/operations.md).

The PR pipeline checks the source tree and new commit history for product archives, binaries and local artifacts, then runs configuration checks, unit tests, LDAP integration and Gitleaks. Dependabot covers container images, Actions and Python dependencies. A weekly workflow proposes driver updates after checking the downloaded JAR's SHA-256. The current pin is downloaded from [Maven Central](https://repo.maven.apache.org/maven2/com/microsoft/sqlserver/mssql-jdbc/13.6.0.jre11/), SHA-256 `4c566e4022c4dcf1489aeb639fe49a0f6ffae3d796fdc2f56b5b8882d4c3bf5a`; release notes: [Microsoft JDBC release notes](https://github.com/microsoft/mssql-jdbc/releases/tag/v13.6.0).

See the [ten-point security review report](docs/relatorio-revisao-10-pontos.md) for requested changes, implementation evidence and remaining acceptance work. A source-tree scan does not certify Git history; review historical secrets and rotate any real reuse before publication.

## Licensing

Project source is distributed under [LICENSE.txt](LICENSE.txt). Third-party components retain their own licenses and terms; see [NOTICE](NOTICE). IdentityIQ and SSB are proprietary SailPoint downloads subject to the terms supplied with them. SQL Server requires explicit EULA acceptance and an edition licensed for the intended use. Do not redistribute licensed binaries, SQL scripts or built application images without the necessary rights.

## Contributing and support

Only project source, integration configuration, synthetic fixtures, tests and documentation belong in commits. Product ZIP/JAR/WAR files, compiled code, licensed SQL scripts, full product UI exports, `.env`, keys and local logs must remain outside Git. Run the artifact audit above before publishing. See the [publication audit](docs/auditoria-publicacao.md) for the clean branch and scope.

Use [GitHub issues](https://github.com/sailpoint-oss/colab-SailPoint-IIQ-on-Docker/issues) for reproducible bugs and feature requests, and submit changes through pull requests. Include relevant validation and keep credentials, licensed artifacts and local environment files out of contributions. Community examples require validation for your own licensed environment and are not a production deployment blueprint.
