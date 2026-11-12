#!/usr/bin/env python3
"""Decode recovered embedded MP3 audio to WAV using a local FFmpeg binary.

This is a production/recovery tool, not a dependency of the future player.
An audio.json manifest is written only after all supported resources decode.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import wave
from typing import Any


def digest(data):
    return hashlib.sha256(data).hexdigest()


def export_audio(recovery, destination):
    inventory = json.loads((recovery / 'inventory.json').read_text(encoding='utf-8'))
    composition = json.loads((recovery / 'composition.json').read_text(encoding='utf-8'))
    source_hash = inventory['source']['sha256']
    if composition['source_sha256'] != source_hash:
        raise ValueError('Inventory and composition come from different sources')
    if destination.exists():
        raise ValueError('Audio destination already exists')
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg is None:
        raise ValueError('FFmpeg is required for audio export')
    resources = {r['id']: r for r in inventory['resources']}
    members = {(m['library_id'], m['member_number']): m for m in composition['members']}
    plan: dict[int, dict[str, Any]] = {}
    for member in members.values():
        if member['type'] != 6:
            continue
        for media in member['media']:
            if not media['present'] or media['tag'] not in ('ediM', 'snd '):
                continue
            rid = media['resource_id']
            resource = resources[rid]
            source = (recovery / resource['path']).resolve()
            if not source.is_relative_to(recovery.resolve()):
                raise ValueError('Audio resource path escapes recovery directory')
            if digest(source.read_bytes()) != resource['sha256']:
                raise ValueError(f'Audio resource {rid} has changed since recovery')
            plan.setdefault(rid, dict(resource_id=rid, source=source, tag=media['tag'],
                                      source_sha256=resource['sha256'], members=[]))['members'].append(
                dict(library_id=member['library_id'], member_number=member['member_number'],
                     name=member['name']))
    sounds = []
    for event in composition['score']['sounds']:
        key = (event['library_id'], event['member_number'])
        member = members.get(key)
        if member is None:
            raise ValueError(f'Unknown score sound member {key}')
        media = [m for m in member['media'] if m['present'] and m['resource_id'] in plan]
        if len(media) != 1:
            raise ValueError(f'Missing or ambiguous score sound media for {key}')
        sounds.append(dict(start_frame=event['start_frame'], end_frame=event['end_frame'],
                           channel=event['channel'], library_id=key[0], member_number=key[1],
                           resource_id=media[0]['resource_id']))
    if not plan:
        raise ValueError('No recovered sound resources found')
    destination.mkdir(parents=True, exist_ok=False)
    exported = []
    for rid, item in sorted(plan.items()):
        source = item.pop('source')
        if item['tag'] != 'ediM':
            exported.append(dict(item, status='unsupported',
                                 reason='Proprietary SWA sound requires separate decoding'))
            continue
        filename = f'{rid:05d}.wav'
        result = subprocess.run(
            [ffmpeg, '-v', 'error', '-nostdin', '-xerror', '-n', '-i', str(source),
             '-map', '0:a:0', '-c:a', 'pcm_s16le', str(destination / filename)],
            capture_output=True, text=True)
        if result.returncode:
            raise ValueError(f'FFmpeg failed for resource {rid}: {result.stderr.strip()[:1000]}')
        with wave.open(str(destination / filename)) as audio:
            frames, rate, channels = audio.getnframes(), audio.getframerate(), audio.getnchannels()
        if not frames or not rate:
            raise ValueError(f'Audio resource {rid} decoded to no samples')
        exported.append(dict(item, status='decoded', path=filename, sample_count=frames,
                             sample_rate=rate, channels=channels, duration_seconds=frames / rate,
                             sha256=digest((destination / filename).read_bytes())))
    manifest = dict(source_sha256=source_hash, ffmpeg_version=subprocess.run(
        [ffmpeg, '-version'], capture_output=True, text=True, check=True).stdout.splitlines()[0],
        resources=exported, score_sounds=sounds,
        limitations=['Sound roles need classification by listening and rendered comparison.',
                     'Decoded durations do not establish score playback timestamps.',
                     'MP3 encoder delay and Director-specific trimming remain unverified.',
                     'The unsupported quit sound is retained in the resource inventory.'])
    (destination / 'audio.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recovery', type=Path, help='Directory produced by tools/recover.py')
    parser.add_argument('destination', type=Path, help='New WAV export directory')
    args = parser.parse_args()
    try:
        manifest = export_audio(args.recovery, args.destination)
    except (OSError, ValueError, KeyError, TypeError, wave.Error, subprocess.SubprocessError) as error:
        parser.exit(1, f'Audio export failed: {error}\n')
    decoded = sum(r['status'] == 'decoded' for r in manifest['resources'])
    print(f'Decoded {decoded} audio resources; see audio.json for unsupported media and score references')


if __name__ == '__main__':
    main()
