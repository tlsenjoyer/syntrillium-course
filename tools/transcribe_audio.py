#!/usr/bin/env python3
"""Transcribe source audio locally; translation into Russian is a separate step."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audio', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', default='base.en')
    parser.add_argument('--language', default='en')
    parser.add_argument('--model-cache', type=Path, default=Path('recovered/tools/whisper-models'))
    args = parser.parse_args()
    if not args.audio.is_file():
        parser.error(f'Audio file not found: {args.audio}')
    if args.output.exists():
        parser.error(f'Output already exists: {args.output}')
    os.environ.setdefault('HF_HOME', str(args.model_cache.parent / 'huggingface'))
    from faster_whisper import WhisperModel

    model = WhisperModel(args.model, device='cpu', compute_type='int8',
                         download_root=str(args.model_cache))
    segments, info = model.transcribe(str(args.audio), language=args.language,
                                      beam_size=5, condition_on_previous_text=False)
    rows = [dict(start=s.start, end=s.end, text=s.text.strip()) for s in segments]
    result = dict(source_audio=str(args.audio),
                  source_sha256=hashlib.sha256(args.audio.read_bytes()).hexdigest(),
                  model=args.model, language=info.language, reviewed=False,
                  text=' '.join(s['text'] for s in rows), segments=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(result['text'])
    print(f'Saved unreviewed transcript: {args.output}')


if __name__ == '__main__':
    main()
