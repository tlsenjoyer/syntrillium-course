"""Verify that recovered course audio becomes real, locally playable media."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('ffmpeg'), 'Audio export requires FFmpeg')
class AudioExportTests(unittest.TestCase):
    def test_changed_audio_resource_is_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as temp:
            recovery = Path(temp) / 'recovered'
            exported = Path(temp) / 'audio'
            subprocess.run([sys.executable, str(ROOT / 'tools/recover.py'),
                            str(ROOT / 'course.exe'), str(recovery)],
                           check=True, capture_output=True)
            # A source clip replaced after inventorying must not pass as original.
            (recovery / 'resources/01892.bin').write_bytes(b'changed audio')
            result = subprocess.run([sys.executable, str(ROOT / 'tools/export_audio.py'),
                                     str(recovery), str(exported)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('changed since recovery', result.stderr)
            self.assertFalse(exported.exists())

    def test_all_embedded_mp3_resources_decode_and_unsupported_audio_stays_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            recovery = Path(temp) / 'recovered'
            exported = Path(temp) / 'audio'
            subprocess.run([sys.executable, str(ROOT / 'tools/recover.py'),
                            str(ROOT / 'course.exe'), str(recovery)],
                           check=True, capture_output=True)
            result = subprocess.run([sys.executable, str(ROOT / 'tools/export_audio.py'),
                                     str(recovery), str(exported)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((exported / 'audio.json').read_text())
            decoded = [r for r in manifest['resources'] if r['status'] == 'decoded']
            self.assertEqual(len(decoded), 151)
            for resource in decoded:
                with wave.open(str(exported / resource['path'])) as audio:
                    self.assertGreater(audio.getnframes(), 0)
                    self.assertGreater(audio.getframerate(), 0)
                    self.assertIn(audio.getnchannels(), (1, 2))
            encoded = [r for r in manifest['resources'] if r['status'] == 'unsupported']
            self.assertEqual([r['resource_id'] for r in encoded], [1870])
            self.assertEqual(len(manifest['score_sounds']), 141)
            by_id = {r['resource_id']: r for r in decoded}
            self.assertTrue(all(s['resource_id'] in by_id for s in manifest['score_sounds']))
            # A second run must leave the completed export untouched.
            before = (exported / 'audio.json').read_bytes()
            again = subprocess.run([sys.executable, str(ROOT / 'tools/export_audio.py'),
                                    str(recovery), str(exported)], capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual((exported / 'audio.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
