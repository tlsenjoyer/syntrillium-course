"""First-lesson coverage and narration readiness, without generated audio."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from narration import validate_utterances


class SoundFundamentalsTests(unittest.TestCase):
    def test_translation_covers_retained_source_segments_in_order(self):
        lesson = json.loads((ROOT / 'content/sound-fundamentals.json').read_text())
        source = json.loads((ROOT / 'content/sources/sound-fundamentals.json').read_text())
        self.assertEqual(lesson['source']['executable_sha256'], source['source']['executable_sha256'])
        fields = ('id', 'source_resource_id', 'source_start_frame', 'source_end_frame', 'audio_sha256')
        self.assertEqual(
            [tuple(s[k] for k in fields) for s in lesson['segments']],
            [tuple(s[k] for k in fields) for s in source['segments'] if s['id'] != '1970'])
        for segment in lesson['segments']:
            self.assertTrue(segment['english_asr'].strip())
            self.assertTrue(segment['russian'].strip())
        for utterance in validate_utterances(lesson, lesson['segments']):
            self.assertTrue(utterance['russian'].endswith('.'))
        self.assertFalse(lesson['source']['transcription_reviewed'])
        self.assertFalse(lesson['source']['translation_reviewed'])


if __name__ == '__main__':
    unittest.main()
