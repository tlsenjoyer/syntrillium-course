"""Verify Computer Audio and MIDI source coverage and the offline course ending."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from elevenlabs_audio import player_lesson, validate_candidate_record

LESSONS = [('computer-audio', 'Звук на компьютере', 8, list(range(2474, 2631, 6))),
           ('midi', 'MIDI', 9, [*range(2636, 2745, 6), 1886])]


class FinalLessonsTests(unittest.TestCase):
    def test_bundles_cover_the_source_and_use_aligned_local_audio(self):
        for slug, _, _, source_ids in LESSONS:
            with self.subTest(lesson=slug):
                content = json.loads((ROOT / 'content' / f'{slug}.json').read_text())
                bundle = ROOT / 'player/lessons' / slug
                data = player_lesson(bundle)
                manifest = json.loads((bundle / 'generation.json').read_text())
                self.assertEqual((manifest['voice_id'], manifest['model_id']),
                                 ('3EuKHIEZbSzrHGNmdYsx', 'eleven_v4_turbo'))
                self.assertEqual([int(c['segment_id']) for u in data['utterances'] for c in u['cues']], source_ids)
                for item, utterance in zip(data['utterances'], content['utterances'], strict=True):
                    times = validate_candidate_record(utterance, manifest['candidate_utterances'][item['id']],
                                                      bundle / item['audio'])
                    self.assertEqual([c['at'] for c in item['cues']], [times[sid] for sid in item['segment_ids']])
                    for asset in {i['asset'] for cue in item['cues'] for frame in cue['frames']
                                  for i in frame['items'] if i['kind'] == 'image'}:
                        self.assertTrue((bundle / 'assets' / f'{asset}.svg').is_file(), asset)

    @unittest.skipUnless(importlib.util.find_spec('playwright'), 'Player checks require Playwright')
    def test_computer_audio_diagram_alignment(self):
        from playwright.sync_api import expect, sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'))
            page = browser.new_page(offline=True)
            page.goto((ROOT / 'player/index.html').as_uri() + '#lesson/computer-audio')
            expect(page.locator('#lesson-title')).to_have_text('Звук на компьютере')
            stage = page.locator('#visualization')
            position = page.locator('#position')

            def seek(percent):
                position.evaluate('''(slider, value) => {
                    slider.value = value;
                    slider.dispatchEvent(new Event('input', {bubbles: true}));
                }''', percent * 10)

            def box(selector, label=None):
                element = stage.locator(selector, has_text=label).first
                return element.evaluate('''node => {
                    const {x, y, width, height} = node.getBBox();
                    return {x, y, width, height};
                }''')

            seek(39)
            line = box('text', 'Линейный вход')
            mic = box('text', 'Микрофонный вход')
            wave = box('image[href$="/complex-1.svg"]')
            self.assertEqual(line['x'], mic['x'])
            self.assertLess(mic['x'] + mic['width'], wave['x'])
            heading = box('text', 'Аналоговый сигнал на входе')
            arrow = box('text', '←')
            self.assertAlmostEqual(heading['y'] + heading['height'] / 2,
                                   arrow['y'] + arrow['height'] / 2, delta=6)

            seek(62)
            line = box('text', 'Линейный выход')
            wave = box('image[href$="/complex-1.svg"]')
            speaker = box('image[href$="/speaker.svg"]')
            mask = box('image[href$="/stage-mask.svg"]')
            self.assertLess(line['x'] + line['width'], wave['x'])
            self.assertAlmostEqual(speaker['y'] + speaker['height'] / 2,
                                   wave['y'] + wave['height'] / 2, delta=3)
            self.assertAlmostEqual(mask['x'], speaker['x'], delta=1)
            self.assertEqual(mask['width'], speaker['width'])

            seek(74)
            rows = stage.locator('text', has_text='Частота дискретизации: 44 100 Гц').locator('tspan')
            row_starts = rows.evaluate_all('nodes => nodes.map(node => node.getStartPositionOfChar(0).x)')
            self.assertEqual(len(row_starts), 3)
            self.assertAlmostEqual(min(row_starts), max(row_starts), delta=1)
            bracket = box('image[href$="/header-bracket.svg"]')
            self.assertAlmostEqual(row_starts[0], bracket['x'] + bracket['width'], delta=10)

            seek(100)
            rate = box('text', '44 100 отсчётов/с')
            bits = box('text', '× 16 бит/отсчёт')
            self.assertAlmostEqual(bits['x'] - (rate['x'] + rate['width']), 12, delta=2)
            self.assertEqual(rate['y'], bits['y'])
            browser.close()

    @unittest.skipUnless(importlib.util.find_spec('playwright'), 'Player checks require Playwright')
    def test_menu_complete_offline_playback_and_final_lesson_boundary(self):
        from playwright.sync_api import expect, sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'))
            page = browser.new_page(offline=True)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('requestfailed', lambda request: errors.append(request.url))
            url = (ROOT / 'player/index.html').as_uri()
            for slug, title, number, _ in LESSONS:
                page.goto(url)
                page.get_by_role('button', name=title, exact=True).click()
                expect(page.locator('#lesson-number')).to_have_text(str(number))
                expect(page.locator('.lesson-list a[aria-current="page"]')).to_have_text(title)
                expected = [Path(u['audio']).name for u in player_lesson(ROOT / 'player/lessons' / slug)['utterances']]
                page.evaluate('''() => {
                    const audio = document.querySelector('audio');
                    window.finished = [];
                    audio.addEventListener('ended', () => window.finished.push(audio.src.split('/').pop()), true);
                    audio.defaultPlaybackRate = audio.playbackRate = 8;
                }''')
                page.locator('#toggle').click()
                expect(page.get_by_role('button', name='Повторить', exact=True)).to_be_visible(timeout=25000)
                self.assertEqual(page.evaluate('window.finished'), expected)
            expect(page.locator('#next-lesson')).to_be_disabled()
            expect(page.locator('#visualization')).to_contain_text('www.cooledit.com')
            page.locator('#previous-lesson').click()
            expect(page.locator('#lesson-number')).to_have_text('8')
            page.locator('#next-lesson').click()
            expect(page.locator('#lesson-number')).to_have_text('9')
            page.go_back()
            expect(page.locator('#lesson-number')).to_have_text('8')
            page.reload()
            expect(page.locator('#lesson-number')).to_have_text('8')
            expect(page.locator('#error')).to_be_hidden()
            self.assertEqual(errors, [])
            browser.close()
