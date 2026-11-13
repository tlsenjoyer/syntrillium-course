# Russian adaptation of the Syntrillium audio course

Work in progress for [issue #1](https://github.com/tlsenjoyer/syntrillium-course/issues/1).
The source is `course.exe`; the requirements are in
[the spec](docs/russian-course-spec.md). A Russian lesson/player is not delivered yet.

## Recover the original resources

Python 3.10 or newer, standard library only:

```sh
python3 tools/recover.py course.exe recovered
python3 -m unittest discover -s tests
```

The output directory must be new. Use a different directory for a second run;
existing recoveries are never overwritten. Generated resources stay out of Git.
Recovery does not execute the Windows source.

`recovered/inventory.json` records source/movie hashes, every resource ID,
container compression, output hashes, cast member names, media references
(including missing targets), and Flash candidates. `movie.dcr` is the embedded
Director movie. `resources/` retains all resource-map entries; `flash/` contains
15 extracted SWF candidates. Numeric filenames refer to resource IDs, not lesson
order. Container decompression alone does not decode Director images or audio.

`recovered/composition.json` connects the 12 cast libraries to their members,
recovers 96 rich-text bodies, and records the 9,416-frame static score: sprite
placement spans, sound and script references, labels and topic entry addresses.
Frame addresses are **not playback timestamps**: the original scripts can hold
or jump frames. Bitmap/Flash text and runtime animation behavior still need
recovery and comparison with the original.

To decode embedded MP3 audio to local WAV files, install FFmpeg and run:

```sh
python3 tools/export_audio.py recovered /tmp/syntrillium-audio
```

The destination must be new. `audio.json` records all 151 decoded resources,
hashes, measured durations, and 141 score sound references. One proprietary
`quit` sound remains explicitly unsupported. No audio roles are inferred merely
from resource names. Export uses local FFmpeg; learner playback has no dependency
on this recovery tool. A failed export may leave partial WAVs, but writes no
completed manifest; retry with a new destination after resolving the error.

Checks: `python3 -m unittest discover -s tests` exercises recovery and, when
FFmpeg is installed, audio decoding. `mypy --check-untyped-defs tools tests`
checks Python types. Generated recovery/audio output belongs outside Git.

See [recovery findings and remaining work](docs/recovery.md) before using these
assets as lesson inputs. For Windows inspection, follow
[the project guide](docs/agents/windows-inspection.md).

## Generate lesson narration with ElevenLabs

ElevenLabs is used only when producing course audio. Learner playback uses
bundled MP3 files and does not need an account, API key, or network connection.
The key is read from `ELEVENLABS_API_KEY`, `.env.local`, or `.env`; those files
and generated candidates are ignored by Git.

Add the key to `.env.local`, then check access without generating speech:

```text
ELEVENLABS_API_KEY=your_api_key
```

```sh
python3 tools/elevenlabs_audio.py check-elevenlabs
```

Generate selected segments into an isolated candidate:

```sh
python3 tools/elevenlabs_audio.py generate-elevenlabs \
  --lesson waveforms --voice-id VOICE_ID --model-id MODEL_ID \
  --segments 1976,1982 \
  --candidate candidates/elevenlabs/waveforms/voice-model-test
```

Use the same candidate path to resume a partial run. Existing valid segments
are reused; only missing segments are requested. Use `--all` instead of
`--segments` to request every remaining segment for the lesson. The default
format is `mp3_44100_128`. Other MP3 formats can be selected with
`--output-format`; non-MP3 formats are rejected because the current player
packages MP3 files.

After listening to the candidate, promote only reviewed segments:

```sh
python3 tools/elevenlabs_audio.py promote-elevenlabs \
  --lesson waveforms --candidate candidates/elevenlabs/waveforms/voice-model-test \
  --segments 1976,1982
```

Use `--all` to promote every segment in the candidate. Promotion validates all
selected files and hashes before replacing approved MP3s, stages local copies,
and restores prior files if a replacement fails. Generation metadata records
the lesson, text hash, voice, model, format, selected segments, request IDs when
returned, and audio hashes. See the [ElevenAPI quickstart](https://elevenlabs.io/docs/eleven-api/quickstart)
and [speech API reference](https://elevenlabs.io/docs/api-reference/text-to-speech/convert)
for current account and output-format limits.
