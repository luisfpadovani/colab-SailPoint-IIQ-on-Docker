"""Preserve existing SQL settings and enforce authenticated TLS for this lab."""
import configparser
from pathlib import Path

path = Path('/var/opt/mssql/mssql.conf')
config = configparser.ConfigParser()
config.read(path)
if not config.has_section('network'):
    config.add_section('network')
for key, value in {
    'tlscert': '/run/sql-tls/server.crt',
    'tlskey': '/run/sql-tls/server.key',
    'tlsprotocols': '1.2',
    'forceencryption': '1',
}.items():
    config.set('network', key, value)
with path.open('w') as stream:
    config.write(stream)
