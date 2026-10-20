# Operations and maintenance

This guide supplements the [installation instructions](../README.md). Commands run from the repository root. The stack is intended for a local development lab.

## Lifecycle and persistent data

```bash
docker compose ps -a
docker compose stop
docker compose up -d
```

SQL, LDAP, Mailpit and IIQ state use named volumes. `docker compose down` retains named volumes; `docker compose down -v` deletes them. Back up required data before any reset or migration. A bootstrap marker prevents imports and schema creation from running again on an initialized volume.

Changing `.env` does not rotate existing SQL/LDAP accounts. Rotate the actual service account, regenerate the matching IIQ encrypted value, then rebuild/restart its consumers. For changed build secrets, use `docker compose build --no-cache server_web_iiq`; BuildKit secret contents do not invalidate its cache.

The rendered configuration in the local IIQ image contains secret material. Keep the image and build cache private.

## SQL Server and certificate lifecycle

SQL Server 2022 CU27 runs only inside the Compose network, with persistent storage. Use `docker compose exec server_db /opt/mssql-tools18/bin/sqlcmd -N -S sqlserver -U sa` for interactive access; allow the tool to prompt for the password. All scripts execute in version order, SQLCMD fails on SQL errors, and a persistent marker prevents rerunning schema creation on restart. A failed partial initialization stops the container and requires restoring/resetting the lab SQL volume before another attempt. Existing volumes need a separately reviewed migration; these bootstrap scripts target a fresh lab.

All four JDBC URLs require `encrypt=true;trustServerCertificate=false`. The network hostname is `sqlserver`. A one-shot, network-isolated `sql_tls_init` service generates a private lab CA (365 days) and a server certificate (seven days), renewing the server certificate on startup when fewer than 24 hours remain. SQL Server forces TLS; SQLCMD validates the CA without `-C`. The CA private key is kept in `sql_ca`, accessible only to the certificate initializer. SQL receives only `sql_tls` (server certificate/key) and `sql_trust` (public CA); IIQ receives only the public CA, imported into its temporary Java truststore alongside LDAP's certificate.

For custom SQL certificates, stop SQL and IIQ, and use an administrator-controlled helper to replace `server.crt` and `server.key` in `sql_tls` and `ca.crt` in `sql_trust`. Use PEM, SAN `sqlserver`, serverAuth EKU, a matching key owned by UID 10001 with mode 0600, and public certificates mode 0644. Start SQL and IIQ with `docker compose up -d --no-deps server_db server_web_iiq` to avoid the lab initializer overwriting custom material. Adapt or disable `sql_tls_init` before subsequent full-stack starts. For the generated lab CA, run `docker compose run --rm sql_tls_init` and restart SQL and IIQ to activate a renewed server certificate. CA expiry deliberately fails startup; replace the CA and server certificate together and restart both consumers. Back up volumes first. The initializer runs at startup, not continuously; restart/renew before certificate expiration. Never share the CA private key with clients.

## LDAP and certificate lifecycle

OpenLDAP exposes LDAPS on 636. At first start it generates a seven-day self-signed lab certificate with SANs `ldap`, `localhost`, and `127.0.0.1`. Anonymous reads and reads of other users' password hashes are denied; simple binds require TLS. The Compose healthcheck authenticates over LDAPS and validates the certificate. IIQ trusts the public certificate via a temporary Java truststore; the private key is readable only by OpenLDAP.

For custom certificates, replace `ldap.crt` and `ldap.key` in the `ldap_tls` volume using an administrator-controlled local helper container. Use PEM format, a matching key and certificate, and a certificate valid for `ldap` (add the issuer chain to `ldap.crt` for a private CA). Keep the key owned by the container's `openldap` user with mode 0600 and the public certificate mode 0644. The certificate directory must be traversable (0755). Restart LDAP and Tomcat after replacement. Expired certificates cause startup/healthchecks to fail. To generate a fresh short-lived lab certificate, remove those two files from the volume and restart LDAP, then recreate Tomcat's truststore by restarting Tomcat. LDAP data and configuration persist separately.

