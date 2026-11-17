"""Source coverage, vector conversion and offline third-lesson playback."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analog_audio import FLASH_ASSETS, solid_flash_svg
from build_lesson import stage_audio
from elevenlabs_audio import player_lesson
from narration import validate_utterances
from recover import recover


class AnalogAudioTests(unittest.TestCase):
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
        stage_audio(ROOT / 'content/analog-audio.json', cls.recovery, cls.player)

    def test_source_coverage_and_complete_speaker_utterance(self):
        lesson = json.loads((ROOT / 'content/analog-audio.json').read_text())
        source = json.loads((ROOT / 'content/sources/analog-audio.json').read_text())
        fields = ('id', 'source_resource_id', 'source_start_frame', 'source_end_frame', 'audio_sha256')
        self.assertEqual([tuple(s[k] for k in fields) for s in lesson['segments']],
                         [tuple(s[k] for k in fields) for s in source['segments']])
        utterances = validate_utterances(lesson, lesson['segments'])
        self.assertEqual(len(lesson['segments']), 8)
        self.assertEqual(len(utterances), 7)
        speaker = next(u for u in utterances if u['id'] == '2180')
        self.assertEqual(speaker['segment_ids'], ['2180', '2186'])
        self.assertTrue(all(u['russian'].endswith('.') for u in utterances))

    def test_silent_build_preserves_visual_order_and_all_original_assets(self):
        lesson = player_lesson(self.player)
        self.assertEqual(lesson['id'], 'analog-audio')
        self.assertEqual([c['segment_id'] for u in lesson['utterances'] for c in u['cues']],
                         [str(rid) for rid in range(2150, 2193, 6)])
        self.assertTrue(all(u['audio'] is None and u['duration'] > 0 for u in lesson['utterances']))
        used = {i['asset'] for u in lesson['utterances'] for c in u['cues'] for f in c['frames']
                for i in f['items'] if i['kind'] == 'image'}
        self.assertEqual(used, {'complex-2', 'leftcover', 'mic', 'speaker', 'tape-recorder'})
        for asset in used:
            ET.parse(self.player / 'assets' / f'{asset}.svg')
        cues = {c['segment_id']: c for u in lesson['utterances'] for c in u['cues']}
        assets = lambda sid: {i.get('asset') for f in cues[sid]['frames'] for i in f['items']}
        self.assertIn('mic', assets('2150'))
        self.assertNotIn('speaker', assets('2150'))
        self.assertIn('tape-recorder', assets('2168'))
        self.assertIn('speaker', assets('2180'))
        final = cues['2192']['frames'][-1]['items']
        self.assertTrue(any(i.get('lines') == ['Аналоговый звук'] for i in final))
        self.assertEqual((self.player / 'index.html').read_text().count('id="open-lesson"'), 1)
        with self.assertRaises(FileExistsError):
            stage_audio(ROOT / 'content/analog-audio.json', self.recovery, self.player)

    def test_solid_fill_conversion_and_rejection_of_truncated_input(self):
        for name, rid in FLASH_ASSETS.items():
            data = (self.recovery / 'flash' / f'{rid:05d}-12.swf').read_bytes()
            root = ET.fromstring(solid_flash_svg(data))
            paths = root.findall('{http://www.w3.org/2000/svg}path')
            self.assertEqual(len(paths), {'mic': 5, 'speaker': 9, 'tape-recorder': 35}[name])
            self.assertTrue(all(p.attrib['d'].startswith('M') for p in paths))
            with self.assertRaises(ValueError):
                solid_flash_svg(data[:-1])
            with self.assertRaises(ValueError):
                solid_flash_svg(b'')

    def test_missing_source_segment_is_rejected_before_output_is_created(self):
        lesson = json.loads((ROOT / 'content/analog-audio.json').read_text())
        lesson['segments'].pop()
        content = Path(self.temp.name) / 'incomplete.json'
        content.write_text(json.dumps(lesson))
        destination = Path(self.temp.name) / 'incomplete'
        with self.assertRaisesRegex(ValueError, 'sound references in order'):
            stage_audio(content, self.recovery, destination)
        self.assertFalse(destination.exists())

    def test_bundled_narration_and_timing_match_requested_voice_and_content(self):
        player = ROOT / 'player/lessons/analog-audio'
        lesson = player_lesson(player)
        manifest = json.loads((player / 'generation.json').read_text())
        self.assertEqual(manifest['voice_id'], '3EuKHIEZbSzrHGNmdYsx')
        self.assertEqual(manifest['model_id'], 'eleven_v4_turbo')
        content = json.loads((ROOT / 'content/analog-audio.json').read_text())
        self.assertEqual([u['caption'] for u in lesson['utterances']],
                         [u['russian'] for u in content['utterances']])
        for u in lesson['utterances']:
            record = manifest['candidate_utterances'][u['id']]
            self.assertEqual(hashlib.sha256((player / u['audio']).read_bytes()).hexdigest(), record['sha256'])
            times = [c['at'] for c in u['cues']]
            self.assertEqual(times[0], 0)
            self.assertTrue(all(a < b for a, b in zip(times, times[1:])))
            self.assertLess(times[-1], u['duration'])

    @unittest.skipUnless(importlib.util.find_spec('playwright'), 'Player checks require Playwright')
    def test_offline_lesson_navigation_audio_seeking_and_history(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            options: dict[str, Any] = dict(headless=True)
            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
                options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
            browser = p.chromium.launch(**options)
            page = browser.new_page(offline=True)
            errors = []
            network = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('request', lambda r: network.append(r.url)
                    if r.url.startswith(('https:', 'http:')) else None)
            page.goto((ROOT / 'player/index.html').as_uri())
            page.get_by_role('button', name='Аналоговый звук', exact=True).click()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '3'")
            self.assertTrue(page.locator('#previous-lesson').is_enabled())
            self.assertTrue(page.locator('#next-lesson').is_enabled())
            for u in player_lesson(ROOT / 'player/lessons/analog-audio')['utterances']:
                page.locator('#toggle').click()
                page.wait_for_function("document.querySelector('audio').currentTime > 0.1")
                self.assertIn('lessons/analog-audio/audio/', page.locator('audio').get_attribute('src'))
                self.assertGreater(page.locator('#visualization image').count(), 0)
                self.assertTrue(page.locator('#error').is_hidden())
                page.locator('#toggle').click()
                if u['id'] != '2192':
                    page.locator('#next').click()
                    page.locator('#toggle').click()
            page.locator('#position').evaluate('''el => {
                el.value = '700';
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }''')
            page.wait_for_function("document.querySelector('audio').currentTime > 0.5")
            page.locator('#previous-lesson').click()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '2'")
            self.assertTrue(page.locator('audio').evaluate('a => a.paused'))
            page.go_back()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '3'")
            page.reload()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '3'")
            self.assertEqual(page.locator('.lesson-list a[aria-current="page"]').inner_text(), 'Аналоговый звук')
            page.evaluate('''() => {
                const audio = document.querySelector('audio');
                window.endedUtterances = 0;
                audio.addEventListener('ended', () => window.endedUtterances++);
                audio.playbackRate = audio.defaultPlaybackRate = 16;
            }''')
            page.locator('#toggle').click()
            page.get_by_role('button', name='Повторить', exact=True).wait_for(timeout=15000)
            self.assertEqual(page.evaluate('window.endedUtterances'), 7)
            self.assertEqual(errors, [])
            self.assertEqual(network, [])
            browser.close()


if __name__ == '__main__':
    unittest.main()
