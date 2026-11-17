"""Learner-facing checks: fresh offline launch and real lesson playback."""
import importlib.util
import json
import os
import re
from pathlib import Path
import unittest
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Player checks require Playwright')
class PlayerTests(unittest.TestCase):
    def test_first_lesson_is_available_offline_and_switches_without_old_narration(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            options: dict[str, Any] = dict(headless=True)
            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
                options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
            browser = p.chromium.launch(**options)
            page = browser.new_page(offline=True)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto((ROOT / 'player/index.html').as_uri())
            first = page.get_by_role('button', name='Основы звука', exact=True)
            self.assertTrue(first.is_enabled())
            first.click()
            page.wait_for_function("document.querySelector('#lesson-title').textContent === 'Основы звука'")
            self.assertEqual(page.locator('#lesson-number').inner_text(), '1')
            self.assertTrue(page.locator('#previous-lesson').is_disabled())
            self.assertTrue(page.locator('#next-lesson').is_enabled())
            page.get_by_role('button', name='Воспроизвести', exact=True).click()
            page.wait_for_function("document.querySelector('audio').currentTime > 0.1")
            self.assertTrue(page.locator('audio').get_attribute('src').startswith('lessons/sound-fundamentals/audio/'))
            page.locator('#next').click()
            page.wait_for_function("document.querySelector('#visualization image') !== null")
            self.assertTrue(page.locator('#visualization image').first.get_attribute('href').startswith(
                'lessons/sound-fundamentals/assets/'))
            page.locator('#next-lesson').click()
            page.wait_for_function("document.querySelector('#lesson-title').textContent === 'Форма звуковой волны'")
            self.assertEqual(page.locator('#lesson-number').inner_text(), '2')
            self.assertTrue(page.locator('audio').evaluate('audio => audio.paused'))
            self.assertTrue(page.locator('audio').get_attribute('src').startswith('audio/'))
            page.go_back()
            page.wait_for_function("document.querySelector('#lesson-title').textContent === 'Основы звука'")
            self.assertTrue(page.locator('audio').evaluate('audio => audio.paused'))
            page.reload()
            page.wait_for_function("document.querySelector('#lesson-title').textContent === 'Основы звука'")
            self.assertEqual(page.locator('.lesson-list a[aria-current="page"]').inner_text(), 'Основы звука')
            page.locator('.lesson-list a[href="#lesson/waveforms"]').click()
            page.wait_for_function("document.querySelector('#lesson-title').textContent === 'Форма звуковой волны'")
            self.assertTrue(page.locator('#error').is_hidden())
            self.assertEqual(errors, [])
            browser.close()

    def _open_lesson(self, page):
        page.goto((ROOT / 'player/index.html').as_uri())
        page.get_by_role('button', name='Форма звуковой волны', exact=True).click()
        page.get_by_role('button', name='Воспроизвести', exact=True).click()
        page.wait_for_function("!document.querySelector('audio').paused")

    def test_transport_controls_are_stable_and_keyboard_accessible(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            options: dict[str, Any] = dict(headless=True)
            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
                options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
            browser = p.chromium.launch(**options)
            page = browser.new_page()
            self._open_lesson(page)

            toggle = page.locator('#toggle')
            self.assertEqual(toggle.inner_text(), '')
            self.assertEqual(toggle.get_attribute('aria-label'), 'Приостановить')
            self.assertEqual(page.locator('.wordmark').count(), 0)
            self.assertTrue(page.locator('footer #next-lesson').is_enabled())
            self.assertEqual(page.locator('#playback-status').count(), 0)

            toggle.click()
            page.wait_for_function("document.querySelector('audio').paused")
            page.locator('#lesson-title').evaluate("element => { element.tabIndex = -1; element.focus(); }")
            page.keyboard.press('Space')
            page.wait_for_function("!document.querySelector('audio').paused")

            evidence = page.evaluate('''() => {
                const audio = document.querySelector('audio');
                const position = document.querySelector('#position');
                let loads = 0;
                const load = audio.load.bind(audio);
                audio.load = () => { loads += 1; load(); };
                position.value = '100';
                for (const value of ['101', '102', '103', '104']) {
                    position.value = value;
                    position.dispatchEvent(new Event('input', {bubbles: true}));
                }
                const labelDuringDrag = document.querySelector('#toggle').getAttribute('aria-label');
                const loadsDuringDrag = loads;
                position.dispatchEvent(new Event('change', {bubbles: true}));
                return {loadsDuringDrag, loadsAfterCommit: loads, labelDuringDrag};
            }''')
            self.assertEqual(evidence, {
                'loadsDuringDrag': 0, 'loadsAfterCommit': 1,
                'labelDuringDrag': 'Приостановить',
            })
            browser.close()

    def test_lesson_routes_preserve_history_captions_and_opening_visual(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            options: dict[str, Any] = dict(headless=True)
            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
                options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
            browser = p.chromium.launch(**options)
            page = browser.new_page()
            page.goto((ROOT / 'player/index.html').as_uri())
            page.get_by_role('button', name='Форма звуковой волны', exact=True).click()
            page.wait_for_url('**/index.html#lesson/waveforms')
            self.assertTrue(page.locator('audio').evaluate('audio => audio.paused'))
            page.get_by_role('button', name='Воспроизвести', exact=True).click()
            page.wait_for_function("!document.querySelector('audio').paused")

            self.assertEqual(page.locator('#visualization image[href="assets/ball.svg"]').count(), 0)
            self.assertEqual(page.locator('#captions-toggle').get_attribute('aria-pressed'), 'true')
            page.get_by_role('button', name='Субтитры').click()
            self.assertTrue(page.locator('#caption').is_hidden())
            self.assertEqual(page.locator('#captions-toggle').get_attribute('aria-pressed'), 'false')
            page.reload()
            page.wait_for_url('**/index.html#lesson/waveforms')
            self.assertTrue(page.locator('#caption').is_hidden())

            page.get_by_role('button', name='К темам курса').click()
            page.wait_for_url(re.compile(r'/index\.html#?$'))
            page.wait_for_function("document.querySelector('audio').paused")
            page.go_back()
            page.wait_for_url('**/index.html#lesson/waveforms')
            self.assertTrue(page.locator('#lesson').is_visible())
            self.assertTrue(page.locator('#caption').is_hidden())
            page.go_forward()
            page.wait_for_url(re.compile(r'/index\.html#?$'))
            self.assertTrue(page.get_by_role('heading', name='Темы курса').is_visible())
            browser.close()

    def test_visual_cues_change_inside_one_continuous_utterance_recording(self):
        from playwright.sync_api import sync_playwright
        utterance = {
            'id': 'cycle', 'caption': 'Полное предложение.',
            'audio': 'audio/01982.mp3', 'duration': 6.2,
            'cues': [
                {'at': 0, 'caption': 'Начало', 'frames': [{'at': 0, 'items': []}]},
                {'at': 0.5, 'caption': 'Продолжение', 'frames': [{'at': 0, 'items': []}]},
            ],
        }
        next_utterance = {
            'id': 'next', 'caption': 'Следующее предложение.',
            'audio': 'audio/01988.mp3', 'duration': 3.2,
            'cues': [{'at': 0, 'caption': 'Следующее предложение.',
                      'frames': [{'at': 0, 'items': []}]}],
        }
        lesson_script = '''
            Object.defineProperty(window, 'LESSON', {
                configurable: true, get: () => ({title: 'Форма звуковой волны', utterances: %s}),
                set: () => {}
            });
        ''' % json.dumps([utterance, next_utterance], ensure_ascii=False)
        with sync_playwright() as p:
            options: dict[str, Any] = dict(headless=True)
            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
                options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
            browser = p.chromium.launch(**options)
            page = browser.new_page()
            page.add_init_script(lesson_script)
            page.goto((ROOT / 'player/index.html').as_uri())
            page.get_by_role('button', name='Форма звуковой волны', exact=True).click()
            page.get_by_role('button', name='Воспроизвести', exact=True).click()
            page.wait_for_function("document.querySelector('audio').readyState >= 1")
            page.get_by_role('button', name='Приостановить').click()
            audio = page.locator('audio')
            source = audio.get_attribute('src')
            audio.evaluate("element => { element.currentTime = 1; element.dispatchEvent(new Event('timeupdate')); }")
            self.assertEqual(page.locator('#caption').text_content(), 'Полное предложение.')
            self.assertEqual(page.locator('#visualization desc').text_content(), 'Продолжение')
            self.assertEqual(page.locator('#visualization title').count(), 0)
            self.assertEqual(audio.get_attribute('src'), source)
            page.get_by_role('button', name='Следующая фраза').click()
            self.assertEqual(page.locator('#caption').text_content(), 'Следующее предложение.')
            self.assertNotEqual(audio.get_attribute('src'), source)
            browser.close()

    def test_russian_lesson_completes_with_every_narration_clip_offline(self):
        from playwright.sync_api import sync_playwright
        lesson = json.loads((ROOT / 'content/waveforms.json').read_text(encoding='utf-8'))
        with sync_playwright() as p:
            options: dict[str, Any] = dict(headless=True)
            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
                options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
            browser = p.chromium.launch(**options)
            context = browser.new_context(offline=True)
            page = context.new_page()
            errors = []
            network = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: network.append(request.url)
                    if request.url.startswith(('http:', 'https:')) else None)
            page.goto((ROOT / 'player/index.html').as_uri())
            page.get_by_role('button', name='Форма звуковой волны', exact=True).click()
            page.evaluate('''() => {
                window.playbackEvidence = {ended: 0, captions: [document.querySelector('#caption').textContent]};
                document.querySelector('audio').addEventListener('ended', () => window.playbackEvidence.ended++);
                new MutationObserver(() => window.playbackEvidence.captions.push(document.querySelector('#caption').textContent))
                    .observe(document.querySelector('#caption'), {childList: true, subtree: true});
                document.querySelector('audio').playbackRate = 16;
                document.querySelector('audio').defaultPlaybackRate = 16;
            }''')
            page.get_by_role('button', name='Воспроизвести', exact=True).click()
            page.get_by_role('button', name='Повторить', exact=True).wait_for(timeout=90000)
            evidence = page.evaluate('window.playbackEvidence')
            self.assertEqual(evidence['ended'], len(lesson['utterances']))
            self.assertTrue({s['russian'] for s in lesson['utterances']} <= set(evidence['captions']))
            self.assertEqual(errors, [])
            self.assertEqual(network, [])
            self.assertEqual(page.get_by_text('Урок завершён', exact=True).count(), 0)
            self.assertEqual(page.get_by_role('button', name='Повторить урок', exact=True).count(), 0)
            self.assertTrue(page.locator('#next-lesson').is_enabled())
            page.get_by_role('button', name='Повторить', exact=True).click()
            page.wait_for_function("!document.querySelector('audio').paused")
            self.assertEqual(page.locator('#visualization').evaluate("element => getComputedStyle(element).position"), 'static')
            page.get_by_role('button', name='К темам курса', exact=True).click()
            self.assertTrue(page.get_by_role('heading', name='Темы курса').is_visible())
            browser.close()


if __name__ == '__main__':
    unittest.main()
