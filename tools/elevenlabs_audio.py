#!/usr/bin/env python3
"""Generate and promote ElevenLabs candidate narration for course lessons.

The API key is read from ELEVENLABS_API_KEY or a local .env file. Generated
candidate directories are production artifacts; learner playback never calls
ElevenLabs.
"""
import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from narration import NarrationError, validate_utterances

API_ROOT = 'https://api.elevenlabs.io/v1'
DEFAULT_FORMAT = 'mp3_44100_128'
DEFAULT_VOICE_SETTINGS = {
    'stability': 0.5,
    'similarity_boost': 0.75,
    'style': 0,
    'use_speaker_boost': True,
    'speed': 1,
}


class ElevenLabsError(RuntimeError):
    """An actionable ElevenLabs or local generation error."""


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_text(value: str) -> str:
    return digest_bytes(value.encode('utf-8'))


def lesson_digest(lesson: dict[str, Any]) -> str:
    return digest_text(json.dumps(lesson, sort_keys=True, ensure_ascii=False))


def load_api_key() -> str | None:
    value = os.environ.get('ELEVENLABS_API_KEY')
    if value:
        return value
    for name in ('.env.local', '.env'):
        path = Path(name)
        if not path.is_file():
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and line.startswith('ELEVENLABS_API_KEY='):
                return line.split('=', 1)[1].strip().strip("'\"") or None
    return None


