"""Content-integrity checks through the recovery command's public interface."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]


class RecoveryTests(unittest.TestCase):
    def test_original_resources_are_accounted_for(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'recovered'
            result = subprocess.run(
                [sys.executable, str(ROOT / 'tools/recover.py'),
                 str(ROOT / 'course.exe'), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            inventory = json.loads((output / 'inventory.json').read_text())
            self.assertEqual(inventory['source']['sha256'],
                             'c385ac83b9cad64cc988d37b8e5b3c30586fcf63c478d56d473a5dcf5c360725')
            # Independently observed resource-map totals, not a completeness claim.
            self.assertEqual(len(inventory['resources']), 880)
            self.assertEqual(sum(r['tag'] == 'CASt' for r in inventory['resources']), 441)
            self.assertEqual(len(inventory['flash']), 15)
            self.assertEqual(len(inventory['members']), 441)
            self.assertIn('course023', [m['name'] for m in inventory['members']])
            self.assertTrue(any(m['media'] for m in inventory['members']))
            for resource in inventory['resources']:
                data = (output / resource['path']).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), resource['sha256'])
                self.assertEqual(len(data), resource['stored_size'])
            for flash in inventory['flash']:
                data = (output / flash['path']).read_bytes()
                self.assertEqual(data[:3], b'FWS')
                self.assertEqual(int.from_bytes(data[4:8], 'little'), len(data))
                self.assertEqual(hashlib.sha256(data).hexdigest(), flash['sha256'])


    def test_truncated_source_does_not_produce_an_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'truncated.exe'
            source.write_bytes((ROOT / 'course.exe').read_bytes()[:-100])
            output = Path(temp) / 'recovered'
            result = subprocess.run(
                [sys.executable, str(ROOT / 'tools/recover.py'), str(source), str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Truncated', result.stderr)
            self.assertFalse(output.exists())

    def test_empty_compressed_resource_cannot_claim_missing_content(self):
        # Minimal Afterburner movie with an empty ILS and a BITD entry
        # claiming eight decoded bytes but supplying zero encoded bytes.
        codec = bytes.fromhex('04e999ac7000360b0000080007377a34')
        compression = zlib.compress(b'\x01\x00' + codec + b'zlib\x00')
        initial = zlib.compress(b'')
        resource_map = (b'\x00\x00\x02'
                        + bytes([2, 0, len(initial), 0, 0]) + b' SLI'
                        + bytes([3, len(initial), 0, 8, 0]) + b'DTIB')
        packed_map = b'\x00' + bytes([len(resource_map)]) + zlib.compress(resource_map)
        body = (b'MDGFrevF\x00rdcF' + bytes([len(compression)]) + compression
                + b'PMBA' + bytes([len(packed_map)]) + packed_map
                + b'IEGF\x00' + initial)
        movie = b'XFIR' + struct.pack('<I', len(body)) + body
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'invalid.exe'
            source.write_bytes(movie)
            output = Path(temp) / 'recovered'
            result = subprocess.run(
                [sys.executable, str(ROOT / 'tools/recover.py'), str(source), str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_existing_recovery_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'recovered'
            output.mkdir()
            inventory = output / 'inventory.json'
            inventory.write_text('prior recovery')
            result = subprocess.run(
                [sys.executable, str(ROOT / 'tools/recover.py'),
                 str(ROOT / 'course.exe'), str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(inventory.read_text(), 'prior recovery')
            self.assertEqual(list(output.iterdir()), [inventory])


if __name__ == '__main__':
    unittest.main()
