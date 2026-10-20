#!/usr/bin/env python3
"""Disposable runtime regressions. SQL requires the operator's ACCEPT_EULA=Y."""
import os
from pathlib import Path
import secrets
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
prefix = 'iiq-review-' + secrets.token_hex(4)
created = []
created_volumes = []


def run(*args, input=None, check=True):
    return subprocess.run(args, input=input, text=True, capture_output=True, check=check)


def wait_for(name, args, attempts=60):
    for _ in range(attempts):
        result = run('docker', 'exec', name, *args, check=False)
        if result.returncode == 0:
            return
        status = run('docker', 'inspect', '-f', '{{.State.Running}}', name).stdout.strip()
        if status != 'true':
            break
        time.sleep(2)
    logs = run('docker', 'logs', '--tail', '30', name, check=False).stdout
    raise RuntimeError(f'{name} failed readiness: {logs}')


def ldap_test():
    name = prefix + '-ldap'
    password = secrets.token_urlsafe(32)
    # Rebuild to test the current source, using cached packages where available.
    subprocess.run(['docker', 'build', '-q', '-t', 'iiq-review-openldap:local', './openldap'], check=True)
    created.append(name)
    # Feed secret through a temporary env file, avoiding command-line values.
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w') as env_file:
        env_file.write(f'LDAP_ADMIN_PASSWORD={password}\n')
        env_file.flush()
        run('docker', 'run', '-d', '--name', name, '--hostname', 'ldap', '--env-file', env_file.name,
            '--read-only', '--tmpfs', '/tmp', '--tmpfs', '/run',
            '-v', '/etc/ldap/slapd.d', '-v', '/var/lib/ldap', '-v', '/etc/ldap/tls',
            '-v', f'{ROOT}/data/Application/ldap/bootstrap/schema/attributes.schema:/bootstrap/schema/attributes.schema:ro',
            '-v', f'{ROOT}/data/Application/ldap/bootstrap/ldif/adata.ldif:/bootstrap/ldif/adata.ldif:ro',
            'iiq-review-openldap:local')
    admin = ['ldapsearch', '-x', '-H', 'ldaps://localhost:636', '-D', 'cn=admin,dc=corp1', '-y', '/run/ldap-admin-password', '-b', 'dc=corp1']
    trusted = ['env', 'LDAPTLS_CACERT=/etc/ldap/tls/ldap.crt']
    wait_for(name, trusted + admin)
    result = run('docker', 'exec', name, *trusted, *admin)
    import csv
    with (ROOT / 'data/Application/file/BaseHumanResource.csv').open() as source:
        ceo = next(csv.DictReader(source, delimiter=';'))
    assert ceo['name'] in result.stdout
    anon = run('docker', 'exec', name, *trusted, 'ldapsearch', '-x', '-H', 'ldaps://localhost:636', '-b', 'dc=corp1', check=False)
    assert 'dn: ' not in anon.stdout, 'Anonymous read disclosed entries'
    untrusted = run('docker', 'exec', name, 'ldapsearch', '-x', '-H', 'ldaps://localhost:636', '-b', 'dc=corp1', check=False)
    assert untrusted.returncode != 0, 'Untrusted TLS was accepted'
    # Set one fixture password, then verify an ordinary user cannot read password hashes.
    user_password = secrets.token_urlsafe(24)
    ldif = f'dn: cn=00000001,ou=Users,dc=corp1\nchangetype: modify\nreplace: userPassword\nuserPassword: {user_password}\n'
    run('docker', 'exec', '-i', name, *trusted, 'ldapmodify', '-x', '-H', 'ldaps://localhost:636', '-D', 'cn=admin,dc=corp1', '-y', '/run/ldap-admin-password', input=ldif)
    run('docker', 'exec', '-i', name, 'sh', '-c', 'umask 077; cat >/run/user-password', input=user_password)
    result = run('docker', 'exec', name, *trusted, 'ldapsearch', '-x', '-H', 'ldaps://localhost:636', '-D', 'cn=00000001,ou=Users,dc=corp1', '-y', '/run/user-password', '-b', 'cn=00000003,ou=Users,dc=corp1', 'userPassword')
    assert 'userPassword:' not in result.stdout and 'userPassword::' not in result.stdout
    # No cleartext TCP listener, including inside the network namespace.
    plain = run('docker', 'exec', name, 'ldapsearch', '-x', '-H', 'ldap://localhost:389', '-b', 'dc=corp1', check=False)
    assert plain.returncode != 0
    run('docker', 'restart', name)
    wait_for(name, trusted + admin)
    print('PASS: LDAP bootstrap, LDAPS certificate validation, anonymous read denial, password ACL, no plaintext listener, restart')


