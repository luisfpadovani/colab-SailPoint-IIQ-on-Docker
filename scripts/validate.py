#!/usr/bin/env python3
"""Offline checks and build-secret renderer regression tests (stdlib only)."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
for script in ROOT.glob('**/*.sh'):
    if '.git' not in script.parts:
        subprocess.run(['bash', '-n', str(script)], check=True)
for xml in ROOT.glob('tomcat/file_config/**/*.xml'):
    ET.parse(xml)
assert not Path('.env').exists() or subprocess.run(['git', 'check-ignore', '-q', '.env']).returncode == 0
for removed in ['tomcat/file_install/ssb/web/WEB-INF/lib/sqljdbc4.jar', 'tomcat/file_config/UI/UIConfig-Uiconfig.xml', 'README_luisfpadovani.md']:
    assert not Path(removed).exists(), removed
spec = importlib.util.spec_from_file_location('renderer', ROOT / 'tomcat/render-build-config.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp)
    env_path = folder / '.env'
    source = ROOT / 'tomcat/file_install/ssb'
    keys = ['IIQ_DB_PASSWORD_ENCRYPTED', 'IIQ_PLUGIN_PASSWORD_ENCRYPTED', 'IIQ_AH_PASSWORD_ENCRYPTED', 'LDAP_PASSWORD_ENCRYPTED', 'JDBC_PASSWORD_ENCRYPTED']
    encoded = '1:' + 'ACP:' + 'VGVzdFZhbHVl'
    env_path.write_text('\n'.join(f"{key}='{encoded}'" for key in keys))
    def reset():
        for name in ['docker.iiq.properties', 'docker.target.properties']:
            (folder / name).write_text((source / name).read_text())
    reset()
    module.render(env_path, folder)
    assert '@@' not in (folder / 'docker.iiq.properties').read_text()
    assert encoded in (folder / 'docker.target.properties').read_text()
    for invalid in ['', 'plaintext', encoded + '\\nmalicious=true']:
        reset()
        env_path.write_text('\n'.join(f'{key}={invalid}' for key in keys))
        try:
            module.render(env_path, folder)
        except ValueError:
            pass
        else:
            raise AssertionError('Renderer accepted invalid secret')
# Generate ephemeral config-only values; never start services or accept licenses here.
env = dict(os.environ)
for key in ['LDAP_ADMIN_PASSWORD', 'MSSQL_SA_PASSWORD', 'APP_MOCK_PASSWORD', 'HEALTHCHECK_PASSWORD', 'IIQ_DB_PASSWORD', 'IIQ_PLUGIN_PASSWORD', 'IIQ_AH_PASSWORD']:
    env[key] = os.urandom(24).hex()
env['ACCEPT_EULA'] = 'CONFIG_VALIDATION_ONLY'
result = subprocess.run(['docker', 'compose', '--env-file', '.env.example', 'config', '--format', 'json'], env=env, text=True, capture_output=True, check=True)
config = json.loads(result.stdout)
for service in config['services'].values():
    for port in service.get('ports', []):
        assert port['host_ip'] == '127.0.0.1', port
        assert port['target'] != 9009
assert not config['services']['server_db'].get('ports')
assert all(service.get('read_only') for service in config['services'].values())
urls = []
for name in ['docker.iiq.properties', 'docker.target.properties']:
    urls.extend(line for line in (source / name).read_text().splitlines()
                if 'jdbc:sqlserver://' in line and not line.lstrip().startswith('#'))
assert len(urls) == 4, 'Expected three IIQ datasources and one mock connector'
assert all('sqlserver:1433' in line and 'encrypt=true' in line
           and 'trustServerCertificate=false' in line for line in urls), 'JDBC must authenticate TLS'
# An empty environment must fail closed.
minimal = {k: v for k, v in os.environ.items() if k not in env or k not in ['LDAP_ADMIN_PASSWORD', 'MSSQL_SA_PASSWORD', 'APP_MOCK_PASSWORD', 'HEALTHCHECK_PASSWORD', 'IIQ_DB_PASSWORD', 'IIQ_PLUGIN_PASSWORD', 'IIQ_AH_PASSWORD', 'ACCEPT_EULA']}
result = subprocess.run(['docker', 'compose', '--env-file', '.env.example', 'config', '--quiet'], env=minimal, capture_output=True)
assert result.returncode != 0
print('PASS: shell/XML syntax, secret rendering and invalid-secret rejection, Compose bindings and required settings')
