"""Validate dependency update policy without contacting Maven."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('updater', ROOT / 'scripts/update_jdbc.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class UpdaterTest(unittest.TestCase):
    def test_stable_supported_artifact_is_selected(self):
        metadata = '<metadata><versioning><versions>' + ''.join(f'<version>{v}</version>' for v in [
            '13.6.0.jre11', '13.7.0.jre11-preview', '13.6.1.jre8', '13.6.1.jre11', '../untrusted']) + '</versions></versioning></metadata>'
        self.assertEqual(updater.latest_version(metadata), '13.6.1.jre11')

    def test_corrupted_artifact_is_rejected(self):
        with patch.object(updater, 'download', side_effect=[b'0' * 64, b'corrupted jar']):
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                updater.verified_checksum('13.6.0.jre11')
        with self.assertRaises(ValueError):
            updater.verified_checksum('../untrusted')


if __name__ == '__main__':
    unittest.main()
