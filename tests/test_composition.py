"""Content-integrity checks against the original course's recovered composition."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CompositionTests(unittest.TestCase):
    def test_recovery_connects_original_text_and_narration_to_the_score(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'recovered'
            result = subprocess.run(
                [sys.executable, str(ROOT / 'tools/recover.py'),
                 str(ROOT / 'course.exe'), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            composition = json.loads((output / 'composition.json').read_text())
            # Independent decompiler output: DRCF, MCsL and CAS*.
            self.assertEqual(composition['nominal_frame_rate'], 15)
            self.assertEqual(composition['stage'], {'width': 500, 'height': 375})
            libraries = composition['libraries']
            self.assertEqual(len(libraries), 12)
            self.assertEqual(libraries[4]['name'], 'Audio')
            members = composition['members']
            narration = next(m for m in members
                             if m['library_id'] == 5 and m['member_number'] == 5)
            self.assertEqual(narration['name'], 'course005')
            self.assertTrue(any(m['present'] and m['tag'] == 'ediM'
                                for m in narration['media']))
            # Original topic-menu order, corroborated by its navigation scripts.
            self.assertEqual([t['entry_frame'] for t in composition['topics']],
                             [130, 1003, 2814, 3389, 3697, 4684, 5985, 6377, 8022])
            self.assertEqual(composition['topics'][0]['title'], 'Sound Fundamentals')
            self.assertEqual(composition['topics'][-1]['title'], 'MIDI')
            self.assertIn({'frame': 130, 'name': '5', 'comment': ''}, composition['labels'])
            self.assertEqual(composition['score']['frame_count'], 9416)
            first_sound = composition['score']['sounds'][0]
            self.assertEqual((first_sound['start_frame'], first_sound['channel'],
                              first_sound['library_id'], first_sound['member_number']),
                             (131, 1, 5, 5))
            # Text bodies, rather than shortened cast names.
            texts = {m['name']: m['text']['value'] for m in members if 'text' in m}
            self.assertEqual(texts['pressure'], 'pressure')
            self.assertIn('Click the Jump to topic button', texts['Help Text'])
            self.assertIn('the sampling rate must be double the highest frequency',
                          texts['nyquist theorum'])
            # The End marker's script has an unresolved high-bit library value;
            # keep it visible instead of inventing a library or discarding it.
            unresolved = {(r['library_id'], r['member_number'])
                          for r in composition['unresolved_cast_references']}
            self.assertEqual(unresolved, {(16388, 1)})
            # Every score member, including unresolved ones, stays accounted for.
            known = {(m['library_id'], m['member_number']) for m in members}
            for kind in ('sprites', 'sounds', 'scripts'):
                for event in composition['score'][kind]:
                    self.assertIn((event['library_id'], event['member_number']), known | unresolved)
                    self.assertLessEqual(event['start_frame'], event['end_frame'])
                    self.assertLessEqual(event['end_frame'], 9416)


if __name__ == '__main__':
    unittest.main()
