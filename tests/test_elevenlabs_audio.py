import json
from pathlib import Path
import tempfile
import unittest
import sys
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import elevenlabs_audio
from elevenlabs_audio import ElevenLabsError, generate, promote


class FakeApi:
    def __init__(self, failing=()):
        self.calls = []
        self.failing = set(failing)

    def audio(self, voice_id, model_id, text, output_format, voice_settings):
        self.calls.append((voice_id, model_id, text, output_format))
        if text in self.failing:
            raise ElevenLabsError('quota exhausted')
        return ('audio:' + text).encode(), None


class ElevenLabsAudioTests(unittest.TestCase):
    def setUp(self):
        self.lesson = {
            'id': 'demo', 'title': 'Demo',
            'segments': [
                {'id': '1', 'source_resource_id': 1001, 'russian': 'Первый'},
                {'id': '2', 'source_resource_id': 1002, 'russian': 'Второй'},
            ],
        }

    def test_generation_keeps_successful_segments_when_later_segment_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            api = FakeApi(failing=('Второй',))
            with self.assertRaisesRegex(ElevenLabsError, 'candidate kept'):
                generate(content, 'demo', 'voice', 'model', None, True, candidate, 'mp3_44100_128', api)
            self.assertTrue((candidate / 'audio/1.mp3').is_file())
            manifest = json.loads((candidate / 'generation.json').read_text())
            self.assertEqual(manifest['missing_segments'], ['2'])
            self.assertEqual([call[2] for call in api.calls], ['Первый', 'Второй'])

    def test_rerun_reuses_existing_segment_and_generates_only_selected_missing_segment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            first = FakeApi(failing=('Второй',))
            with self.assertRaises(ElevenLabsError):
                generate(content, 'demo', 'voice', 'model', None, True, candidate, 'mp3_44100_128', first)
            second = FakeApi()
            generate(content, 'demo', 'voice', 'model', '2', False, candidate, 'mp3_44100_128', second)
            self.assertEqual([call[2] for call in second.calls], ['Второй'])

    def test_promotion_validates_all_selected_files_before_copying_any(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            api = FakeApi()
            generate(content, 'demo', 'voice', 'model', '1', False, candidate, 'mp3_44100_128', api)
            player = root / 'player'
            with self.assertRaisesRegex(ElevenLabsError, 'missing segment 2'):
                promote(content, 'demo', candidate, None, True, player)
            self.assertFalse((player / 'audio/00001.mp3').exists())

    def test_promotion_rejects_stale_text_before_copying(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            generate(content, 'demo', 'voice', 'model', '1', False, candidate, 'mp3_44100_128', FakeApi())
            changed = dict(self.lesson)
            changed['segments'] = [dict(self.lesson['segments'][0], russian='Updated text'), self.lesson['segments'][1]]
            content.write_text(json.dumps(changed), encoding='utf-8')
            player = root / 'player'
            with self.assertRaisesRegex(ElevenLabsError, 'lesson content has changed'):
                promote(content, 'demo', candidate, '1', False, player)
            self.assertFalse((player / 'audio/01001.mp3').exists())

    def test_promotion_rejects_changed_lesson_content_before_copying(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            generate(content, 'demo', 'voice', 'model', '1', False, candidate, 'mp3_44100_128', FakeApi())
            changed = dict(self.lesson, title='Changed title')
            content.write_text(json.dumps(changed), encoding='utf-8')
            player = root / 'player'
            with self.assertRaisesRegex(ElevenLabsError, 'lesson content has changed'):
                promote(content, 'demo', candidate, '1', False, player)
            self.assertFalse((player / 'audio/01001.mp3').exists())

    def test_cli_generates_and_promotes_all_segments_for_one_lesson(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            player = root / 'player'
            api = FakeApi()
            with patch.object(sys, 'argv', [
                    'elevenlabs_audio.py', 'generate-elevenlabs', '--content', str(content),
                    '--lesson', 'demo', '--voice-id', 'voice', '--model-id', 'model', '--all',
                    '--candidate', str(candidate)]), patch.object(elevenlabs_audio, 'require_client', return_value=api), \
                    redirect_stdout(StringIO()):
                elevenlabs_audio.main()
            with patch.object(sys, 'argv', [
                    'elevenlabs_audio.py', 'promote-elevenlabs', '--content', str(content),
                    '--lesson', 'demo', '--candidate', str(candidate), '--all', '--player', str(player)]), \
                    patch.object(elevenlabs_audio, 'load_api_key', return_value=None), redirect_stdout(StringIO()):
                elevenlabs_audio.main()
            self.assertEqual((player / 'audio/01001.mp3').read_bytes(), 'audio:Первый'.encode())
            self.assertEqual((player / 'audio/01002.mp3').read_bytes(), 'audio:Второй'.encode())
            approved = json.loads((player / 'generation.json').read_text())['approved_narration']
            self.assertEqual(approved['1001']['provider'], 'elevenlabs')
            self.assertEqual(approved['1001']['model_id'], 'model')
            self.assertEqual(approved['1001']['voice_settings']['speed'], 1)

    def test_promotion_rolls_back_audio_files_if_a_later_replacement_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            player = root / 'player'
            generate(content, 'demo', 'voice', 'model', None, True, candidate, 'mp3_44100_128', FakeApi())
            audio_dir = player / 'audio'
            audio_dir.mkdir(parents=True)
            (audio_dir / '01001.mp3').write_bytes(b'old one')
            (audio_dir / '01002.mp3').write_bytes(b'old two')
            real_replace = elevenlabs_audio.os.replace
            replacements = 0

            def fail_second(source, target):
                nonlocal replacements
                replacements += 1
                if replacements == 2:
                    raise OSError('simulated disk error')
                return real_replace(source, target)

            with patch.object(elevenlabs_audio.os, 'replace', side_effect=fail_second):
                with self.assertRaisesRegex(OSError, 'simulated disk error'):
                    promote(content, 'demo', candidate, None, True, player)
            self.assertEqual((audio_dir / '01001.mp3').read_bytes(), b'old one')
            self.assertEqual((audio_dir / '01002.mp3').read_bytes(), b'old two')


if __name__ == '__main__':
    unittest.main()
