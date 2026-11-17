"""Bit Depth source coverage, binary tables, narration and offline playback."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bit_depth import drawing
from build_lesson import stage_audio
from elevenlabs_audio import player_lesson, validate_candidate_record
from narration import validate_utterances
from recover import recover


class BitDepthTests(unittest.TestCase):
    def test_source_coverage_visual_tables_and_validation(self):
        content = ROOT / 'content/bit-depth.json'
        lesson = json.loads(content.read_text())
        source = json.loads((ROOT / 'content/sources/bit-depth.json').read_text())
        fields = ('id', 'source_resource_id', 'source_start_frame', 'source_end_frame', 'audio_sha256')
        self.assertEqual([tuple(s[k] for k in fields) for s in lesson['segments']],
                         [tuple(s[k] for k in fields) for s in source['segments']])
        utterances = validate_utterances(lesson, lesson['segments'])
        self.assertEqual(len(lesson['segments']), 18)
        self.assertEqual(len(utterances), 13)
        self.assertTrue(all(u['russian'].endswith('.') for u in utterances))
        with tempfile.TemporaryDirectory() as directory:
            recovery, player = Path(directory) / 'recovered', Path(directory) / 'player'
            recover(ROOT / 'course.exe', recovery)
            stage_audio(content, recovery, player)
            data = player_lesson(player)
            self.assertTrue(all(u['audio'] is None for u in data['utterances']))
            cues = {c['segment_id']: c for u in data['utterances'] for c in u['cues']}
            self.assertEqual(list(cues), [s['id'] for s in lesson['segments']])
            rendered = [i.get('lines') for c in cues.values() for f in c['frames'] for i in f['items']]
            for label in lesson['labels'].values():
                self.assertIn(label, rendered)
            for sid, count in [('2330', 2), ('2336', 8), ('2354', 24)]:
                digits = [i for i in cues[sid]['frames'][-1]['items'] if i.get('lines') in (['0'], ['1'])]
                self.assertEqual(len(digits), count)
            table = next(i for i in cues['2354']['frames'][-1]['items'] if i.get('lines') == lesson['labels']['states8'])
            rows = [table['y'] + n * table['font_size'] * 1.15 for n in range(1, 9)]
            for digit in digits:
                self.assertLessEqual(min(abs(digit['y'] - y) for y in rows), 2)
            samples = lambda sid: [i['y'] for i in cues[sid]['frames'][-1]['items'] if i.get('asset') == 'sample']
            self.assertEqual(len(set(samples('2372'))), 4)
            # Seven of the eight possible levels are occupied by this source waveform.
            self.assertEqual(len(set(samples('2378'))), 7)
            html = (player / 'index.html').read_text()
            self.assertEqual(html.count('id="open-lesson"'), 1)
            self.assertNotIn('href="#lesson/sampling-rate"', html)
            with self.assertRaises(FileExistsError):
                stage_audio(content, recovery, player)
            lesson['segments'].pop()
            incomplete = Path(directory) / 'incomplete.json'
            incomplete.write_text(json.dumps(lesson))
            with self.assertRaisesRegex(ValueError, 'sound references in order'):
                stage_audio(incomplete, recovery, Path(directory) / 'bad')
        with self.assertRaisesRegex(ValueError, 'not converted'):
            drawing(dict(library_id=10, member_number=29),
                    dict(record_hex=bytes(48).hex(), x=0, y=0, width=1, height=1), {}, 4702)

    def test_bundled_candidate_narration_and_assets(self):
        player = ROOT / 'player/lessons/bit-depth'
        data = player_lesson(player)
        manifest = json.loads((player / 'generation.json').read_text())
        lesson = json.loads((ROOT / 'content/bit-depth.json').read_text())
        self.assertEqual(manifest['voice_id'], '3EuKHIEZbSzrHGNmdYsx')
        self.assertEqual(manifest['model_id'], 'eleven_v4_turbo')
        self.assertNotIn('approved_utterances', manifest)
        self.assertEqual(len(data['utterances']), 13)
        self.assertEqual([u['caption'] for u in data['utterances']], [u['russian'] for u in lesson['utterances']])
        for u, original in zip(data['utterances'], lesson['utterances']):
            times = validate_candidate_record(original, manifest['candidate_utterances'][u['id']], player / u['audio'])
            self.assertEqual([c['at'] for c in u['cues']], [times[sid] for sid in u['segment_ids']])
        for asset in manifest['vectors']:
            self.assertEqual(hashlib.sha256((player / asset['path']).read_bytes()).hexdigest(), asset['sha256'])

    @unittest.skipUnless(importlib.util.find_spec('playwright'), 'Player checks require Playwright')
    def test_offline_menu_audio_seeking_navigation_and_completion(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'))
            page = browser.new_page(offline=True)
            errors, network = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda r: network.append(r.url) if r.url.startswith(('http:', 'https:')) else None)
            page.goto((ROOT / 'player/index.html').as_uri())
            page.get_by_role('button', name='Разрядность', exact=True).click()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '6'")
            self.assertTrue(page.locator('#next-lesson').is_enabled())
            for index in range(13):
                page.locator('#toggle').click()
                page.wait_for_function("document.querySelector('audio').currentTime > 0.1")
                self.assertIn('lessons/bit-depth/audio/', page.locator('audio').get_attribute('src') or '')
                self.assertTrue(page.locator('#error').is_hidden())
                page.locator('#toggle').click()
                if index < 12:
                    page.locator('#next').click()
                    page.locator('#toggle').click()
            page.locator('#position').evaluate('''el => {
                el.value = '500';
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }''')
            utterances = player_lesson(ROOT / 'player/lessons/bit-depth')['utterances']
            offset = sum(u['duration'] for u in utterances) / 2
            for utterance in utterances:
                if offset < utterance['duration']:
                    break
                offset -= utterance['duration']
            page.wait_for_function("t => Math.abs(document.querySelector('audio').currentTime-t) < 0.05", arg=offset)
            page.screenshot(path='/tmp/bit-depth-desktop.png')
            page.set_viewport_size(dict(width=390, height=844))
            page.locator('#lesson-navigation summary').click()
            page.wait_for_function("!document.querySelector('#lesson-navigation').open")
            page.screenshot(path='/tmp/bit-depth-mobile.png')
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 390)
            page.set_viewport_size(dict(width=1280, height=720))
            page.locator('#previous-lesson').click()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '5'")
            page.locator('#next-lesson').click()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '6'")
            self.assertTrue(page.locator('audio').evaluate('a => a.paused'))
            page.go_back()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '5'")
            page.go_forward()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '6'")
            page.reload()
            page.wait_for_function("document.querySelector('#lesson-number').textContent === '6'")
            page.evaluate('''() => {
                const audio = document.querySelector('audio');
                window.endedUtterances = 0;
                audio.addEventListener('ended', () => window.endedUtterances++);
                audio.playbackRate = audio.defaultPlaybackRate = 16;
            }''')
            page.locator('#toggle').click()
            page.get_by_role('button', name='Повторить', exact=True).wait_for(timeout=30000)
            self.assertEqual(page.evaluate('window.endedUtterances'), 13)
            self.assertEqual(errors, [])
            self.assertEqual(network, [])
            browser.close()


if __name__ == '__main__':
    unittest.main()
