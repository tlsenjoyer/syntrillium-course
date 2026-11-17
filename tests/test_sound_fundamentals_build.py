"""Build the silent first-lesson draft from a fresh source recovery."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from typing import Any
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_lesson import stage_sound_fundamentals
from elevenlabs_audio import ElevenLabsClient, build_preview, generate, player_lesson, promote
from recover import recover
from sound_fundamentals import cone_bitmap, ear_svg


class SoundFundamentalsBuildTests(unittest.TestCase):
    temp: tempfile.TemporaryDirectory
    recovery: Path
    player: Path

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.recovery = Path(cls.temp.name) / 'recovered'
        recover(ROOT / 'course.exe', cls.recovery)
        cls.player = Path(cls.temp.name) / 'player'
        stage_sound_fundamentals(ROOT / 'content/sound-fundamentals.json', cls.recovery, cls.player)

    def test_build_preserves_all_source_cues_without_generating_audio(self):
        data = player_lesson(self.player)
        content = json.loads((ROOT / 'content/sound-fundamentals.json').read_text())
        self.assertEqual(data['id'], 'sound-fundamentals')
        self.assertEqual(len(data['utterances']), 9)
        self.assertEqual([c['segment_id'] for u in data['utterances'] for c in u['cues']],
                         [s['id'] for s in content['segments']])
        self.assertFalse(list((self.player / 'audio').iterdir()))
        self.assertTrue(all(u['audio'] is None and u['duration'] > 0 for u in data['utterances']))
        used = {i['asset'] for u in data['utterances'] for c in u['cues'] for f in c['frames']
                for i in f['items'] if i['kind'] == 'image'}
        self.assertEqual(used, {'ball', 'sine', 'ear'} | {f'cone-{n}' for n in range(18, 27)})
        for asset in used:
            ET.parse(self.player / 'assets' / f'{asset}.svg')
        html = (self.player / 'index.html').read_text()
        self.assertEqual(html.count('id="open-lesson"'), 1)
        self.assertIn('href="#lesson/sound-fundamentals"', html)
        self.assertNotIn('href="#lesson/analog-audio"', html)
        self.assertNotIn('id="open-analog-audio"', html)
        with self.assertRaises(FileExistsError):
            stage_sound_fundamentals(ROOT / 'content/sound-fundamentals.json', self.recovery, self.player)

    def test_rejects_incomplete_source_coverage_before_creating_output(self):
        content = json.loads((ROOT / 'content/sound-fundamentals.json').read_text())
        content['segments'].pop()
        source = Path(self.temp.name) / 'incomplete.json'
        source.write_text(json.dumps(content))
        destination = Path(self.temp.name) / 'incomplete'
        with self.assertRaisesRegex(ValueError, 'sound references in order'):
            stage_sound_fundamentals(source, self.recovery, destination)
        self.assertFalse(destination.exists())

    def test_asset_decoding_preserves_alpha_and_rejects_truncation(self):
        cast = (self.recovery / 'resources/00610.bin').read_bytes()
        encoded = (self.recovery / 'resources/02873.bin').read_bytes()
        width, height, rgba = cone_bitmap(cast, encoded)
        self.assertEqual((width, height), (5, 205))
        self.assertEqual(rgba[:4], bytes((17, 17, 17, 0)))
        self.assertIn(255, rgba[3::4])
        with self.assertRaises(ValueError):
            cone_bitmap(cast, b'\xff')
        with self.assertRaises(ValueError):
            cone_bitmap(b'', encoded)
        ear = (self.recovery / 'flash/02847-12.swf').read_bytes()
        self.assertIn(b'<path', ear_svg(ear))
        with self.assertRaises(ValueError):
            ear_svg(ear[:-1])
        with self.assertRaises(ValueError):
            ear_svg(b'FWS\x04')

    def test_candidate_preview_and_promotion_preserve_first_lesson_cues(self):
        with tempfile.TemporaryDirectory() as temp:
            player = Path(temp) / 'player'
            shutil.copytree(self.player, player)
            candidate = Path(temp) / 'candidate'
            content = ROOT / 'content/sound-fundamentals.json'
            text = next(u['russian'] for u in json.loads(content.read_text())['utterances'] if u['id'] == '1904')
            api = Mock(spec=ElevenLabsClient)
            api.audio_with_timestamps.return_value = (b'local-test-fixture', None, {
                'characters': list(text),
                'character_start_times_seconds': [i * 0.1 for i in range(len(text))],
                'character_end_times_seconds': [(i + 1) * 0.1 for i in range(len(text))],
            })
            generate(content, 'sound-fundamentals', 'test-voice', 'test-model', '1904', False,
                     candidate, 'mp3_44100_128', api)
            preview = build_preview(content, 'sound-fundamentals', candidate, player, '1904')
            data = player_lesson(preview)
            self.assertEqual(data['id'], 'sound-fundamentals')
            self.assertEqual([c['segment_id'] for c in data['utterances'][0]['cues']], ['1904', '1910'])
            promote(content, 'sound-fundamentals', candidate, '1904', False, player)
            utterances = player_lesson(player)['utterances']
            self.assertIsNone(utterances[0]['audio'])
            self.assertEqual(utterances[2]['audio'], 'audio/01904.mp3')
            self.assertGreater(utterances[2]['cues'][1]['at'], 0)

    @unittest.skipUnless(importlib.util.find_spec('playwright'), 'Player checks require Playwright')
    def test_offline_silent_playback_seeking_and_history(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            options: dict[str, Any] = dict(headless=True)
            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
                options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
            browser = p.chromium.launch(**options)
            context = browser.new_context(offline=True)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto((self.player / 'index.html').as_uri())
            page.get_by_role('button', name='Основы звука', exact=True).click()
            page.wait_for_url('**/index.html#lesson/sound-fundamentals')
            self.assertEqual(page.locator('#lesson-title').inner_text(), 'Основы звука')
            page.locator('#next').click()
            page.locator('#next').click()
            page.wait_for_function("document.querySelectorAll('#visualization image').length > 2")
            page.get_by_role('button', name='Приостановить', exact=True).click()
            position = page.locator('#position').input_value()
            page.wait_for_timeout(150)
            self.assertEqual(page.locator('#position').input_value(), position)
            page.locator('#position').evaluate('''element => {
                element.value = '580';
                element.dispatchEvent(new Event('input', {bubbles:true}));
                element.dispatchEvent(new Event('change', {bubbles:true}));
            }''')
            self.assertGreater(page.locator('#visualization image[href="assets/ear.svg"]').count(), 0)
            page.get_by_role('button', name='К темам курса').click()
            page.go_back()
            self.assertTrue(page.locator('#lesson').is_visible())
            self.assertEqual(page.locator('#toggle').get_attribute('aria-label'), 'Воспроизвести')
            self.assertTrue(page.locator('#error').is_hidden())
            page.locator('#position').evaluate('''element => {
                element.value = '995';
                element.dispatchEvent(new Event('input', {bubbles:true}));
                element.dispatchEvent(new Event('change', {bubbles:true}));
            }''')
            page.get_by_role('button', name='Воспроизвести', exact=True).click()
            page.get_by_role('button', name='Повторить', exact=True).wait_for()
            self.assertEqual(page.locator('#position').input_value(), '1000')
            self.assertEqual(errors, [])
            browser.close()


if __name__ == '__main__':
    unittest.main()
