#!/usr/bin/env python3
"""Build narrated Waveforms media or silent lesson review players.

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
from narration import NarrationError, anchor_position, validate_utterances
from computer_audio import (COMPUTER_BITMAPS, COMPUTER_AUDIO_RANGE, MIDI_RANGE,
                            compile_computer_visuals, compile_midi_visuals)


ASSETS = {'sine.svg': 2850, 'complex-1.svg': 2911, 'complex-2.svg': 2913, 'ball.svg': 2844}
STAGED_TOPICS = {
    'analog-audio': ('Analog Audio', 'Аналоговый звук', 2814, 3389),
    'digital-audio': ('Digital Audio', 'Цифровой звук', 3389, 3697),
    'sampling-rate': ('Sampling Rate', 'Частота дискретизации', 3697, 4684),
    'bit-depth': ('Bit Depth', 'Разрядность', 4684, 5985),
    'digital-summary': ('Digital Summary', 'Итоги: цифровой звук', 5985, 6377),
    'computer-audio': ('Computer Audio', 'Звук на компьютере', *COMPUTER_AUDIO_RANGE),
    'midi': ('MIDI', 'MIDI', *MIDI_RANGE),
}


def stage_audio(content, recovery, destination):
    """Build audio lesson visuals with silent, provisional narration timing."""
    from analog_audio import FLASH_ASSETS, solid_flash_svg
    from analog_audio import compile_visuals
    from digital_audio import compile_visuals as compile_digital_visuals
    from digital_summary import compile_visuals as compile_summary_visuals
    from composition import SOURCE_SHA256
    from sampling_rate import compile_visuals as compile_sampling_visuals
    from bit_depth import compile_visuals as compile_bit_depth_visuals
    from sound_fundamentals import bitmap_svg, cone_bitmap

    lesson = json.loads(content.read_text(encoding='utf-8'))
    composition = json.loads((recovery / 'composition.json').read_text(encoding='utf-8'))
    digital = lesson['id'] == 'digital-audio'
    sampling = lesson['id'] == 'sampling-rate'
    bit_depth = lesson['id'] == 'bit-depth'
    summary = lesson['id'] == 'digital-summary'
    computer = lesson['id'] == 'computer-audio'
    midi = lesson['id'] == 'midi'
    title, _, start, end = STAGED_TOPICS.get(lesson['id'], ('Unknown', '', 0, 0))
    if (not start or composition['source_sha256'] != SOURCE_SHA256
            or lesson['source']['executable_sha256'] != SOURCE_SHA256):
        raise ValueError(f'Lesson and recovery source do not match {title}')
    members = {(m['library_id'], m['member_number']): m for m in composition['members']}
    sounds = [s for s in composition['score']['sounds'] if start <= s['start_frame'] < end]
    expected = [(s['start_frame'], media['resource_id']) for s in sounds
                for media in members[s['library_id'], s['member_number']]['media']
                if media['present'] and media['tag'] == 'ediM']
    supplied = [(s['source_start_frame'], s['source_resource_id']) for s in lesson['segments']]
    if supplied != expected:
        raise ValueError(f'Lesson does not cover the recovered {title} sound references in order')
    utterances = validate_utterances(lesson, lesson['segments'])
    shell = Path(__file__).resolve().parents[1] / 'player'
    names = ('complex-1.svg',) if sampling or bit_depth or summary or computer else (
        ('complex-1.svg', 'complex-2.svg') if digital else (() if midi else ('complex-2.svg',)))
    assets = {name: (shell / 'assets' / name).read_bytes() for name in names}
    provenance = [dict(path=f'assets/{name}', reused_from=f'player/assets/{name}',
                       source_sha256=digest(shell / 'assets' / name)) for name in names]
    if summary:
        flash_assets = {'mic': FLASH_ASSETS['mic'], 'sound-card': 2989}
    elif computer:
        flash_assets = {'sound-card': 2989, 'speaker': FLASH_ASSETS['speaker']}
    elif midi:
        flash_assets = {'sound-card': 2989, 'tape-recorder': FLASH_ASSETS['tape-recorder']}
    else:
        flash_assets = {} if sampling or bit_depth else ({'speaker': FLASH_ASSETS['speaker']} if digital else FLASH_ASSETS)
    for name, rid in flash_assets.items():
        source = recovery / 'flash' / f'{rid:05d}-12.swf'
        assets[name + '.svg'] = solid_flash_svg(source.read_bytes())
        provenance.append(dict(path=f'assets/{name}.svg', resource_id=rid, source_sha256=digest(source)))
    if not (sampling or bit_depth or midi):
        member = members[8, 39]
        cast = recovery / 'resources' / f"{member['resource_id']:05d}.bin"
        bitmap = recovery / 'resources/02915.bin'
        width, height, _ = cone_bitmap(cast.read_bytes(), bitmap.read_bytes())
        # The source background-colored mask must match the adapted player's stage.
        assets['leftcover.svg'] = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
                                   f'<path fill="#eef2f6" d="M0 0H{width}V{height}H0Z"/></svg>\n').encode()
        provenance.append(dict(path='assets/leftcover.svg', resource_id=2915, source_sha256=digest(bitmap),
                               cast_resource_id=member['resource_id'], cast_sha256=digest(cast),
                               adaptation='Background mask recolored to player stage #eef2f6.'))
    if digital or sampling or bit_depth or summary or computer:
        assets['sample.svg'] = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 5 5"><path fill="#076938" d="M0 0H5V5H0Z"/></svg>\n'
        provenance.append(dict(path='assets/sample.svg', cast_resource_id=858,
                               cast_sha256=digest(recovery / 'resources/00858.bin'),
                               adaptation='Original primitive square, source RGB #076938.'))
    if computer or midi:
        rid = 2947 if computer else 2977
        assets['stage-mask.svg'] = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><path fill="#eef2f6" d="M0 0H1V1H0Z"/></svg>\n'
        provenance.append(dict(path='assets/stage-mask.svg', resource_id=rid,
                               source_sha256=digest(recovery / 'resources' / f'{rid:05d}.bin'),
                               adaptation='Background mask recolored to the adapted stage.'))
    if computer:
        for name, (cast_id, rid) in COMPUTER_BITMAPS.items():
            cast = recovery / 'resources' / f'{cast_id:05d}.bin'
            bitmap = recovery / 'resources' / f'{rid:05d}.bin'
            width, height, rgba = cone_bitmap(cast.read_bytes(), bitmap.read_bytes())
            pixels = bytearray(rgba)
            for i in range(0, len(pixels), 4):
                if pixels[i:i+3] == b'\xff\xff\xff':
                    pixels[i+3] = 0
            assets[f'{name}.svg'] = bitmap_svg(width, height, pixels)
            provenance.append(dict(path=f'assets/{name}.svg', resource_id=rid,
                                   source_sha256=digest(bitmap), cast_resource_id=cast_id,
                                   cast_sha256=digest(cast), adaptation='White matte made transparent.'))
    if midi:
        for name, rid in {'quarter-note': 2967, 'treble-clef': 2969,
                          'cool-edit-2000': 3016, 'cool-edit-pro': 3018}.items():
            source = recovery / 'flash' / f'{rid:05d}-12.swf'
            exported = shell / 'lessons/midi/assets' / f'{name}.svg'
            assets[exported.name] = exported.read_bytes()
            provenance.append(dict(path=f'assets/{exported.name}', resource_id=rid,
                                   source_sha256=digest(source),
                                   adaptation='Rendered first Flash frame on a transparent stage.'))
    compiler = {'bit-depth': compile_bit_depth_visuals, 'sampling-rate': compile_sampling_visuals,
                'digital-summary': compile_summary_visuals,
                'computer-audio': compile_computer_visuals, 'midi': compile_midi_visuals,
                'digital-audio': compile_digital_visuals}.get(lesson['id'], compile_visuals)
    labels = lesson['labels']
    if midi:
        previous = json.loads((shell.parent / 'content/computer-audio.json').read_text(encoding='utf-8'))
        labels = dict(labels, computerAudio=previous['labels'])
    visuals = compiler(composition, lesson['segments'], labels)
    segments = {str(s['id']): s for s in lesson['segments']}
    frames = {str(s['id']): f for s, f in zip(lesson['segments'], visuals)}
    playback = []
    for utterance in utterances:
        duration = sum(segments[str(sid)]['duration_seconds'] for sid in utterance['segment_ids'])
        playback.append(dict(id=str(utterance['id']), segment_ids=utterance['segment_ids'],
                             caption=utterance['russian'], audio=None, duration=duration,
                             cues=compile_utterance_cues(utterance, segments, frames, duration)))
    data = dict(id=lesson['id'], title=lesson['title'], labels=lesson['labels'], utterances=playback,
                review_status='draft', timing_status='estimated')
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'assets').mkdir()
    (destination / 'audio').mkdir()
    for name, body in assets.items():
        (destination / 'assets' / name).write_bytes(body)
    for name in ('player.js', 'player.css'):
        shutil.copyfile(shell / name, destination / name)
    html = (shell / 'index.html').read_text(encoding='utf-8').replace('<body data-course>', '<body>')
    html = html.replace('id="open-lesson"', 'disabled')
    for number, (lesson_id, (_, other_title, _, _)) in enumerate(STAGED_TOPICS.items(), start=3):
        html = html.replace(f'id="open-{lesson_id}" data-lesson="{lesson_id}"',
                            'id="open-lesson"' if lesson_id == lesson['id'] else 'disabled')
        if lesson_id != lesson['id']:
            html = html.replace(f'<a href="#lesson/{lesson_id}">{other_title}</a>',
                                f'<span aria-disabled="true">{other_title}</span>')
        else:
            html = html.replace('id="lesson-number">2', f'id="lesson-number">{number}')
    html = html.replace('id="open-sound-fundamentals" data-lesson="sound-fundamentals"', 'disabled')
    html = html.replace('<a href="#lesson/sound-fundamentals">Основы звука</a>',
                        '<span aria-disabled="true">Основы звука</span>')
    html = html.replace('<a href="#lesson/waveforms" aria-current="page">Форма звуковой волны</a>',
                        '<span aria-disabled="true">Форма звуковой волны</span>')
    html = html.replace('Для проверки доступны все девять уроков.',
                        f'Черновик урока «{lesson["title"]}» для проверки.')
    (destination / 'index.html').write_text(html, encoding='utf-8')
    (destination / 'lesson.js').write_text('window.LESSON = ' + json.dumps(
        data, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
    for record in provenance:
        record['sha256'] = digest(destination / record['path'])
    manifest = dict(source_sha256=SOURCE_SHA256, content_sha256=digest(content), vectors=provenance,
                    audio=[], review_status='unverified draft', timing_status='estimated',
                    limitations=['Original Windows playback comparison unavailable on this host.',
                                 'Score event order is preserved; within-cue timing is provisional.',
                                 'Transcription, translation and narration require listening review.'])
    if digital:
        manifest['reconstructed_visuals'] = [dict(
            name='White Pop', resource_id=2927, source_sha256=digest(recovery / 'resources/02927.bin'),
            adaptation='Three-frame white-circle pulse; original playback comparison pending.')]
        manifest['limitations'].append('White Pop film-loop pulse is reconstructed and unverified.')
    (destination / 'generation.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


def stage_sound_fundamentals(content, recovery, destination):
    """Build a separate, silent review player; never generate or approve speech."""
    from sound_fundamentals import bitmap_svg, cone_bitmap, ear_svg
    from sound_fundamentals import compile_visuals as compile_sound_visuals
    from composition import SOURCE_SHA256

    lesson = json.loads(content.read_text(encoding='utf-8'))
    composition = json.loads((recovery / 'composition.json').read_text(encoding='utf-8'))
    if (lesson['id'] != 'sound-fundamentals' or composition['source_sha256'] != SOURCE_SHA256
            or lesson['source']['executable_sha256'] != SOURCE_SHA256):
        raise ValueError('Lesson and recovery source do not match Sound Fundamentals')
    members = {(m['library_id'], m['member_number']): m for m in composition['members']}
    sounds = [s for s in composition['score']['sounds'] if 130 <= s['start_frame'] < 1003]
    expected = {(s['start_frame'], media['resource_id']) for s in sounds
                for media in members[s['library_id'], s['member_number']]['media']
                if media['present'] and media['tag'] == 'ediM'}
    supplied = [(s['source_start_frame'], s['source_resource_id']) for s in lesson['segments']]
    if set(supplied) != expected or len(supplied) != len(expected) or supplied != sorted(supplied):
        raise ValueError('Lesson does not cover the recovered Sound Fundamentals sound references in order')
    utterances = validate_utterances(lesson, lesson['segments'])
    shell = Path(__file__).resolve().parents[1] / 'player'
    assets = {}
    sizes = {}
    provenance = []
    for number in range(18, 27):
        member = members[8, number]
        rid = next(m['resource_id'] for m in member['media'] if m['tag'] == 'BITD' and m['present'])
        cast_path = recovery / 'resources' / f"{member['resource_id']:05d}.bin"
        media_path = recovery / 'resources' / f'{rid:05d}.bin'
        width, height, pixels = cone_bitmap(cast_path.read_bytes(), media_path.read_bytes())
        sizes[number] = width, height
        name = f'cone-{number}.svg'
        assets[name] = bitmap_svg(width, height, pixels)
        provenance.append(dict(path=f'assets/{name}', resource_id=rid, source_sha256=digest(media_path),
                               cast_resource_id=member['resource_id'], cast_sha256=digest(cast_path)))
    ear = recovery / 'flash' / '02847-12.swf'
    assets['ear.svg'] = ear_svg(ear.read_bytes())
    provenance.append(dict(path='assets/ear.svg', resource_id=2847, source_sha256=digest(ear)))
    for name in ('ball.svg', 'sine.svg'):
        assets[name] = (shell / 'assets' / name).read_bytes()
        provenance.append(dict(path=f'assets/{name}', reused_from=f'player/assets/{name}',
                               source_sha256=digest(shell / 'assets' / name)))
    visuals = compile_sound_visuals(composition, lesson['segments'], lesson['labels'], sizes)
    segments = {str(s['id']): s for s in lesson['segments']}
    frames = {str(s['id']): f for s, f in zip(lesson['segments'], visuals)}
    playback = []
    for utterance in utterances:
        duration = sum(segments[str(sid)]['duration_seconds'] for sid in utterance['segment_ids'])
        playback.append(dict(id=str(utterance['id']), segment_ids=utterance['segment_ids'],
                             caption=utterance['russian'], audio=None, duration=duration,
                             cues=compile_utterance_cues(utterance, segments, frames, duration)))
    data = dict(id=lesson['id'], title=lesson['title'], labels=lesson['labels'], utterances=playback,
                review_status='draft', timing_status='estimated')
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'assets').mkdir()
    (destination / 'audio').mkdir()
    for name, body in assets.items():
        (destination / 'assets' / name).write_bytes(body)
    for name in ('player.js', 'player.css'):
        shutil.copyfile(shell / name, destination / name)
    html = (shell / 'index.html').read_text(encoding='utf-8')
    html = html.replace('<body data-course>', '<body>')
    html = html.replace('<li><button id="open-sound-fundamentals" data-lesson="sound-fundamentals">Основы звука</button></li>',
                        '<li><button id="open-lesson" aria-label="Основы звука">Основы звука</button></li>')
    html = html.replace('<button id="open-lesson" aria-label="Форма звуковой волны">', '<button disabled>')
    html = html.replace('<a href="#lesson/sound-fundamentals">Основы звука</a>',
                        '<a href="#lesson/sound-fundamentals" aria-current="page">Основы звука</a>')
    html = html.replace('<a href="#lesson/waveforms" aria-current="page">Форма звуковой волны</a>',
                        '<span aria-disabled="true">Форма звуковой волны</span>')
    html = html.replace('<button id="open-analog-audio" data-lesson="analog-audio">', '<button disabled>')
    html = html.replace('<a href="#lesson/analog-audio">Аналоговый звук</a>',
                        '<span aria-disabled="true">Аналоговый звук</span>')
    html = html.replace('<button id="open-digital-audio" data-lesson="digital-audio">', '<button disabled>')
    html = html.replace('<a href="#lesson/digital-audio">Цифровой звук</a>',
                        '<span aria-disabled="true">Цифровой звук</span>')
    html = html.replace('<button id="open-bit-depth" data-lesson="bit-depth">', '<button disabled>')
    html = html.replace('<a href="#lesson/bit-depth">Разрядность</a>',
                        '<span aria-disabled="true">Разрядность</span>')
    html = html.replace('<button id="open-digital-summary" data-lesson="digital-summary">', '<button disabled>')
    html = html.replace('<a href="#lesson/digital-summary">Итоги: цифровой звук</a>',
                        '<span aria-disabled="true">Итоги: цифровой звук</span>')
    html = html.replace('<button id="open-sampling-rate" data-lesson="sampling-rate">', '<button disabled>')
    html = html.replace('<a href="#lesson/sampling-rate">Частота дискретизации</a>',
                        '<span aria-disabled="true">Частота дискретизации</span>')
    for lesson_id in ('computer-audio', 'midi'):
        other_title = STAGED_TOPICS[lesson_id][1]
        html = html.replace(f'id="open-{lesson_id}" data-lesson="{lesson_id}"', 'disabled')
        html = html.replace(f'<a href="#lesson/{lesson_id}">{other_title}</a>',
                            f'<span aria-disabled="true">{other_title}</span>')
    html = html.replace('Для проверки доступны все девять уроков.\n'
                        '          Записи и изображения находятся в папке курса и воспроизводятся без интернета.',
                        'Черновик первого урока «Основы звука». Проверьте текст, '
                        'визуализации и последовательность объяснений.')
    html = html.replace('id="lesson-number">2', 'id="lesson-number">1').replace('Визуализация звуковой волны', 'Визуализация основ звука')
    html = html.replace('viewBox="0 65 550 270"', 'viewBox="0 65 550 290"')
    html = html.replace('← Предыдущий урок: Основы звука', '← Предыдущий урок')
    html = html.replace('Следующий урок: Аналоговый звук →', 'Следующий урок: Форма звуковой волны →')
    html = html.replace('<h1 id="lesson-title">Форма звуковой волны</h1>',
                        '<h1 id="lesson-title">Основы звука</h1>')
    html = html.replace('<span id="lesson-duration"></span></p>',
                        '<span id="lesson-duration"></span><br><span id="narration-note"></span></p>')
    (destination / 'index.html').write_text(html, encoding='utf-8')
    (destination / 'lesson.js').write_text('window.LESSON = ' + json.dumps(
        data, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
    for record in provenance:
        record['sha256'] = digest(destination / record['path'])
    manifest = dict(source_sha256=SOURCE_SHA256, content_sha256=digest(content), vectors=provenance,
                    audio=[], review_status='unverified draft', timing_status='estimated',
                    limitations=['Original continuous playback comparison unavailable in this session.',
                                 'Pressure-wave motion is reconstructed; source frame timing is provisional.',
                                 'Transcription, translation, scientific wording and narration are unapproved.'])
    (destination / 'generation.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


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


def compile_utterance_cues(utterance, segment_by_id, frames_by_id, duration):
    text = utterance['russian']
    cues = []
    for cue in utterance['visual_cues']:
        segment_id = str(cue['segment_id'])
        anchor = cue.get('anchor')
        if anchor:
            index = anchor_position(text, anchor)
            at = duration * index / len(text)
        else:
            at = 0.0
        segment = segment_by_id[segment_id]
        cues.append(dict(segment_id=segment_id, at=at, caption=segment['russian'],
                         frames=frames_by_id[segment_id]))
    return cues


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
    segment_by_id = {str(segment['id']): segment for segment in lesson['segments']}
    frames_by_id = {str(segment['id']): frames for segment, frames in zip(lesson['segments'], visuals)}
    try:
        utterances = validate_utterances(lesson, lesson['segments'])
    except NarrationError as error:
        raise ValueError(str(error)) from error
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
    playback_utterances = []
    with tempfile.TemporaryDirectory(prefix='syntrillium-narration-') as temp:
        for utterance in utterances:
            wav_path = Path(temp) / 'narration.wav'
            with wave.open(str(wav_path), 'wb') as audio:
                voice.synthesize_wav(utterance['russian'], audio,
                                     syn_config=SynthesisConfig(noise_scale=0.5, noise_w_scale=0.333))
            source_ids = [segment_by_id[str(sid)]['source_resource_id'] for sid in utterance['segment_ids']]
            relative = f"audio/{source_ids[0]:05d}.mp3"
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
            playback_utterances.append(dict(
                id=str(utterance['id']), segment_ids=[str(item) for item in utterance['segment_ids']],
                caption=utterance['russian'], audio=relative, duration=duration,
                cues=compile_utterance_cues(utterance, segment_by_id, frames_by_id, duration)))
            manifest['audio'].append(dict(path=relative, utterance_id=str(utterance['id']),
                                          source_resource_ids=source_ids, sha256=digest(path), duration=duration))
            print(f"Generated narration utterance {len(playback_utterances)}/{len(utterances)}", flush=True)
    playback = dict(title=lesson['title'], labels=lesson['labels'], utterances=playback_utterances)
    (destination / 'lesson.js').write_text('window.LESSON = ' + json.dumps(
        playback, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    (destination / 'generation.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('content', type=Path)
    parser.add_argument('destination', type=Path, help='New generated output directory')
    parser.add_argument('--recovery', type=Path, required=True)
    parser.add_argument('--flash-export', type=Path)
    parser.add_argument('--voice-model', type=Path)
    parser.add_argument('--visuals-only', action='store_true', help='Stage lesson visuals without generating narration')
    args = parser.parse_args()
    try:
        if args.visuals_only:
            lesson_id = json.loads(args.content.read_text(encoding='utf-8'))['id']
            if lesson_id in STAGED_TOPICS:
                stage_audio(args.content, args.recovery, args.destination)
            else:
                stage_sound_fundamentals(args.content, args.recovery, args.destination)
        else:
            if not args.flash_export or not args.voice_model:
                raise ValueError('--flash-export and --voice-model are required for narrated Waveforms builds')
            build_lesson(args.content, args.recovery, args.flash_export, args.voice_model, args.destination)
    except (OSError, ValueError, KeyError, ET.ParseError, ImportError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Lesson build failed: {error}\n')


if __name__ == '__main__':
    main()