Passwords in `.env` are bootstrap values: changing them does not rotate existing database/LDAP accounts. Rotate the service account first, update the matching encrypted setting, then rebuild/restart its consumers.

## Filesystem and network configuration

Every Compose service has a read-only root filesystem. SQL writes only to its data volume and temporary `/tmp` and `/home/mssql`; LDAP writes to its data/configuration/certificate volumes and temporary `/run` and `/tmp`; Mailpit writes to the persistent `mail_data` volume and temporary `/tmp`. These mounts preserve normal startup and restart without making the application image writable.

Mailpit captures test mail. SMTP 1025, web UI 8025, LDAPS 636, and IIQ HTTP 8080 bind to `127.0.0.1` by default. SQL Server and LDAP plaintext ports are unpublished, and port 9009 has been removed. Reach the UI at `http://localhost:8025`.

For remote lab access, set `BIND_ADDRESS` in `.env` to a specific host interface IP and recreate containers. This also exposes Mailpit's unauthenticated UI; prefer an SSH tunnel, or configure Mailpit UI authentication and an HTTPS proxy before exposing it. IIQ HTTP also needs an HTTPS proxy for remote use. No remote setting publishes SQL Server.

The path settings `LDAP_DATA_SCHEMA`, `LDAP_DATA`, and `DIRECTORY_TOMCAT_APPLICATION` refer to host bind mounts. Adjust them for your checkout, including Docker Desktop/Windows paths, and verify `docker compose config --quiet` before starting. Use the lowercase filename `.env`.

## Custom SQL and database upgrades

Put custom bootstrap scripts in `sqlserver_iiq/scripts`, with an explicit numeric prefix, for example `4-custom.sqlserver`. The SQL entrypoint executes `.sql` and `.sqlserver` files in version order on a new volume; it does not migrate existing databases. The mock and healthcheck scripts use prefixes 98 and 99. Review dependencies before assigning an order.

For a fresh 8.5 database, supply the GA creation script and the p1 patch script. Do not also run the general upgrade-to-8.5 script: its changes are already included in the GA creation script. Upgrades from an existing installation require a separate reviewed migration.

## Optional SSB tools

Unused services and tools default to false in `tomcat/file_install/ssb/docker.build.properties`, including plugin/generic importers, object exporter, BeanShell kit, Rule Runner and SSP. Enable only the necessary `deploy...` setting and rebuild the application. Plugin SQL/import options in `docker.iiq.properties` also default to false.

## Exclude example connectors

If you do NOT want the fake applications and demo configurations, add the following entries to:

```text
tomcat/file_install/ssb/docker.ignorefiles.properties
```

```text
Application/Application-HumanResources.xml
Application/Application-Jdbc.xml
Application/Application-Openldap.xml
CorrelationConfig/CorrelationConfig-HumanResourcesEmployee.xml
CorrelationConfig/CorrelationConfig-JdbcEmployee.xml
CorrelationConfig/CorrelationConfig-Openldap.xml
Form/Form-CreateAccountJdbc.xml
Form/Form-CreateAccountOpenldap.xml
Form/Form-CreateGroupJdbc.xml
Form/Form-CreateGroupOpenldap.xml
Form/Form-UpdateAccountJdbc.xml
Form/Form-UpdateGroupJdbc.xml
Form/Form-UpdateGroupOpenldap.xml
ObjectConfig/ObjectConfig-IdentityHumanResources.xml
Rule/Rule-HumanResourcesBuildmapEmployee.xml
Rule/Rule-HumanResourcesCreationEmployee.xml
Rule/Rule-HumanResourcesEmail.xml
Rule/Rule-HumanResourcesFirstName.xml
Rule/Rule-HumanResourcesLastName.xml
Rule/Rule-HumanResourcesManager.xml
Rule/Rule-HumanResourcesName.xml
Rule/Rule-HumanResourcesStatus.xml
Rule/Rule-HumanResourcesType.xml
Rule/Rule-IdentityGetEmployee.xml
Rule/Rule-IdentityGetFirstname.xml
Rule/Rule-IdentityGetFullName.xml
Rule/Rule-IdentityGetLastname.xml
Rule/Rule-JdbcCreateProvision.xml
Rule/Rule-JdbcDeleteProvision.xml
Rule/Rule-JdbcDisableProvision.xml
Rule/Rule-JdbcEnableProvision.xml
Rule/Rule-JdbcSetNameGroup.xml
Rule/Rule-JdbcUpdateProvision.xml
Rule/Rule-OpenldapSetAccountDn.xml
Rule/Rule-OpenldapSetGroupDn.xml
RuleLibrary/Rule-RuleLibraryGetAttributesRequest.xml
Rule/Rule-SetGroupRequest.xml
SystemConfiguration/SystemConfiguration-Email.xml
TaskDefinition/TaskDefinition-HumanResourcesAccountAggregation.xml
TaskDefinition/TaskDefinition-JdbcAccountAggregation.xml
TaskDefinition/TaskDefinition-JdbcGroupAggregation.xml
TaskDefinition/TaskDefinition-OpenLdapAccountAggregation.xml
TaskDefinition/TaskDefinition-OpenLdapGroupAggregation.xml
```