def sql_test():
    if os.environ.get('ACCEPT_EULA') != 'Y':
        print('SKIP: SQL runtime checks require the operator to set ACCEPT_EULA=Y after reviewing Microsoft terms')
        return
    import tempfile
    name = prefix + '-sql'
    subprocess.run(['docker', 'build', '-q', '-t', 'iiq-review-sql:local', './sqlserver_iiq'], check=True)
    subprocess.run(['docker', 'build', '-q', '-t', 'iiq-review-tls:local', './tls'], check=True)
    volumes = {key: prefix + '-' + key for key in ['ca', 'tls', 'trust']}
    created_volumes.extend(volumes.values())
    for volume in volumes.values():
        run('docker', 'volume', 'create', volume)
    run('docker', 'run', '--rm', '--network', 'none', '--read-only', '--tmpfs', '/tmp',
        '-v', volumes['ca'] + ':/ca', '-v', volumes['tls'] + ':/out/server',
        '-v', volumes['trust'] + ':/out/trust', 'iiq-review-tls:local')
    with tempfile.NamedTemporaryFile(mode='w') as env_file:
        env_file.write('ACCEPT_EULA=Y\nMSSQL_PID=Developer\nMSSQL_MEMORY_LIMIT_MB=2048\nSSL_CERT_FILE=/run/sql-trust/ca.crt\n')
        for key in ['MSSQL_SA_PASSWORD', 'APP_MOCK_PASSWORD', 'HEALTHCHECK_PASSWORD', 'IIQ_DB_PASSWORD', 'IIQ_PLUGIN_PASSWORD', 'IIQ_AH_PASSWORD']:
            env_file.write(f'{key}=Aa9!{secrets.token_hex(20)}\n')
        env_file.flush()
        created.append(name)
        run('docker', 'run', '-d', '--name', name, '--hostname', 'sqlserver', '--env-file', env_file.name,
            '--read-only', '--memory', '3g', '--cpus', '2',
            '--tmpfs', '/tmp:uid=10001,gid=10001,mode=1770',
            '--tmpfs', '/home/mssql:uid=10001,gid=10001,mode=0700',
            '-v', '/var/opt/mssql', '-v', volumes['tls'] + ':/run/sql-tls:ro',
            '-v', volumes['trust'] + ':/run/sql-trust:ro', 'iiq-review-sql:local')
    sql = ['sh', '-c', 'SQLCMDPASSWORD="$MSSQL_SA_PASSWORD" /opt/mssql-tools18/bin/sqlcmd -N -b -l 3 -S sqlserver -U sa -i /tmp/regression.sql']
    wait_for(name, ['test', '-f', '/var/opt/mssql/.initialized'], attempts=180)
    run('docker', 'exec', '-i', name, 'sh', '-c', 'cat >/tmp/regression.sql', input=(ROOT / 'scripts/sql-regression.sql').read_text())
    run('docker', 'exec', name, *sql)
    # appMock can execute procedures but cannot read tables or acquire db_owner.
    query = 'EXEC dbo.GET_ALL_USER; IF IS_ROLEMEMBER(\'db_owner\')=1 THROW 51009, \'appMock is db_owner\', 1; IF HAS_PERMS_BY_NAME(\'dbo.tbl_user\',\'OBJECT\',\'SELECT\')=1 THROW 51010, \'Direct read granted\', 1;'
    run('docker', 'exec', '-i', name, 'sh', '-c', 'SQLCMDPASSWORD="$APP_MOCK_PASSWORD" /opt/mssql-tools18/bin/sqlcmd -N -b -l 3 -S sqlserver -U appMock -d appMock', input=query)
    rejected = run('docker', 'exec', name, 'sh', '-c', 'SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt SQLCMDPASSWORD="$HEALTHCHECK_PASSWORD" /opt/mssql-tools18/bin/sqlcmd -N -b -l 3 -S sqlserver -U healthcheck -d master -Q "SELECT 1"', check=False)
    assert rejected.returncode != 0 and 'certificate' in (rejected.stdout + rejected.stderr).lower(), 'Untrusted SQL certificate accepted'
    run('docker', 'restart', name)
    wait_for(name, ['sh', '-c', 'SQLCMDPASSWORD="$HEALTHCHECK_PASSWORD" /opt/mssql-tools18/bin/sqlcmd -N -b -l 3 -S sqlserver -U healthcheck -d master -Q "SELECT 1"'])
    print('PASS: read-only SQL bootstrap, authenticated TLS and rejection of untrusted issuer, membership isolation, duplicates, salt/hash, appMock permissions, restart')


try:
    ldap_test()
    sql_test()
finally:
    for name in created:
        run('docker', 'rm', '-f', '-v', name, check=False)

    for volume in created_volumes:
        run('docker', 'volume', 'rm', volume, check=False)
