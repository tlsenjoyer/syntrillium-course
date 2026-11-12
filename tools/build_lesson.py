#!/usr/bin/env python3
"""Produce bundled Russian media/data for the Waveforms review lesson.

Requires Piper 1.8.0, its local Denis model, FFmpeg, and FFDec SVG frame exports.
None of these tools or models are required during learner playback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave
import xml.etree.ElementTree as ET

from waveforms import compile_visuals


ASSETS = {'sine.svg': 2850, 'complex-1.svg': 2911, 'complex-2.svg': 2913, 'ball.svg': 2844}


def remove_flash_stage(root):
    svg = '{http://www.w3.org/2000/svg}'
    stage_width = root.get('width', '').removesuffix('px')
    for group in root.findall(f'{svg}g'):
        for rect in group.findall(f'{svg}rect'):
            width = rect.get('width', '').removesuffix('px')
            if rect.get('fill') == '#ffffff' and width == stage_width:
                group.remove(rect)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_lesson(content, recovery, flash_export, model, destination):
    from piper import PiperVoice, SynthesisConfig

    lesson = json.loads(content.read_text(encoding='utf-8'))
    composition = json.loads((recovery / 'composition.json').read_text(encoding='utf-8'))
    if lesson['id'] != 'waveforms' or lesson['source']['executable_sha256'] != composition['source_sha256']:
        raise ValueError('Lesson and recovery source do not match')
    sounds = {(s['start_frame'], s['library_id'], s['member_number'])
              for s in composition['score']['sounds'] if 1003 <= s['start_frame'] < 2814}
    members = {(m['library_id'], m['member_number']): m for m in composition['members']}
    expected = {(frame, media['resource_id']) for frame, lib, num in sounds
                for media in members[lib, num]['media'] if media['present'] and media['tag'] == 'ediM'}
    supplied = [(s['source_start_frame'], s['source_resource_id']) for s in lesson['segments']]
    if set(supplied) != expected or len(supplied) != len(expected) or supplied != sorted(supplied):
        raise ValueError('Lesson does not cover the recovered Waveforms sound references in order')
    if not all(s['russian'].strip() for s in lesson['segments']):
        raise ValueError('A lesson narration segment is empty')
    visuals = compile_visuals(composition, lesson['segments'], lesson['labels'])
    ffmpeg, ffprobe = shutil.which('ffmpeg'), shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:
        raise ValueError('FFmpeg and ffprobe are required')
    vectors = {}
    for name, rid in ASSETS.items():
        source = flash_export / f'{rid:05d}-12.swf/frames/1.svg'
        tree = ET.parse(source)
        root = tree.getroot()
        # Director composites these Flash graphics without their white stage.
        remove_flash_stage(root)
        vectors[name] = (ET.tostring(root, encoding='utf-8', xml_declaration=True), digest(source))
    voice = PiperVoice.load(model)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'audio').mkdir()
    (destination / 'assets').mkdir()
    manifest = dict(source_sha256=composition['source_sha256'], content_sha256=digest(content),
                    model_sha256=digest(model), model_config_sha256=digest(Path(str(model) + '.json')),
                    voice=lesson['voice'], vectors=[], audio=[], review_status='unverified draft')
    for name, (data, source_hash) in vectors.items():
        path = destination / 'assets' / name
        path.write_bytes(data)
        manifest['vectors'].append(dict(path='assets/' + name, resource_id=ASSETS[name],
                                       exported_frame_sha256=source_hash, sha256=digest(path)))
    segments = []
    with tempfile.TemporaryDirectory(prefix='syntrillium-narration-') as temp:
        for index, segment in enumerate(lesson['segments']):
            wav_path = Path(temp) / 'narration.wav'
            with wave.open(str(wav_path), 'wb') as audio:
                voice.synthesize_wav(segment['russian'], audio,
                                     syn_config=SynthesisConfig(noise_scale=0.5, noise_w_scale=0.333))
            relative = f"audio/{segment['source_resource_id']:05d}.mp3"
            path = destination / relative
            result = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-n', '-i', str(wav_path),
                                     '-codec:a', 'libmp3lame', '-q:a', '3', str(path)],
                                    capture_output=True, text=True)
            if result.returncode:
                raise ValueError(f'Audio encoding failed: {result.stderr[:1000]}')
            duration = float(subprocess.check_output(
                [ffprobe, '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', str(path)], text=True))
            if duration <= 0:
                raise ValueError('Narration has no duration')
            segments.append(dict(id=segment['id'], caption=segment['russian'], frames=visuals[index],
                                 audio=relative, duration=duration))
            manifest['audio'].append(dict(path=relative, source_resource_id=segment['source_resource_id'],
                                          sha256=digest(path), duration=duration))
            print(f"Generated narration {len(segments)}/{len(lesson['segments'])}", flush=True)
    playback = dict(title=lesson['title'], labels=lesson['labels'], segments=segments)
    (destination / 'lesson.js').write_text('window.LESSON = ' + json.dumps(
        playback, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    (destination / 'generation.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('content', type=Path)
    parser.add_argument('destination', type=Path, help='New generated output directory')
    parser.add_argument('--recovery', type=Path, required=True)
    parser.add_argument('--flash-export', type=Path, required=True)
    parser.add_argument('--voice-model', type=Path, required=True)
    args = parser.parse_args()
    try:
        build_lesson(args.content, args.recovery, args.flash_export, args.voice_model, args.destination)
    except (OSError, ValueError, KeyError, ET.ParseError, ImportError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Lesson build failed: {error}\n')


if __name__ == '__main__':
    main()
