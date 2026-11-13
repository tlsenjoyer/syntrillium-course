import json
import base64
from pathlib import Path
import shutil
import tempfile
import unittest
import sys
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import elevenlabs_audio
from elevenlabs_audio import DEFAULT_VOICE_SETTINGS, ElevenLabsError, build_preview, generate, promote


class FakeApi:
    def __init__(self, failing=()):
        self.calls = []
        self.failing = set(failing)

    def audio_with_timestamps(self, voice_id, model_id, text, output_format, voice_settings):
        self.calls.append((voice_id, model_id, text, output_format))
        if text in self.failing:
            raise ElevenLabsError('quota exhausted')
        return ('audio:' + text).encode(), None, {
            'characters': list(text),
            'character_start_times_seconds': [index * 0.1 for index in range(len(text))],
            'character_end_times_seconds': [(index + 1) * 0.1 for index in range(len(text))],
        }


class ElevenLabsAudioTests(unittest.TestCase):
    def setUp(self):
        self.lesson = {
            'id': 'demo', 'title': 'Demo',
            'segments': [
                {'id': '1', 'source_resource_id': 1001, 'russian': 'Первый…'},
                {'id': '2', 'source_resource_id': 1002, 'russian': '…и второй'},
                {'id': '3', 'source_resource_id': 1003, 'russian': 'Третий'},
            ],
            'utterances': [
                {'id': '1', 'segment_ids': ['1', '2'], 'russian': 'Первый и второй',
                 'visual_cues': [{'segment_id': '1'}, {'segment_id': '2', 'anchor': 'и второй'}]},
                {'id': '3', 'segment_ids': ['3'], 'russian': 'Третий',
                 'visual_cues': [{'segment_id': '3'}]},
            ],
        }

    def test_generation_requests_one_complete_utterance_with_character_timings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            api = FakeApi()

            generate(content, 'demo', 'voice', 'model', '1', False, candidate,
                     'mp3_44100_128', api)

            self.assertEqual([call[2] for call in api.calls], ['Первый и второй'])
            self.assertEqual((candidate / 'audio/1.mp3').read_bytes(), 'audio:Первый и второй'.encode())
            manifest = json.loads((candidate / 'generation.json').read_text())
            record = manifest['utterances']['1']
            self.assertEqual(record['segment_ids'], ['1', '2'])
            self.assertEqual(record['alignment']['characters'], list('Первый и второй'))
            self.assertEqual(record['duration'], 1.5)

    def test_generation_rejects_a_missing_visual_anchor_before_requesting_speech(self):
        with tempfile.TemporaryDirectory() as temp:
            content = Path(temp) / 'lesson.json'
            lesson = json.loads(json.dumps(self.lesson))
            lesson['utterances'][0]['visual_cues'][1]['anchor'] = 'not in the sentence'
            content.write_text(json.dumps(lesson), encoding='utf-8')
            api = FakeApi()

            with self.assertRaisesRegex(ElevenLabsError, 'Missing or ambiguous visual cue anchor'):
                generate(content, 'demo', 'voice', 'model', '1', False, Path(temp) / 'candidate',
                         'mp3_44100_128', api)

            self.assertEqual(api.calls, [])

    def test_generation_keeps_audio_when_the_provider_omits_alignment(self):
        class MissingAlignmentApi(FakeApi):
            def audio_with_timestamps(self, voice_id, model_id, text, output_format, voice_settings):
                self.calls.append((voice_id, model_id, text, output_format))
                return b'mp3 audio', 'request-1', None

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            with patch.object(elevenlabs_audio, 'probe_audio_duration', return_value=1.5):
                generate(content, 'demo', 'voice', 'model', '1', False, candidate,
                         'mp3_44100_128', MissingAlignmentApi())

            manifest = json.loads((candidate / 'generation.json').read_text())
            record = manifest['utterances']['1']
            self.assertEqual((candidate / 'audio/1.mp3').read_bytes(), b'mp3 audio')
            self.assertEqual(record['status'], 'needs_manual_timing')
            self.assertEqual(record['duration'], 1.5)
            self.assertEqual(record['cue_times'], [])

    def test_timestamped_client_uses_the_json_endpoint_and_decodes_audio(self):
        class Response:
            headers = {'request-id': 'request-1'}

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return json.dumps({
                    'audio_base64': base64.b64encode(b'mp3').decode(),
                    'alignment': {'characters': ['A'], 'character_start_times_seconds': [0],
                                  'character_end_times_seconds': [0.1]},
                }).encode()

        requests = []

        def open_request(request, timeout):
            requests.append((request, timeout))
            return Response()

        client = elevenlabs_audio.ElevenLabsClient('secret')
        with patch.object(elevenlabs_audio, 'urlopen', side_effect=open_request):
            audio, request_id, alignment = client.audio_with_timestamps(
                'voice', 'model', 'A', 'mp3_44100_128', DEFAULT_VOICE_SETTINGS)

        request, timeout = requests[0]
        self.assertEqual(request.full_url, 'https://api.elevenlabs.io/v1/text-to-speech/voice/with-timestamps?output_format=mp3_44100_128')
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(audio, b'mp3')
        self.assertEqual(request_id, 'request-1')
        self.assertEqual(alignment['characters'], ['A'])
        self.assertEqual(timeout, 120)

    def test_generation_keeps_successful_utterances_when_later_utterance_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            api = FakeApi(failing=('Третий',))
            with self.assertRaisesRegex(ElevenLabsError, 'candidate kept'):
                generate(content, 'demo', 'voice', 'model', None, True, candidate, 'mp3_44100_128', api)
            self.assertTrue((candidate / 'audio/1.mp3').is_file())
            manifest = json.loads((candidate / 'generation.json').read_text())
            self.assertEqual(manifest['missing_utterances'], ['3'])
            self.assertEqual([call[2] for call in api.calls], ['Первый и второй', 'Третий'])

    def test_rerun_reuses_existing_segment_and_generates_only_selected_missing_segment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            first = FakeApi(failing=('Третий',))
            with self.assertRaises(ElevenLabsError):
                generate(content, 'demo', 'voice', 'model', None, True, candidate, 'mp3_44100_128', first)
            second = FakeApi()
            generate(content, 'demo', 'voice', 'model', '3', False, candidate, 'mp3_44100_128', second)
            self.assertEqual([call[2] for call in second.calls], ['Третий'])

    def test_promotion_validates_all_selected_files_before_copying_any(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            api = FakeApi()
            generate(content, 'demo', 'voice', 'model', '1', False, candidate, 'mp3_44100_128', api)
            player = root / 'player'
            with self.assertRaisesRegex(ElevenLabsError, 'missing utterance 3'):
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
            changed['segments'] = [dict(self.lesson['segments'][0], russian='Updated text'),
                                  self.lesson['segments'][1], self.lesson['segments'][2]]
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

    def test_promotion_updates_one_utterance_and_its_visual_cue_times(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            generate(content, 'demo', 'voice', 'model', '1', False, candidate,
                     'mp3_44100_128', FakeApi())
            player = root / 'player'
            player.mkdir()
            playback = {
                'title': 'Demo',
                'utterances': [{
                    'id': '1', 'caption': 'Первый и второй', 'audio': 'audio/01001.mp3',
                    'duration': 2, 'segment_ids': ['1', '2'],
                    'cues': [
                        {'segment_id': '1', 'at': 0, 'frames': []},
                        {'segment_id': '2', 'at': 1, 'frames': []},
                    ],
                }],
            }
            (player / 'lesson.js').write_text('window.LESSON = ' + json.dumps(playback) + ';\n')

            promote(content, 'demo', candidate, '1', False, player)

            updated = json.loads((player / 'lesson.js').read_text().removeprefix('window.LESSON = ').rstrip(' ;\n'))
            utterance = updated['utterances'][0]
            self.assertEqual(utterance['duration'], 1.5)
            self.assertAlmostEqual(utterance['cues'][1]['at'], 0.7)
            self.assertEqual(utterance['caption'], 'Первый и второй')
            generation = json.loads((player / 'generation.json').read_text())
            self.assertEqual(generation['audio'], [{
                'path': 'audio/01001.mp3', 'utterance_id': '1',
                'source_resource_id': 1001, 'source_resource_ids': [1001, 1002],
                'sha256': generation['approved_utterances']['1']['sha256'], 'duration': 1.5,
            }])

    def test_promotion_upgrades_legacy_segments_and_preserves_unselected_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            generate(content, 'demo', 'voice', 'model', '1', False, candidate,
                     'mp3_44100_128', FakeApi())
            player = root / 'player'
            player.mkdir()
            legacy_segments = [
                {'id': segment['id'], 'caption': segment['russian'],
                 'audio': f"audio/{segment['source_resource_id']:05d}.mp3", 'duration': 2.0,
                 'frames': [{'at': 0, 'items': [{'segment': segment['id']}]}]}
                for segment in self.lesson['segments']
            ]
            (player / 'lesson.js').write_text('window.LESSON = ' + json.dumps({
                'title': 'Demo', 'segments': legacy_segments,
            }) + ';\n')

            promote(content, 'demo', candidate, '1', False, player)

            source = (player / 'lesson.js').read_text().removeprefix('window.LESSON = ').strip().removesuffix(';')
            updated = json.loads(source)
            first, second = updated['utterances']
            self.assertEqual(first['id'], '1')
            self.assertEqual(first['segment_ids'], ['1', '2'])
            self.assertEqual(first['audio'], 'audio/01001.mp3')
            self.assertAlmostEqual(first['cues'][1]['at'], 0.7)
            self.assertEqual(second['id'], '3')
            self.assertEqual(second['audio'], 'audio/01003.mp3')
            self.assertEqual(second['duration'], 2.0)
            self.assertEqual(second['cues'][0]['frames'][0]['items'][0]['segment'], '3')
            self.assertFalse((player / 'audio/01003.mp3').exists())

    def test_promotion_rejects_incomplete_visual_timing_without_writing_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            generate(content, 'demo', 'voice', 'model', '1', False, candidate,
                     'mp3_44100_128', FakeApi())
            manifest_path = candidate / 'generation.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['utterances']['1']['cue_times'].pop()
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            player = root / 'player'

            with self.assertRaisesRegex(ElevenLabsError, 'invalid cue timing data'):
                promote(content, 'demo', candidate, '1', False, player)

            self.assertFalse((player / 'audio/01001.mp3').exists())

    def test_candidate_preview_uses_the_complete_audio_and_source_segment_visuals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = root / 'lesson.json'
            content.write_text(json.dumps(self.lesson), encoding='utf-8')
            candidate = root / 'candidate'
            generate(content, 'demo', 'voice', 'model', '1', False, candidate,
                     'mp3_44100_128', FakeApi())
            player = root / 'player'
            player.mkdir()
            (player / 'assets').mkdir()
            (player / 'lesson.js').write_text('window.LESSON = ' + json.dumps({
                'title': 'Demo', 'segments': [
                    {'caption': 'Первый…', 'frames': [{'at': 0, 'items': [{'kind': 'one'}]}]},
                    {'caption': '…и второй', 'frames': [{'at': 0, 'items': [{'kind': 'two'}]}]},
                    {'caption': 'Третий', 'frames': [{'at': 0, 'items': []}]},
                ]
            }) + ';\n')
            for name in ('index.html', 'player.js', 'player.css'):
                shutil.copyfile(ROOT / 'player' / name, player / name)
            shutil.copytree(ROOT / 'player' / 'assets', player / 'assets', dirs_exist_ok=True)

            preview = build_preview(content, 'demo', candidate, player)

            source = (preview / 'lesson.js').read_text().removeprefix('window.LESSON = ').strip().removesuffix(';')
            utterance = json.loads(source)['utterances'][0]
            self.assertEqual(utterance['caption'], 'Первый и второй')
            self.assertEqual(utterance['audio'], '../audio/1.mp3')
            self.assertEqual([cue['caption'] for cue in utterance['cues']], ['Первый…', '…и второй'])
            self.assertEqual(utterance['cues'][0]['frames'][0]['items'][0]['kind'], 'one')
            self.assertAlmostEqual(utterance['cues'][1]['at'], 0.7)

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
            self.assertEqual((player / 'audio/01001.mp3').read_bytes(), 'audio:Первый и второй'.encode())
            self.assertEqual((player / 'audio/01003.mp3').read_bytes(), 'audio:Третий'.encode())
            approved = json.loads((player / 'generation.json').read_text())['approved_utterances']
            self.assertEqual(approved['1']['provider'], 'elevenlabs')
            self.assertEqual(approved['1']['model_id'], 'model')
            self.assertEqual(approved['1']['duration'], 1.5)

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
            (audio_dir / '01003.mp3').write_bytes(b'old two')
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
            self.assertEqual((audio_dir / '01003.mp3').read_bytes(), b'old two')


if __name__ == '__main__':
    unittest.main()