These exclusions affect subsequent builds/imports. They do not delete applications already persisted in an existing IIQ database.

## Validation, samples and dependency updates

Run `python3 scripts/validate.py` for syntax/template/security regression checks, and `python3 scripts/integration.py` for isolated LDAP/SQL runtime tests (Docker required; downloads images, creates disposable containers, and accepts the Microsoft EULA only when explicitly provided by the operator). Full IIQ acceptance still requires the licensed artifacts and the checklist in [the security report](relatorio-revisao-10-pontos.md).

The PR workflow scans the resulting source tree with Gitleaks and the repository checks. It deliberately does not rewrite or certify Git history: old commits contain the previously published sample credentials. Treat those credentials as compromised and rotate any real reuse. Review repository history and any required artifact removal separately before publication.

Sample identities are generated with **Faker**, pinned in `requirements-dev.txt`. The generator updates the CSV, LDAP users, and SQL mock fixtures together, retaining consistent employee IDs and manager relationships. It uses reserved `example.com` email addresses; LDAP/SQL passwords are random, salted and discarded. The seed reproduces identities, never password material.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/generate_samples.py --seed 20261020
python -m unittest discover -s tests -p 'test_*.py'
```

Generated fixtures apply to **new** database/LDAP volumes. Regenerating files does not migrate or overwrite existing lab accounts. Preserve existing data and plan migrations separately.

For the licensed, running lab, `python3 scripts/check_iiq.py` reads local `.env` credentials privately and evaluates the shipped LDAP DN rules with special characters, tests the actual JDBC driver (four database users, trusted TLS, rejection of unknown CA and wrong hostname), and verifies the shipped JDBC connector's parameter binding against the built Application XML. In IIQ 8.5p1 the quoted `$(identity)` tokens in account/group `getObjectSQL` are converted internally to `?` and bound with `PreparedStatement.setString`; keep the documented template syntax. Re-run these probes after upgrading IIQ. They do not replace full aggregation/provisioning acceptance.

On an existing IIQ volume, rebuilding connector XML does not replace persisted Application objects automatically. Import the reviewed updated JDBC application using the IIQ console before acceptance:

```bash
docker compose exec server_web_iiq webapps/identityiq/WEB-INF/bin/iiq console -c "import /usr/local/tomcat/webapps/identityiq/WEB-INF/config/custom/Application/Application-Jdbc.xml"
```

Third-party notices and licensing requirements are in [NOTICE](../NOTICE). See the [ten-point security review report](relatorio-revisao-10-pontos.md) for local results and remaining functional acceptance.

The SQL integration tests require an explicit `ACCEPT_EULA=Y` in the invoking environment. The workflow deliberately runs LDAP tests without accepting Microsoft's terms on behalf of contributors.

Dependabot covers Dockerfiles, Compose images, GitHub Actions and Python development dependencies. The weekly JDBC updater verifies the upstream artifact checksum and proposes a reviewed PR. Enable the repository setting **Allow GitHub Actions to create and approve pull requests** for PR creation; licensed IIQ acceptance is still needed before merging a driver upgrade.
