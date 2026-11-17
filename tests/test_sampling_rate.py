"""Source coverage, sampling visuals, narration and offline lesson-five playback."""
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
from build_lesson import stage_audio
from sampling_rate import drawing
from elevenlabs_audio import player_lesson, validate_candidate_record
from narration import validate_utterances
from recover import recover


class SamplingRateTests(unittest.TestCase):
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
        stage_audio(ROOT / 'content/sampling-rate.json', cls.recovery, cls.player)

    def test_source_coverage_and_uninterrupted_sentences(self):
        lesson = json.loads((ROOT / 'content/sampling-rate.json').read_text())
        source = json.loads((ROOT / 'content/sources/sampling-rate.json').read_text())
        fields = ('id', 'source_resource_id', 'source_start_frame', 'source_end_frame', 'audio_sha256')
        self.assertEqual([tuple(s[k] for k in fields) for s in lesson['segments']],
                         [tuple(s[k] for k in fields) for s in source['segments']])
        utterances = validate_utterances(lesson, lesson['segments'])
        self.assertEqual([u['segment_ids'] for u in utterances],
                         [['2228'], ['2234'], ['2240'], ['2246'], ['2252', '2258'],
                          ['2264', '2270'], ['2276', '2282'], ['2288'], ['2294'], ['2300']])
        for u in utterances:
            self.assertTrue(u['russian'].endswith('.'))

    def test_sampling_build_preserves_visual_order_and_labels(self):
        data = player_lesson(self.player)
        self.assertEqual(data['id'], 'sampling-rate')
        self.assertTrue(all(u['audio'] is None and u['duration'] > 0 for u in data['utterances']))
        cues = {c['segment_id']: c for u in data['utterances'] for c in u['cues']}
        self.assertEqual(list(cues), [str(rid) for rid in range(2228, 2301, 6)])
        samples = lambda f: [i for i in f['items'] if i.get('asset') == 'sample']
        doubling = cues['2252']['frames']
        self.assertEqual(len(samples(doubling[0])), 21)
        self.assertEqual(len(samples(doubling[-1])), 41)
        self.assertEqual([len(samples(f)) for f in doubling], sorted(len(samples(f)) for f in doubling))
        labels = json.loads((ROOT / 'content/sampling-rate.json').read_text())['labels']
        rendered = [i.get('lines') for c in cues.values() for f in c['frames'] for i in f['items']]
        for lines in labels.values():
            self.assertIn(lines, rendered)
        for asset in self.player.glob('assets/*.svg'):
            ET.parse(asset)
        html = (self.player / 'index.html').read_text()
        self.assertEqual(html.count('id="open-lesson"'), 1)
        self.assertNotIn('href="#lesson/digital-audio"', html)
        with self.assertRaises(FileExistsError):
            stage_audio(ROOT / 'content/sampling-rate.json', self.recovery, self.player)

    def test_incomplete_coverage_and_unknown_visuals_are_rejected(self):
        lesson = json.loads((ROOT / 'content/sampling-rate.json').read_text())
        lesson['segments'].pop()
        path = Path(self.temp.name) / 'incomplete.json'
        path.write_text(json.dumps(lesson))
        destination = Path(self.temp.name) / 'incomplete'
        with self.assertRaisesRegex(ValueError, 'sound references in order'):
            stage_audio(path, self.recovery, destination)
        self.assertFalse(destination.exists())
        with self.assertRaisesRegex(ValueError, 'not converted'):
            drawing(dict(library_id=8, member_number=56),
                    dict(record_hex=bytes(48).hex(), x=0, y=0, width=1, height=1), {}, 3513)

    def test_bundled_narration_matches_requested_voice_and_content(self):
        player = ROOT / 'player/lessons/sampling-rate'
        data = player_lesson(player)
        manifest = json.loads((player / 'generation.json').read_text())
        content = json.loads((ROOT / 'content/sampling-rate.json').read_text())
        self.assertEqual(manifest['voice_id'], '3EuKHIEZbSzrHGNmdYsx')
        self.assertEqual(manifest['model_id'], 'eleven_v4_turbo')
        self.assertNotIn('approved_utterances', manifest)
        self.assertEqual([u['caption'] for u in data['utterances']], [u['russian'] for u in content['utterances']])
        for u, original in zip(data['utterances'], content['utterances']):
            times = validate_candidate_record(original, manifest['candidate_utterances'][u['id']], player / u['audio'])
            self.assertEqual([c['at'] for c in u['cues']], [times[sid] for sid in u['segment_ids']])
        for asset in manifest['vectors']:
            self.assertEqual(hashlib.sha256((player / asset['path']).read_bytes()).hexdigest(), asset['sha256'])

    @unittest.skipUnless(importlib.util.find_spec('playwright'), 'Player checks require Playwright')
    def test_offline_menu_navigation_seeking_history_and_completion(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            options: dict[str, Any] = dict(headless=True)
            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
                options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
            browser = p.chromium.launch(**options)
            page = browser.new_page(offline=True)
            errors, network = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('request', lambda r: network.append(r.url)
                    if r.url.startswith(('https:', 'http:')) else None)
            page.goto((ROOT / 'player/index.html').as_uri())
            page.get_by_role('button', name='Частота дискретизации', exact=True).click()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '5'")
            self.assertTrue(page.locator('#previous-lesson').is_enabled())
            self.assertTrue(page.locator('#next-lesson').is_disabled())
            for index in range(10):
                page.locator('#toggle').click()
                page.wait_for_function("document.querySelector('audio').currentTime > 0.1")
                audio_src = page.locator('audio').get_attribute('src')
                assert audio_src is not None
                self.assertIn('lessons/sampling-rate/audio/', audio_src)
                self.assertTrue(page.locator('#error').is_hidden())
                page.locator('#toggle').click()
                if index < 9:
                    page.locator('#next').click()
                    page.locator('#toggle').click()
            page.locator('#position').evaluate('''el => {
                el.value = '700';
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }''')
            utterances = player_lesson(ROOT / 'player/lessons/sampling-rate')['utterances']
            offset = sum(u['duration'] for u in utterances) * 0.7
            for utterance in utterances:
                if offset < utterance['duration']:
                    break
                offset -= utterance['duration']
            page.wait_for_function("expected => Math.abs(document.querySelector('audio').currentTime - expected) < 0.05",
                                   arg=offset)
            seek_source = page.locator('audio').get_attribute('src')
            assert seek_source is not None
            self.assertIn(utterance['audio'], seek_source)
            page.screenshot(path='/tmp/sampling-rate-desktop.png')
            page.set_viewport_size(dict(width=390, height=844))
            page.locator('#lesson-navigation summary').click()
            page.wait_for_function("!document.querySelector('#lesson-navigation').open")
            page.screenshot(path='/tmp/sampling-rate-mobile.png')
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 390)
            page.set_viewport_size(dict(width=1280, height=720))
            page.locator('#previous-lesson').click()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '4'")
            self.assertTrue(page.locator('audio').evaluate('a => a.paused'))
            page.locator('#next-lesson').click()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '5'")
            page.go_back()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '4'")
            page.go_forward()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '5'")
            page.reload()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '5'")
            self.assertEqual(page.locator('.lesson-list a[aria-current="page"]').inner_text(), 'Частота дискретизации')
            page.evaluate('''() => {
                const audio = document.querySelector('audio');
                window.endedUtterances = 0;
                audio.addEventListener('ended', () => window.endedUtterances++);
                audio.playbackRate = audio.defaultPlaybackRate = 16;
            }''')
            page.locator('#toggle').click()
            page.get_by_role('button', name='Повторить', exact=True).wait_for(timeout=30000)
            self.assertEqual(page.evaluate('window.endedUtterances'), 10)
            self.assertEqual(errors, [])
            self.assertEqual(network, [])
            browser.close()


if __name__ == '__main__':
    unittest.main()