class ElevenLabsClient:
    def __init__(self, api_key: str, base_url: str = API_ROOT):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')

    def request_json(self, method: str, path: str, payload: dict[str, Any] | None = None,
                     query: dict[str, str] | None = None) -> Any:
        url = self.base_url + path
        if query:
            url += '?' + urlencode(query)
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        headers = {'xi-api-key': self.api_key, 'Accept': 'application/json'}
        if data is not None:
            headers['Content-Type'] = 'application/json'
        try:
            with urlopen(Request(url, data=data, headers=headers, method=method), timeout=60) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as error:
            detail = error.read().decode('utf-8', errors='replace')[:500]
            raise ElevenLabsError(f'ElevenLabs API {error.code} for {path}: {detail}') from error
        except URLError as error:
            raise ElevenLabsError(f'ElevenLabs API connection failed: {error.reason}') from error

    def audio_with_timestamps(self, voice_id: str, model_id: str, text: str, output_format: str,
                              voice_settings: dict[str, Any]) -> tuple[bytes, str | None, dict[str, Any] | None]:
        url = f'{self.base_url}/text-to-speech/{voice_id}/with-timestamps?{urlencode({"output_format": output_format})}'
        payload = json.dumps({'text': text, 'model_id': model_id,
                              'voice_settings': voice_settings}).encode('utf-8')
        try:
            with urlopen(Request(url, data=payload, headers={
                    'xi-api-key': self.api_key, 'Content-Type': 'application/json'}, method='POST'), timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                request_id = response.headers.get('request-id') or response.headers.get('x-request-id')
        except HTTPError as error:
            detail = error.read().decode('utf-8', errors='replace')[:500]
            raise ElevenLabsError(f'ElevenLabs API {error.code} for timestamped speech: {detail}') from error
        except (URLError, json.JSONDecodeError) as error:
            reason = getattr(error, 'reason', error)
            raise ElevenLabsError(f'ElevenLabs timestamped speech request failed: {reason}') from error
        try:
            audio = base64.b64decode(result['audio_base64'], validate=True)
            alignment = result.get('alignment')
        except (KeyError, ValueError, TypeError) as error:
            raise ElevenLabsError('ElevenLabs returned an invalid timestamped audio response') from error
        if not audio:
            raise ElevenLabsError('ElevenLabs returned an empty timestamped audio file')
        if not isinstance(alignment, dict):
            alignment = None
        return audio, request_id, alignment


def require_client() -> ElevenLabsClient:
    key = load_api_key()
    if not key:
        raise ElevenLabsError('ELEVENLABS_API_KEY is missing; add it to the environment or .env.local')
    return ElevenLabsClient(key)


def load_lesson(content: Path, lesson_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lesson = json.loads(content.read_text(encoding='utf-8'))
    if lesson.get('id') != lesson_id:
        raise ElevenLabsError(f'Content file is lesson {lesson.get("id")!r}, not {lesson_id!r}')
    segments = lesson.get('segments')
    if not isinstance(segments, list) or not segments:
        raise ElevenLabsError(f'Lesson {lesson_id} has no narration segments')
    return lesson, segments


def lesson_utterances(lesson: dict[str, Any], segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        return validate_utterances(lesson, segments)
    except NarrationError as error:
        raise ElevenLabsError(str(error)) from error


def select_utterances(utterances: list[dict[str, Any]], selection: str | None,
                      all_utterances: bool) -> list[dict[str, Any]]:
    if all_utterances == bool(selection):
        raise ElevenLabsError('Choose exactly one of --utterances or --all')
    by_id = {str(utterance['id']): utterance for utterance in utterances}
    if all_utterances:
        return utterances
    ids = [part.strip() for part in (selection or '').split(',') if part.strip()]
    if not ids or len(set(ids)) != len(ids):
        raise ElevenLabsError('--utterances must contain one or more unique utterance IDs')
    missing = [item for item in ids if item not in by_id]
    if missing:
        raise ElevenLabsError(f'Unknown utterance ID(s): {", ".join(missing)}')
    return [by_id[item] for item in ids]


def resolve_cue_times(utterance: dict[str, Any], alignment: dict[str, Any]) -> tuple[list[dict[str, Any]], float]:
    if not isinstance(alignment, dict):
        raise ElevenLabsError(f"Utterance {utterance['id']} has no character timings")
    characters = alignment.get('characters')
    starts = alignment.get('character_start_times_seconds')
    ends = alignment.get('character_end_times_seconds')
    if not isinstance(characters, list) or not isinstance(starts, list) or not isinstance(ends, list):
        raise ElevenLabsError(f"Utterance {utterance['id']} has malformed character timings")
    if not characters or len(characters) != len(starts) or len(characters) != len(ends):
        raise ElevenLabsError(f"Utterance {utterance['id']} has incomplete character timings")
    try:
        starts = [float(value) for value in starts]
        ends = [float(value) for value in ends]
    except (TypeError, ValueError) as error:
        raise ElevenLabsError(f"Utterance {utterance['id']} has invalid character timings") from error
    if (any(not math.isfinite(value) or value < 0 for value in starts + ends)
            or any(start > end for start, end in zip(starts, ends))
            or any(left > right for left, right in zip(starts, starts[1:]))
            or any(left > right for left, right in zip(ends, ends[1:]))):
        raise ElevenLabsError(f"Utterance {utterance['id']} has invalid character timings")
    spoken_text = ''.join(characters)
    cue_times = []
    for cue in utterance['visual_cues']:
        anchor = cue.get('anchor')
        if not anchor:
            cue_times.append({'segment_id': str(cue['segment_id']), 'at': 0.0})
            continue
        first = spoken_text.find(anchor)
        if first < 0 or spoken_text.find(anchor, first + 1) >= 0:
            raise ElevenLabsError(f"Visual cue anchor is missing or ambiguous in utterance {utterance['id']}: {anchor}")
        at = starts[first]
        cue_times.append({'segment_id': str(cue['segment_id']), 'at': at})
    duration = max(ends)
    if duration <= 0 or any(cue_times[i]['at'] >= cue_times[i + 1]['at']
                             for i in range(len(cue_times) - 1)):
        raise ElevenLabsError(f"Utterance {utterance['id']} has invalid visual cue ordering")
    if any(cue['at'] >= duration for cue in cue_times[1:]):
        raise ElevenLabsError(f"Utterance {utterance['id']} has a visual cue outside its audio")
    return cue_times, duration


def validate_candidate_timing(utterance: dict[str, Any], record: dict[str, Any]) -> dict[str, float]:
    try:
        duration = float(record['duration'])
        cue_times = record['cue_times']
        ids = [str(cue['segment_id']) for cue in cue_times]
        values = [float(cue['at']) for cue in cue_times]
    except (KeyError, TypeError, ValueError) as error:
        raise ElevenLabsError(f"Utterance {utterance['id']} has incomplete cue timing data") from error
    expected = [str(item) for item in utterance['segment_ids']]
    if (not math.isfinite(duration) or duration <= 0 or ids != expected or not values
            or values[0] != 0 or any(not math.isfinite(value) for value in values)
            or any(left >= right for left, right in zip(values, values[1:]))
            or any(value < 0 or value >= duration for value in values)):
        raise ElevenLabsError(f"Utterance {utterance['id']} has invalid cue timing data")
    return dict(zip(ids, values))


def validate_candidate_record(utterance: dict[str, Any], record: dict[str, Any] | None,
                              audio_path: Path) -> dict[str, float]:
    uid = str(utterance['id'])
    if not record or not audio_path.is_file():
        raise ElevenLabsError(f'Candidate is missing utterance {uid}')
    if (record.get('segment_ids') != [str(item) for item in utterance['segment_ids']]
            or record.get('text_sha256') != digest_text(utterance['russian'])):
        raise ElevenLabsError(f'Candidate utterance {uid} does not match current lesson content')
    cue_times = validate_candidate_timing(utterance, record)
    if digest_bytes(audio_path.read_bytes()) != record.get('sha256'):
        raise ElevenLabsError(f'Candidate utterance {uid} failed its hash check')
    return cue_times


def probe_audio_duration(path: Path) -> float | None:
    ffprobe = shutil.which('ffprobe')
    if not ffprobe:
        return None
    try:
        result = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format=duration',
                                 '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
                                capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return None
    return duration if math.isfinite(duration) and duration > 0 else None


def candidate_manifest(path: Path) -> dict[str, Any]:
    manifest_path = path / 'generation.json'
    if not manifest_path.is_file():
        raise ElevenLabsError(f'Candidate has no generation.json: {path}')
    return json.loads(manifest_path.read_text(encoding='utf-8'))


def player_lesson(path: Path) -> dict[str, Any]:
    prefix = 'window.LESSON = '
    source = (path / 'lesson.js').read_text(encoding='utf-8')
    if not source.startswith(prefix):
        raise ElevenLabsError('Player lesson data has an unsupported format')
    try:
        return json.loads(source[len(prefix):].strip().removesuffix(';'))
    except json.JSONDecodeError as error:
        raise ElevenLabsError('Player lesson data is invalid') from error


def upgrade_segment_playback(playback: dict[str, Any], lesson: dict[str, Any],
                             selected_ids: set[str]) -> dict[str, Any]:
    legacy_segments = playback.get('segments')
    if not isinstance(legacy_segments, list):
        raise ElevenLabsError('Player lesson has no visual data to upgrade')
    by_id = {str(item.get('id')): item for item in legacy_segments}
    expected_ids = [str(segment['id']) for segment in lesson['segments']]
    if len(by_id) != len(legacy_segments) or set(by_id) != set(expected_ids):
        raise ElevenLabsError('Player visuals do not match lesson source segments')
    for segment in lesson['segments']:
        item = by_id[str(segment['id'])]
        if item.get('caption') != segment['russian']:
            raise ElevenLabsError('Player visuals are stale; rebuild the lesson before promoting')

    upgraded = []
    for utterance in lesson_utterances(lesson, lesson['segments']):
        uid = str(utterance['id'])
        segment_ids = [str(item) for item in utterance['segment_ids']]
        if uid in selected_ids:
            first = by_id[segment_ids[0]]
            upgraded.append({
                'id': uid,
                'segment_ids': segment_ids,
                'caption': utterance['russian'],
                'audio': first['audio'],
                'duration': first['duration'],
                'cues': [{'segment_id': sid, 'at': 0, 'caption': by_id[sid]['caption'],
                          'frames': by_id[sid].get('frames', [])} for sid in segment_ids],
            })
        else:
            for sid in segment_ids:
                item = by_id[sid]
                upgraded.append({
                    'id': sid,
                    'segment_ids': [sid],
                    'caption': item['caption'],
                    'audio': item['audio'],
                    'duration': item['duration'],
                    'cues': [{'segment_id': sid, 'at': 0, 'caption': item['caption'],
                              'frames': item.get('frames', [])}],
                })
    result = dict(playback)
    result.pop('segments', None)
    result['utterances'] = upgraded
    return result


def build_preview(content: Path, lesson_id: str, candidate: Path, player: Path,
                  selection: str | None = None, all_utterances: bool = False) -> Path:
    lesson, source_segments = load_lesson(content, lesson_id)
    utterances = lesson_utterances(lesson, source_segments)
    manifest = candidate_manifest(candidate)
    if manifest.get('lesson_id') != lesson_id or manifest.get('content_sha256') != lesson_digest(lesson):
        raise ElevenLabsError('Candidate does not match current lesson content')
    if not selection and not all_utterances:
        requested = manifest.get('requested_utterances', list(manifest.get('utterances', {})))
        selection = ','.join(requested)
        if not selection:
            raise ElevenLabsError('Candidate has no generated narration utterances')
    selected = select_utterances(utterances, selection, all_utterances)
    playback = player_lesson(player)
    visuals: dict[str, dict[str, Any]] = {}
    if isinstance(playback.get('utterances'), list):
        for item in playback['utterances']:
            for cue in item.get('cues', []):
                visuals[str(cue['segment_id'])] = cue
    elif isinstance(playback.get('segments'), list):
        if len(playback['segments']) != len(source_segments):
            raise ElevenLabsError('Player visuals do not match lesson source segments')
        for source_segment, item in zip(source_segments, playback['segments']):
            if item.get('caption') != source_segment['russian']:
                raise ElevenLabsError('Player visuals are stale; rebuild the lesson before previewing')
            visuals[str(source_segment['id'])] = item
    else:
        raise ElevenLabsError('Player lesson has no visual data')
    candidate_utterances = manifest.get('utterances', {})
    preview_utterances = []
    for utterance in selected:
        uid = str(utterance['id'])
        record = candidate_utterances.get(uid)
        audio_source = candidate / 'audio' / f'{uid}.mp3'
        cue_times = validate_candidate_record(utterance, record, audio_source)
        cues = []
        for source_id in utterance['segment_ids']:
            sid = str(source_id)
            visual = visuals.get(sid)
            if visual is None or sid not in cue_times:
                raise ElevenLabsError(f'Player has no matching visual cue for source segment {sid}')
            cues.append(dict(segment_id=sid, at=cue_times[sid],
                             caption=source_segment_caption(source_segments, sid),
                             frames=visual.get('frames', [])))
        preview_utterances.append(dict(
            id=uid, segment_ids=[str(item) for item in utterance['segment_ids']],
            caption=utterance['russian'], audio=f'../audio/{uid}.mp3',
            duration=record['duration'], cues=cues))
    preview = candidate / 'preview'
    preview.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'player.js', 'player.css'):
        shutil.copyfile(player / name, preview / name)
    shutil.copytree(player / 'assets', preview / 'assets', dirs_exist_ok=True)
    preview_data = dict(id=lesson_id, title=playback.get('title', lesson['title']),
                        labels=playback.get('labels', lesson.get('labels', {})),
                        utterances=preview_utterances)
    (preview / 'lesson.js').write_text('window.LESSON = ' + json.dumps(
        preview_data, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    return preview


def source_segment_caption(segments: list[dict[str, Any]], segment_id: str) -> str:
    return next(segment['russian'] for segment in segments if str(segment['id']) == segment_id)


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    temporary = path / 'generation.json.tmp'
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path / 'generation.json')


def generate(content: Path, lesson_id: str, voice_id: str, model_id: str, selection: str | None,
             all_utterances: bool, candidate: Path | None, output_format: str, api: ElevenLabsClient) -> Path:
    lesson, segments = load_lesson(content, lesson_id)
    utterances = lesson_utterances(lesson, segments)
    selected = select_utterances(utterances, selection, all_utterances)
    if not output_format.startswith('mp3_'):
        raise ElevenLabsError('Only MP3 output formats can be promoted to the current lesson player')
    if candidate is None:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        candidate = Path('candidates') / 'elevenlabs' / lesson_id / f'{stamp}-{voice_id}-{model_id}'
    candidate.mkdir(parents=True, exist_ok=True)
    audio_dir = candidate / 'audio'
    audio_dir.mkdir(exist_ok=True)
    manifest_path = candidate / 'generation.json'
    if manifest_path.exists():
        manifest = candidate_manifest(candidate)
        expected = (lesson_id, voice_id, model_id, output_format, lesson_digest(lesson))
        actual = (manifest.get('lesson_id'), manifest.get('voice_id'), manifest.get('model_id'),
                  manifest.get('output_format'), manifest.get('content_sha256'))
        if actual != expected:
            raise ElevenLabsError('Existing candidate uses different lesson, voice, model, format, or content')
    else:
        manifest = dict(lesson_id=lesson_id, content_sha256=lesson_digest(lesson),
                        voice_id=voice_id, model_id=model_id, output_format=output_format,
                        voice_settings=DEFAULT_VOICE_SETTINGS, created_at=datetime.now(timezone.utc).isoformat(), utterances={})
        write_manifest(candidate, manifest)
    errors = []
    for utterance in selected:
        uid = str(utterance['id'])
        text = utterance['russian']
        existing = manifest['utterances'].get(uid)
        target = audio_dir / f'{uid}.mp3'
        if (existing and existing.get('text_sha256') == digest_text(text) and target.is_file()
                and existing.get('sha256') == digest_bytes(target.read_bytes())):
            continue
        try:
            audio, request_id, alignment = api.audio_with_timestamps(
                voice_id, model_id, text, output_format, DEFAULT_VOICE_SETTINGS)
            if not audio:
                raise ElevenLabsError('empty audio response')
            with tempfile.NamedTemporaryFile(dir=audio_dir, prefix=f'.{uid}.', suffix='.tmp', delete=False) as handle:
                handle.write(audio)
                temporary = Path(handle.name)
            status = 'generated'
            timing_error = None
            try:
                cue_times, duration = resolve_cue_times(utterance, alignment)
            except ElevenLabsError as error:
                cue_times = []
                duration = probe_audio_duration(temporary)
                status = 'needs_manual_timing'
                timing_error = str(error)
            os.replace(temporary, target)
            manifest['utterances'][uid] = dict(
                id=uid, segment_ids=[str(item) for item in utterance['segment_ids']],
                text_sha256=digest_text(text), path=f'audio/{uid}.mp3',
                sha256=digest_bytes(audio), request_id=request_id, status=status,
                duration=duration, alignment=alignment, cue_times=cue_times,
                timing_error=timing_error)
            write_manifest(candidate, manifest)
            note = ' (manual cue timing required)' if status != 'generated' else ''
            print(f'Generated utterance {uid}{note}')
        except (ElevenLabsError, OSError) as error:
            errors.append(f'{uid}: {error}')
            print(f'Failed utterance {uid}: {error}')
            break
    requested = list(dict.fromkeys(manifest.get('requested_utterances', []) + [str(item['id']) for item in selected]))
    manifest['requested_utterances'] = requested
    manifest['missing_utterances'] = [uid for uid in requested if uid not in manifest['utterances']]
    write_manifest(candidate, manifest)
    if errors:
        raise ElevenLabsError(f'Generation incomplete; candidate kept at {candidate}: ' + '; '.join(errors))
    return candidate


def promote(content: Path, lesson_id: str, candidate: Path, selection: str | None, all_utterances: bool,
            player: Path) -> None:
    lesson, segments = load_lesson(content, lesson_id)
    utterances = lesson_utterances(lesson, segments)
    selected = select_utterances(utterances, selection, all_utterances)
    selected_by_id = {str(item['id']): item for item in selected}
    manifest = candidate_manifest(candidate)
    if manifest.get('lesson_id') != lesson_id:
        raise ElevenLabsError('Candidate belongs to a different lesson')
    if manifest.get('content_sha256') != lesson_digest(lesson):
        raise ElevenLabsError('Candidate lesson content has changed; nothing was promoted')
    files: list[tuple[str, Path, dict[str, Any]]] = []
    segment_by_id = {str(segment['id']): segment for segment in segments}
    for utterance in selected:
        uid = str(utterance['id'])
        record = manifest.get('utterances', {}).get(uid)
        source = candidate / 'audio' / f'{uid}.mp3'
        validate_candidate_record(utterance, record, source)
        record['source_resource_ids'] = [segment_by_id[sid]['source_resource_id']
                                         for sid in record['segment_ids']]
        files.append((uid, source, record))
    lesson_path = player / 'lesson.js'
    playback = None
    if lesson_path.is_file():
        playback = player_lesson(player)
        if not isinstance(playback, dict):
            raise ElevenLabsError('Player lesson data is invalid')
        if not isinstance(playback.get('utterances'), list):
            playback = upgrade_segment_playback(playback, lesson, set(selected_by_id))
        playback_by_id = {str(item.get('id')): item for item in playback['utterances']}
        for uid, _, record in files:
            item = playback_by_id.get(uid)
            if not item or [str(cue.get('segment_id')) for cue in item.get('cues', [])] != record['segment_ids']:
                raise ElevenLabsError(f'Player lesson has no matching visual cues for utterance {uid}')
            cue_times = validate_candidate_timing(selected_by_id[uid], record)
            item['caption'] = selected_by_id[uid]['russian']
            item['duration'] = record['duration']
            item['audio'] = f"audio/{record['source_resource_ids'][0]:05d}.mp3"
            for cue in item['cues']:
                cue['at'] = cue_times[str(cue['segment_id'])]
    audio_dir = player / 'audio'
    audio_dir.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path, Path | None]] = []
    generation_path = player / 'generation.json'
    generation_temp = generation_path.with_suffix('.json.tmp')
    lesson_temp = lesson_path.with_suffix('.js.tmp')
    generation = None
    try:
        for uid, source, record in files:
            target = audio_dir / f"{int(record['source_resource_ids'][0]):05d}.mp3"
            temporary = audio_dir / f'.{target.name}.promotion.tmp'
            shutil.copyfile(source, temporary)
            backup = audio_dir / f'.{target.name}.promotion.bak' if target.exists() else None
            if backup:
                shutil.copyfile(target, backup)
            staged.append((temporary, target, backup))
        generation = json.loads(generation_path.read_text(encoding='utf-8')) if generation_path.is_file() else {}
        promoted = generation.setdefault('approved_utterances', {})
        replaced_resources = {resource_id for _, _, record in files
                              for resource_id in record['source_resource_ids']}
        audio = generation.setdefault('audio', [])
        def overlaps_promoted_sources(item):
            sources = set(item.get('source_resource_ids', []))
            if item.get('source_resource_id') is not None:
                sources.add(item['source_resource_id'])
            return bool(sources.intersection(replaced_resources))
        audio[:] = [item for item in audio if not overlaps_promoted_sources(item)]
        for uid, _, record in files:
            target_name = f"audio/{int(record['source_resource_ids'][0]):05d}.mp3"
            audio.append(dict(path=target_name, utterance_id=uid,
                              source_resource_id=record['source_resource_ids'][0],
                              source_resource_ids=record['source_resource_ids'],
                              sha256=record['sha256'], duration=record['duration']))
            promoted[uid] = {
                'provider': 'elevenlabs', 'voice_id': manifest['voice_id'],
                'model_id': manifest['model_id'], 'output_format': manifest['output_format'],
                'voice_settings': manifest['voice_settings'], 'text_sha256': record['text_sha256'],
                'sha256': record['sha256'], 'request_id': record.get('request_id'),
                'candidate': str(candidate), 'duration': record['duration'],
                'cue_times': record['cue_times'], 'segment_ids': record['segment_ids'],
            }
        generation_temp.write_text(json.dumps(generation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if playback is not None:
            lesson_temp.write_text('window.LESSON = ' + json.dumps(playback, ensure_ascii=False, indent=2) + ';\n',
                                   encoding='utf-8')
            backup = lesson_path.with_suffix('.js.promotion.bak') if lesson_path.exists() else None
            if backup:
                shutil.copyfile(lesson_path, backup)
            staged.append((lesson_temp, lesson_path, backup))
        backup = generation_path.with_suffix('.json.promotion.bak') if generation_path.exists() else None
        if backup:
            shutil.copyfile(generation_path, backup)
        staged.append((generation_temp, generation_path, backup))
        replaced: list[tuple[Path, Path | None]] = []
        for temporary, target, backup in staged:
            os.replace(temporary, target)
            replaced.append((target, backup))
    except OSError:
        for target, backup in reversed(locals().get('replaced', [])):
            if backup and backup.exists():
                os.replace(backup, target)
            else:
                target.unlink(missing_ok=True)
        raise
    finally:
        generation_temp.unlink(missing_ok=True)
        lesson_temp.unlink(missing_ok=True)
        for temporary, _, backup in staged:
            temporary.unlink(missing_ok=True)
            if backup:
                backup.unlink(missing_ok=True)
    print(f'Promoted {len(files)} narration utterance(s) for lesson {lesson_id}')


def check_access(api: ElevenLabsClient) -> None:
    models = api.request_json('GET', '/models')
    voices = api.request_json('GET', '/voices')
    speech_models = [item.get('model_id') for item in models if item.get('can_do_text_to_speech')]
    available_voices = voices.get('voices', [])
    print(f'API access confirmed; {len(speech_models)} speech model(s), {len(available_voices)} voice(s) available')
    print('Models: ' + ', '.join(model for model in speech_models if model))
    print('Voices: ' + ', '.join(f'{voice.get("name", "(unnamed)")} [{voice.get("voice_id", "")}]'
                                for voice in available_voices))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)
    check_parser = subparsers.add_parser('check-elevenlabs')
    check_parser.set_defaults(handler='check')
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--content', type=Path, default=Path('content/waveforms.json'))
    common.add_argument('--lesson', required=True)
    common.add_argument('--voice-id', required=True)
    common.add_argument('--model-id', required=True)
    common.add_argument('--output-format', default=DEFAULT_FORMAT)
    common.add_argument('--utterances')
    common.add_argument('--all', action='store_true')
    common.add_argument('--candidate', type=Path)
    generate_parser = subparsers.add_parser('generate-elevenlabs', parents=[common])
    generate_parser.set_defaults(handler='generate')
    promote_parser = subparsers.add_parser('promote-elevenlabs')
    promote_parser.add_argument('--content', type=Path, default=Path('content/waveforms.json'))
    promote_parser.add_argument('--lesson', required=True)
    promote_parser.add_argument('--candidate', type=Path, required=True)
    promote_parser.add_argument('--utterances')
    promote_parser.add_argument('--all', action='store_true')
    promote_parser.add_argument('--player', type=Path, default=Path('player'))
    promote_parser.set_defaults(handler='promote')
    preview_parser = subparsers.add_parser('preview-elevenlabs')
    preview_parser.add_argument('--content', type=Path, default=Path('content/waveforms.json'))
    preview_parser.add_argument('--lesson', required=True)
    preview_parser.add_argument('--candidate', type=Path, required=True)
    preview_parser.add_argument('--utterances')
    preview_parser.add_argument('--all', action='store_true')
    preview_parser.add_argument('--player', type=Path, default=Path('player'))
    preview_parser.set_defaults(handler='preview')
    args = parser.parse_args()
    try:
        if args.handler == 'check':
            check_access(require_client())
        elif args.handler == 'generate':
            api = require_client()
            path = generate(args.content, args.lesson, args.voice_id, args.model_id, args.utterances,
                            args.all, args.candidate, args.output_format, api)
            print(f'Candidate: {path}')
        elif args.handler == 'promote':
            promote(args.content, args.lesson, args.candidate, args.utterances, args.all, args.player)
        else:
            path = build_preview(args.content, args.lesson, args.candidate, args.player,
                                 args.utterances, args.all)
            print(f'Preview: {path}')
    except (ElevenLabsError, OSError, json.JSONDecodeError) as error:
        parser.exit(1, f'ElevenLabs narration failed: {error}\n')


if __name__ == '__main__':
    main()
