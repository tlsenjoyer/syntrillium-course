#!/usr/bin/env python3
"""Generate and promote ElevenLabs candidate narration for course lessons.

The API key is read from ELEVENLABS_API_KEY or a local .env file. Generated
candidate directories are production artifacts; learner playback never calls
ElevenLabs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


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

    def audio(self, voice_id: str, model_id: str, text: str, output_format: str,
              voice_settings: dict[str, Any]) -> tuple[bytes, str | None]:
        url = f'{self.base_url}/text-to-speech/{voice_id}?{urlencode({"output_format": output_format})}'
        payload = json.dumps({'text': text, 'model_id': model_id,
                              'voice_settings': voice_settings}).encode('utf-8')
        try:
            with urlopen(Request(url, data=payload, headers={
                    'xi-api-key': self.api_key, 'Content-Type': 'application/json'}, method='POST'), timeout=120) as response:
                result = response.read()
                request_id = response.headers.get('request-id') or response.headers.get('x-request-id')
        except HTTPError as error:
            detail = error.read().decode('utf-8', errors='replace')[:500]
            raise ElevenLabsError(f'ElevenLabs API {error.code} for speech: {detail}') from error
        except URLError as error:
            raise ElevenLabsError(f'ElevenLabs API connection failed: {error.reason}') from error
        if not result:
            raise ElevenLabsError('ElevenLabs returned an empty audio file')
        return result, request_id


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


def select_segments(segments: list[dict[str, Any]], selection: str | None, all_segments: bool) -> list[dict[str, Any]]:
    if all_segments == bool(selection):
        raise ElevenLabsError('Choose exactly one of --segments or --all')
    by_id = {str(segment['id']): segment for segment in segments}
    if all_segments:
        return segments
    ids = [part.strip() for part in (selection or '').split(',') if part.strip()]
    if not ids or len(set(ids)) != len(ids):
        raise ElevenLabsError('--segments must contain one or more unique segment IDs')
    missing = [item for item in ids if item not in by_id]
    if missing:
        raise ElevenLabsError(f'Unknown segment ID(s): {", ".join(missing)}')
    return [by_id[item] for item in ids]


def candidate_manifest(path: Path) -> dict[str, Any]:
    manifest_path = path / 'generation.json'
    if not manifest_path.is_file():
        raise ElevenLabsError(f'Candidate has no generation.json: {path}')
    return json.loads(manifest_path.read_text(encoding='utf-8'))


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    temporary = path / 'generation.json.tmp'
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path / 'generation.json')


def generate(content: Path, lesson_id: str, voice_id: str, model_id: str, selection: str | None,
             all_segments: bool, candidate: Path | None, output_format: str, api: ElevenLabsClient) -> Path:
    lesson, segments = load_lesson(content, lesson_id)
    selected = select_segments(segments, selection, all_segments)
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
                        voice_settings=DEFAULT_VOICE_SETTINGS, created_at=datetime.now(timezone.utc).isoformat(), segments={})
        write_manifest(candidate, manifest)
    errors = []
    for segment in selected:
        sid = str(segment['id'])
        text = segment['russian']
        existing = manifest['segments'].get(sid)
        target = audio_dir / f'{sid}.mp3'
        if (existing and existing.get('text_sha256') == digest_text(text) and target.is_file()
                and existing.get('sha256') == digest_bytes(target.read_bytes())):
            continue
        try:
            audio, request_id = api.audio(voice_id, model_id, text, output_format, DEFAULT_VOICE_SETTINGS)
            if not audio:
                raise ElevenLabsError('empty audio response')
            with tempfile.NamedTemporaryFile(dir=audio_dir, prefix=f'.{sid}.', suffix='.tmp', delete=False) as handle:
                handle.write(audio)
                temporary = Path(handle.name)
            os.replace(temporary, target)
            manifest['segments'][sid] = dict(id=sid, source_resource_id=segment['source_resource_id'],
                                              text_sha256=digest_text(text), path=f'audio/{sid}.mp3',
                                              sha256=digest_bytes(audio), request_id=request_id, status='generated')
            write_manifest(candidate, manifest)
            print(f'Generated segment {sid}')
        except (ElevenLabsError, OSError) as error:
            errors.append(f'{sid}: {error}')
            print(f'Failed segment {sid}: {error}')
            break
    requested = list(dict.fromkeys(manifest.get('requested_segments', []) + [str(segment['id']) for segment in selected]))
    manifest['requested_segments'] = requested
    manifest['missing_segments'] = [sid for sid in requested if sid not in manifest['segments']]
    write_manifest(candidate, manifest)
    if errors:
        raise ElevenLabsError(f'Generation incomplete; candidate kept at {candidate}: ' + '; '.join(errors))
    return candidate


def promote(content: Path, lesson_id: str, candidate: Path, selection: str | None, all_segments: bool,
            player: Path) -> None:
    lesson, segments = load_lesson(content, lesson_id)
    selected = select_segments(segments, selection, all_segments)
    manifest = candidate_manifest(candidate)
    if manifest.get('lesson_id') != lesson_id:
        raise ElevenLabsError('Candidate belongs to a different lesson')
    if manifest.get('content_sha256') != lesson_digest(lesson):
        raise ElevenLabsError('Candidate lesson content has changed; nothing was promoted')
    files: list[tuple[str, Path, dict[str, Any]]] = []
    for segment in selected:
        sid = str(segment['id'])
        record = manifest.get('segments', {}).get(sid)
        source = candidate / 'audio' / f'{sid}.mp3'
        if not record or not source.is_file():
            raise ElevenLabsError(f'Candidate is missing segment {sid}; nothing was promoted')
        if (record.get('source_resource_id') != segment['source_resource_id']
                or record.get('text_sha256') != digest_text(segment['russian'])):
            raise ElevenLabsError(f'Candidate segment {sid} does not match current lesson content; nothing was promoted')
        data = source.read_bytes()
        if digest_bytes(data) != record.get('sha256'):
            raise ElevenLabsError(f'Candidate segment {sid} failed its hash check; nothing was promoted')
        files.append((sid, source, record))
    audio_dir = player / 'audio'
    audio_dir.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path, Path | None]] = []
    generation_path = player / 'generation.json'
    generation_temp = generation_path.with_suffix('.json.tmp')
    generation = None
    try:
        for sid, source, record in files:
            target = audio_dir / f"{int(record['source_resource_id']):05d}.mp3"
            temporary = audio_dir / f'.{target.name}.promotion.tmp'
            shutil.copyfile(source, temporary)
            backup = audio_dir / f'.{target.name}.promotion.bak' if target.exists() else None
            if backup:
                shutil.copyfile(target, backup)
            staged.append((temporary, target, backup))
        generation = json.loads(generation_path.read_text(encoding='utf-8')) if generation_path.is_file() else {}
        by_id = {str(item.get('source_resource_id')): item for item in generation.get('audio', [])}
        promoted = generation.setdefault('approved_narration', {})
        for _, _, record in files:
            item = by_id.get(str(record['source_resource_id']))
            if item is not None:
                item['sha256'] = record['sha256']
            promoted[str(record['source_resource_id'])] = {
                'provider': 'elevenlabs', 'voice_id': manifest['voice_id'],
                'model_id': manifest['model_id'], 'output_format': manifest['output_format'],
                'voice_settings': manifest['voice_settings'], 'text_sha256': record['text_sha256'],
                'sha256': record['sha256'], 'request_id': record.get('request_id'),
                'candidate': str(candidate),
            }
        generation_temp.write_text(json.dumps(generation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        replaced: list[tuple[Path, Path | None]] = []
        for temporary, target, backup in staged:
            os.replace(temporary, target)
            replaced.append((target, backup))
        os.replace(generation_temp, generation_path)
    except OSError:
        for target, backup in reversed(locals().get('replaced', [])):
            if backup and backup.exists():
                os.replace(backup, target)
            else:
                target.unlink(missing_ok=True)
        raise
    finally:
        generation_temp.unlink(missing_ok=True)
        for temporary, _, backup in staged:
            temporary.unlink(missing_ok=True)
            if backup:
                backup.unlink(missing_ok=True)
    print(f'Promoted {len(files)} segment(s) for lesson {lesson_id}')


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
    common.add_argument('--segments')
    common.add_argument('--all', action='store_true')
    common.add_argument('--candidate', type=Path)
    generate_parser = subparsers.add_parser('generate-elevenlabs', parents=[common])
    generate_parser.set_defaults(handler='generate')
    promote_parser = subparsers.add_parser('promote-elevenlabs')
    promote_parser.add_argument('--content', type=Path, default=Path('content/waveforms.json'))
    promote_parser.add_argument('--lesson', required=True)
    promote_parser.add_argument('--candidate', type=Path, required=True)
    promote_parser.add_argument('--segments')
    promote_parser.add_argument('--all', action='store_true')
    promote_parser.add_argument('--player', type=Path, default=Path('player'))
    promote_parser.set_defaults(handler='promote')
    args = parser.parse_args()
    try:
        if args.handler == 'check':
            check_access(require_client())
        elif args.handler == 'generate':
            api = require_client()
            path = generate(args.content, args.lesson, args.voice_id, args.model_id, args.segments,
                            args.all, args.candidate, args.output_format, api)
            print(f'Candidate: {path}')
        else:
            promote(args.content, args.lesson, args.candidate, args.segments, args.all, args.player)
    except (ElevenLabsError, OSError, json.JSONDecodeError) as error:
        parser.exit(1, f'ElevenLabs narration failed: {error}\n')


if __name__ == '__main__':
    main()
