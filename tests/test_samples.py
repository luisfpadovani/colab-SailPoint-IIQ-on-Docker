"""Fixture contract checks: consistent identities, safe mail domains and managers."""
import base64
import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('samples', ROOT / 'scripts/generate_samples.py')
samples = importlib.util.module_from_spec(spec)
spec.loader.exec_module(samples)


class SamplesTest(unittest.TestCase):
    def test_seeded_identity_graph_is_consistent(self):
        rows = samples.identities()
        self.assertEqual(rows, samples.identities())
        self.assertNotEqual(rows, samples.identities(seed=7))
        self.assertEqual(len({r['employeeID'] for r in rows}), len(rows))
        self.assertEqual(len({r['email'] for r in rows}), len(rows))
        for row in rows:
            self.assertTrue(row['email'].endswith('@example.com'))
            self.assertIn(row['employeeStatus'], ('true', 'false'))
            if row['manager']:
                self.assertLess(int(row['manager']), int(row['employeeID']))

    def test_ldap_and_sql_reference_the_csv_identities(self):
        with tempfile.TemporaryDirectory() as folder:
            samples.generate(output_root=folder)
            base = Path(folder)
            with (base / 'data/Application/file/BaseHumanResource.csv').open() as source:
                rows = {r['employeeID']: r for r in csv.DictReader(source, delimiter=';')}
            ldif = (base / 'data/Application/ldap/bootstrap/ldif/adata.ldif').read_text()
            hashes = []
            for block in ldif.split('\n\n'):
                if '\nemployeeID:' not in block:
                    continue
                fields = dict(line.split(': ', 1) for line in block.splitlines() if ': ' in line)
                row = rows[fields['employeeID']]
                self.assertEqual(fields['displayname'], row['name'])
                self.assertEqual(fields['mail'], row['email'])
                encoded = fields['userpassword']
                self.assertTrue(encoded.startswith('{SSHA}'))
                self.assertEqual(len(base64.b64decode(encoded[6:])), 36)
                hashes.append(encoded)
            self.assertEqual(len(hashes), 4)
            self.assertEqual(len(set(hashes)), 4)
            sql = (base / 'sqlserver_iiq/scripts/98-create_table_app_mock.sql').read_text()
            for number in [1, 2, 48, 66, 51]:
                row = rows[f'{number:08d}']
                self.assertIn("N'" + row['name'].replace("'", "''") + "','" + row['employeeID'] + "'", sql)


if __name__ == '__main__':
    unittest.main()
