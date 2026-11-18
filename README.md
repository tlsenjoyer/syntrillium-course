# Russian adaptation of the Syntrillium audio course

Work in progress for [issue #1](https://github.com/tlsenjoyer/syntrillium-course/issues/1).
The source is `course.exe`; the requirements are in
[the spec](docs/russian-course-spec.md).

The learner distribution is the Electron desktop app. Get the package for your
computer from [GitHub Releases](https://github.com/tlsenjoyer/syntrillium-course/releases)
once a release is published. See [desktop installation and release testing](docs/desktop-release.md).
For course authoring and review, `player/index.html` still opens directly from
disk and presents all nine lessons with the bundled Russian narration.

For the complete production sequence, review gates, and remaining first-lesson
tooling gaps, see the [lesson-authoring workflow](docs/lesson-authoring.md).

Lesson 3, «Аналоговый звук», is available from the course menu, the lesson list,
and lesson 2's next-lesson control. It includes all eight original narration
segments in seven complete Russian utterances, generated with ElevenLabs voice
`3EuKHIEZbSzrHGNmdYsx` and model `eleven_v4_turbo`. Its microphone, speaker, and
tape-recorder illustrations are converted from the original Flash paths.
Audio and visuals are bundled for offline playback. This is a review draft;
listening review, continuous original-playback comparison, and Windows/macOS
acceptance remain outstanding. See the [lesson 3 production record](docs/analog-audio-review.md).

Lesson 4, «Цифровой звук», is enabled in the main menu, lesson list, and
lesson 3's next-lesson control. Five source segments form three complete Russian
utterances, generated with the same ElevenLabs voice and model. Waveform,
sampling animation, and localized labels are bundled for offline review.
See the [lesson 4 production record](docs/digital-audio-review.md) for source
coverage, generation details, and outstanding review.

Lesson 5, «Частота дискретизации», is enabled in the main menu, lesson list,
and lesson 4's next-lesson control. All thirteen source segments are presented
in ten complete Russian utterances, generated with the same ElevenLabs voice
and model. The waveform, sample-density animation, translated definitions, and
narration are bundled for offline review. See the
[lesson 5 production record](docs/sampling-rate-review.md) for remaining review.

Lesson 6, «Разрядность», is enabled in the main menu, lesson list, and lesson
5's next-lesson control. Eighteen source segments form thirteen complete Russian
utterances, generated with the same authorized ElevenLabs voice and model.
Binary-state tables, amplitude quantization, CD/DVD definitions, and narration
are bundled for offline review. See the [lesson 6 production record](docs/bit-depth-review.md).

Lesson 7, «Итоги: цифровой звук», is available from the main menu, lesson list,
and lesson 6's next-lesson control. Four Russian utterances recap microphone
conversion, sampling, and playback. See the [lesson 7 production record](docs/digital-summary-review.md).

Lessons 8 and 9, «Звук на компьютере» and «MIDI», are available from the
main menu and lesson list. They include 27 Russian narration utterances and
localized visualizations of sound-card recording and playback, file size,
and MIDI notation and synthesis. See the
[lessons 8 and 9 production record](docs/final-lessons-review.md).

The first course topic, Sound Fundamentals (Основы звука), now has a
[Russian content draft](content/sound-fundamentals.json): 13 source narration
segments, their automatic English transcripts, and eight complete Russian
narration utterances with visual cue anchors. Its
[source inventory](content/sources/sound-fundamentals.json) retains audio hashes
and visual member references. Translation and transcription remain unreviewed;
suspected ASR and scientific wording issues are recorded in `review_notes`.
Build its separate silent review player without generating narration:

```sh
python3 tools/build_lesson.py content/sound-fundamentals.json \
  candidates/lessons/sound-fundamentals --recovery recovered --visuals-only
```

Open `candidates/lessons/sound-fundamentals/index.html`. The destination must be
new; the main Waveforms player is preserved. Play, pause, seeking, and phrase
navigation work without audio. The speaker bitmaps and ear outline are converted
from the original; pressure-wave motion is a draft reconstruction. Timing uses
source durations and text anchors until your narration is added. Original
playback comparison, content approval, narration, and synchronization review
remain outstanding; this is not an accepted learner lesson. The main player
bundles the promoted `review-2` narration in `player/lessons/sound-fundamentals/`.
The silent build command above creates a separate fresh draft and does not
replace that narration. For subsequent promotions into the main player, use
`--player player/lessons/sound-fundamentals`.

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
FFmpeg is installed, audio decoding. After the tool setup below,
`recovered/tools/whisper-env/bin/python -m mypy --check-untyped-defs tools tests`
checks Python types. Generated recovery/audio output belongs outside Git.

See [recovery findings and remaining work](docs/recovery.md) before using these
assets as lesson inputs. For Windows inspection, follow
[the project guide](docs/agents/windows-inspection.md).

## Transcribe original audio locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) on your PATH
(an existing `recovered/tools/uv` is also supported), then run:

```sh
bash scripts/setup-tools.sh
```

This downloads Python 3.12.16 if needed, recreates the local environment at the
current checkout path, and installs every dependency pinned in
`requirements-tools.txt`, including Whisper, its compatible PyAV decoder, mypy,
and Playwright for existing player checks. Run it again after moving the checkout
or to restore the pinned packages. Only `recovered/tools/whisper-env` is cleared;
cached models, recovery outputs, and transcripts are retained.

Setup checks mypy availability, then decodes and transcribes a six-second English
source clip on the CPU, asserting recognizable text. The first run downloads the
`base.en` model; subsequent runs reuse it. Python, packages, and cached models
stay in the ignored `recovered/tools/` directory. To repeat just the smoke test:

```sh
recovered/tools/whisper-env/bin/python tools/smoke_transcription.py
```

To intentionally update dependencies, edit `requirements-tools.in`, regenerate
the lock with `uv pip compile requirements-tools.in --python-version 3.12
--output-file requirements-tools.txt`, and rerun setup and the checks. PyAV is
pinned because newer releases removed the `metadata_errors` argument used by
Whisper 1.2.1. Playwright browser binaries are separate: install Chromium with
`recovered/tools/whisper-env/bin/python -m playwright install chromium` before
running browser tests.

Transcribe an exported WAV file from the repository root:

```sh
recovered/tools/whisper-env/bin/python tools/transcribe_audio.py \
  recovered/audio/01892.wav \
  --output recovered/transcripts/01892.json
```

The first run downloads `base.en`; subsequent runs reuse the local model.
Transcription runs on the CPU without an API key or paid requests. Each output
records the source audio hash, model, text and segment times. Existing output
files are never overwritten. English source transcription is an unreviewed
input to Russian translation; Russian narration and captions are authored from
that translation, not from the English transcript directly.

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

Generate selected narration utterances into an isolated candidate. Each
utterance is sent as one request, and the candidate stores the returned
character timings with its audio:

```sh
python3 tools/elevenlabs_audio.py generate-elevenlabs \
  --lesson waveforms --voice-id VOICE_ID --model-id MODEL_ID \
  --utterances 1976,1982 \
  --candidate candidates/elevenlabs/waveforms/voice-model-test
```

Use the same candidate path to resume a partial run. Existing valid utterances
are reused; only missing utterances are requested. Use `--all` instead of
`--utterances` to request every remaining utterance for the lesson. The default
format is `mp3_44100_128`. Other MP3 formats can be selected with
`--output-format`; non-MP3 formats are rejected because the current player
packages MP3 files.

After listening to the candidate and checking its visual cue timings, promote
only reviewed utterances:

```sh
python3 tools/elevenlabs_audio.py promote-elevenlabs \
  --lesson waveforms --candidate candidates/elevenlabs/waveforms/voice-model-test \
  --utterances 1976,1982
```

Create an offline preview of the generated audio with its source-segment
visuals and cue timings:

```sh
python3 tools/elevenlabs_audio.py preview-elevenlabs \
  --lesson waveforms --candidate candidates/elevenlabs/waveforms/voice-model-test \
  --utterances 1982
```

Open `candidates/elevenlabs/waveforms/voice-model-test/preview/index.html` to
review the utterance before promotion.

Use `--all` to promote every utterance in the candidate. Build player lesson data
with utterances before promotion. Promotion validates audio, text, and cue timing
before updating the approved audio and playback metadata. Generation metadata
records the lesson, text hash, voice, model, format, utterances, request IDs when
returned, alignment, and audio hashes. See the [ElevenAPI quickstart](https://elevenlabs.io/docs/eleven-api/quickstart)
and [speech API reference](https://elevenlabs.io/docs/api-reference/text-to-speech/convert)
for current account and output-format limits.

If ElevenLabs returns audio without usable character timings, the generator
keeps the audio in the candidate and marks its timing for manual correction.
Preview and promotion require complete cue times.
