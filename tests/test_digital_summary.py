"""Digital Summary score coverage, bundled narration, and offline navigation."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'player/lessons/digital-summary'
sys.path.insert(0, str(ROOT / 'tools'))
from elevenlabs_audio import player_lesson, validate_candidate_record


class DigitalSummaryTests(unittest.TestCase):
    def test_bundled_score_and_narration(self):
        lesson = json.loads((ROOT / 'content/digital-summary.json').read_text())
        data = player_lesson(BUNDLE)
        manifest = json.loads((BUNDLE / 'generation.json').read_text())
        self.assertEqual((manifest['voice_id'], manifest['model_id']),
                         ('3EuKHIEZbSzrHGNmdYsx', 'eleven_v4_turbo'))
        self.assertEqual([u['id'] for u in data['utterances']], ['2444', '2450', '2762', '1648'])
        cues = {c['segment_id']: c for u in data['utterances'] for c in u['cues']}
        self.assertEqual(list(cues), ['2444', '2450', '2762', '2456', '1648', '2468'])
        self.assertFalse(any(i.get('asset') == 'leftcover'
                             for cue in cues.values() for f in cue['frames'] for i in f['items']))
        for recorded, original in zip(data['utterances'], lesson['utterances'], strict=True):
            times = validate_candidate_record(original, manifest['candidate_utterances'][recorded['id']],
                                              BUNDLE / recorded['audio'])
            self.assertEqual([c['at'] for c in recorded['cues']], [times[sid] for sid in recorded['segment_ids']])
        items = {sid: cue['frames'][-1]['items'] for sid, cue in cues.items()}
        self.assertIn('mic', [i.get('asset') for i in items['2450']])
        self.assertIn('sound-card', [i.get('asset') for i in items['2762']])
        self.assertEqual(sum(i.get('asset') == 'sample' for i in items['2456']), 11)
        self.assertEqual(sum(i.get('value') == '←' for i in items['2468']), 2)
        self.assertIn('complex-1', [i.get('asset') for i in items['2468']])

    @unittest.skipUnless(importlib.util.find_spec('playwright'), 'Player checks require Playwright')
    def test_offline_menu_audio_and_lesson_navigation(self):
        from playwright.sync_api import expect, sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'))
            page = browser.new_page(offline=True)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto((ROOT / 'player/index.html').as_uri())
            page.get_by_role('button', name='Итоги: цифровой звук', exact=True).click()
            expect(page.locator('#lesson-number')).to_have_text('7')
            expect(page.locator('#next-lesson')).to_have_attribute('data-route', '#lesson/computer-audio')
            page.evaluate('''() => {
                const audio = document.querySelector('audio');
                window.finished = [];
                document.addEventListener('ended', event => {
                    if (event.target === audio) window.finished.push(audio.src.split('/').pop());
                }, {capture: true});
                audio.defaultPlaybackRate = audio.playbackRate = 8;
            }''')
            page.locator('#toggle').click()
            expect(page.get_by_role('button', name='Повторить', exact=True)).to_be_visible(timeout=15000)
            self.assertEqual(page.evaluate('window.finished'), ['2444.mp3', '2450.mp3', '2762.mp3', '1648.mp3'])
            page.locator('#previous-lesson').click()
            expect(page.locator('#lesson-number')).to_have_text('6')
            page.locator('#next-lesson').click()
            expect(page.locator('#lesson-number')).to_have_text('7')
            page.reload()
            expect(page.locator('#lesson-number')).to_have_text('7')
            page.locator('#position').evaluate("""el => {
                el.value = '340';
                el.dispatchEvent(new Event('input', {bubbles: true}));
            }""")
            stage = page.locator('#visualization')
            expect(stage.locator('image[href$="/mic.svg"]')).to_have_count(1)
            expect(stage.locator('image[href$="/complex-1.svg"]')).to_have_count(2)
            expect(stage.locator('image[href$="/leftcover.svg"]')).to_have_count(0)
            expect(page.locator('#error')).to_be_hidden()
            self.assertEqual(errors, [])
            browser.close()


if __name__ == '__main__':
    unittest.main()
