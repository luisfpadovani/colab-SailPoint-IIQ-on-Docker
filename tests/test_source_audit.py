"""Artifact publication guard: reject disguised payloads and product material."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('audit', Path(__file__).resolve().parents[1] / 'scripts/audit_sources.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class SourceAuditTest(unittest.TestCase):
    def test_rejects_binary_deleted_from_tip_but_still_in_new_history(self):
        with tempfile.TemporaryDirectory() as folder:
            def git(*args):
                return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null',
                    '-c', 'user.name=Source Audit Test', '-c', 'user.email=audit@example.invalid',
                    '-c', 'commit.gpgsign=false', *args], cwd=folder, stderr=subprocess.STDOUT)
            git('init')
            source = Path(folder) / 'README.md'
            source.write_text('Own project sources\n')
            git('add', 'README.md')
            git('commit', '-m', 'base')
            base = git('rev-parse', 'HEAD').decode().strip()
            payload = Path(folder) / 'product.jar'
            payload.write_bytes(b'PK\x03\x04synthetic-test-payload')
            git('add', '-f', 'product.jar')
            git('commit', '-m', 'bad intermediate package')
            git('rm', 'product.jar')
            git('commit', '-m', 'remove package at tip')
            command = [sys.executable, str(Path(audit.__file__).resolve())]
            tip = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            history = subprocess.run(command + ['--base', base], cwd=folder, capture_output=True, text=True)
            self.assertEqual(tip.returncode, 0, tip.stdout)
            self.assertEqual(history.returncode, 1, history.stdout)
            self.assertIn('product.jar', history.stdout)

    def test_rejects_product_and_private_paths(self):
        for path in ['tmp/identityiq-9.zip', 'patch.JAR', 'output/app.war', 'bin/Code.class',
                     '.env', '.secrets/log.txt', 'cert/server.key', 'schema/1-create_identityiq_tables.sql',
                     'tomcat/file_config/UI/UIConfig-Uiconfig.xml', 'tomcat/file_install/ssb/web/readme.txt']:
            with self.subTest(path=path):
                self.assertIsNotNone(audit.path_problem(path))
        for path in ['.env.example', 'scripts/check_iiq.py', 'tests/JdbcTlsProbe.java',
                     'sqlserver_iiq/scripts/98-create_table_app_mock.sql']:
            self.assertIsNone(audit.path_problem(path))

    def test_rejects_renamed_binary_and_private_key_contents(self):
        for data in [b'PK\x03\x04payload', b'\x7fELFpayload', b'\xca\xfe\xba\xbe', b'\xff\x00',
                     b'-----BEGIN PRIVATE KEY-----\nexample\n-----END PRIVATE KEY-----']:
            with self.subTest(data=data[:4]):
                self.assertIsNotNone(audit.content_problem(data))
        self.assertIsNone(audit.content_problem('Project configuration — example\n'.encode()))


if __name__ == '__main__':
    unittest.main()
