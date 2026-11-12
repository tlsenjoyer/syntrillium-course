"""Learner-facing checks: fresh offline launch and real lesson playback."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Player checks require Playwright')
class PlayerTests(unittest.TestCase):
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
            page.get_by_text('Урок завершён', exact=True).wait_for(timeout=90000)
            evidence = page.evaluate('window.playbackEvidence')
            self.assertEqual(evidence['ended'], 29)
            self.assertTrue({s['russian'] for s in lesson['segments']} <= set(evidence['captions']))
            self.assertEqual(errors, [])
            self.assertEqual(network, [])
            page.get_by_role('button', name='К темам курса', exact=True).click()
            self.assertTrue(page.get_by_role('heading', name='Темы курса').is_visible())
            browser.close()


if __name__ == '__main__':
    unittest.main()
