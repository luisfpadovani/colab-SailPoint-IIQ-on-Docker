#!/usr/bin/env python3
"""Run LDAP DN rules, connector binding and strict JDBC TLS probes in the live IIQ lab.

Reads test credentials from the ignored .env and transmits them only through
process environment variables, never command arguments, output, or image layers.
"""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
values = {}
for line in (ROOT / '.env').read_text().splitlines():
    key, separator, value = line.partition('=')
    if separator and not key.startswith('#'):
        values[key.strip()] = value.strip().strip('"\'')
credentials = ['IIQ_DB_PASSWORD', 'IIQ_PLUGIN_PASSWORD', 'IIQ_AH_PASSWORD', 'APP_MOCK_PASSWORD']
env = dict(os.environ)
for key in credentials:
    if not values.get(key):
        raise ValueError('Missing local credential: ' + key)
    env['TEST_' + key] = values[key]
for name in ['LdapDnProbe', 'JdbcBindingProbe', 'JdbcTlsProbe']:
    source = (ROOT / 'tests' / (name + '.java')).read_text()
    subprocess.run(['docker', 'compose', 'exec', '-T', 'server_web_iiq', 'sh', '-c', 'cat >/tmp/' + name + '.java'], input=source, text=True, check=True)
    command = ['docker', 'compose', 'exec', '-T']
    for key in credentials:
        command += ['-e', 'TEST_' + key]
    command += ['server_web_iiq', 'sh', '-c',
        'javac -J-Xmx256m -proc:none -cp "webapps/identityiq/WEB-INF/lib/*" -d /tmp /tmp/' + name + '.java && '
        'java -Xmx256m -cp "/tmp:webapps/identityiq/WEB-INF/classes:webapps/identityiq/WEB-INF/lib/*" ' + name]
    subprocess.run(command, env=env, check=True)
