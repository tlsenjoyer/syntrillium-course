#!/usr/bin/env python3
"""Check real audio decoding and CPU transcription of six seconds of source narration."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'recovered/tools'


def main():
    os.environ.setdefault('HF_HOME', str(CACHE / 'huggingface'))
    from faster_whisper import WhisperModel  # type: ignore[import-untyped]
    from faster_whisper.audio import decode_audio  # type: ignore[import-untyped]

    audio = ROOT / 'tests/fixtures/source-narration.mp3'
    samples = decode_audio(str(audio))
    assert 5 < len(samples) / 16000 < 7, 'Expected about six seconds of decoded audio'
    model = WhisperModel('base.en', device='cpu', compute_type='int8', cpu_threads=2,
                         download_root=str(CACHE / 'whisper-models'))
    segments, _ = model.transcribe(str(audio), language='en', beam_size=5,
                                   condition_on_previous_text=False)
    text = ' '.join(segment.text.strip() for segment in segments)
    assert 'fundamentals of sound' in text.lower(), f'Unexpected transcription: {text}'
    print(f'Transcription smoke test passed: {text}')


if __name__ == '__main__':
    main()
