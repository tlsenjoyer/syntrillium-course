# Lesson 3: Analog Audio

Open `player/index.html#lesson/analog-audio` to review «Аналоговый звук».
The course menu, lesson list, previous/next controls, and browser history also
reach this lesson. Bundled playback requires no network access or API key.

## Content and production

- Original topic: Analog Audio, score frames 2814–3388. Digital Audio begins
  at 3389. All eight narration resources, 2150 through 2192 in increments of six,
  are covered in their original order.
- [Source inventory](../content/sources/analog-audio.json) records the executable
  hash, audio hashes and durations, score positions, and visual member references.
  [Russian content](../content/analog-audio.json) retains the automatic English
  transcripts, translated segments, seven complete utterances, and cue anchors.
- Segments 2180 and 2186 form one continuous loudspeaker explanation, with the
  second visual cue anchored to «он принимает». No substantive scientific
  correction was introduced. Tape and vinyl examples are retained.
- ElevenLabs voice: `3EuKHIEZbSzrHGNmdYsx` (Nikolay).
  Model: `eleven_v4_turbo`. Format: `mp3_44100_128`.
  Seven recordings total about 46 seconds; 691 Russian characters were submitted.
- Candidate: `candidates/elevenlabs/analog-audio/review-1`. Successful requests
  are reusable; generating a new candidate spends additional credits.
- [Bundled lesson](../player/lessons/analog-audio/lesson.js) and
  [generation metadata](../player/lessons/analog-audio/generation.json) retain
  character alignment, cue times, audio hashes, request IDs, and voice settings.
  Recordings are identified as `candidate_utterances`, with draft review status;
  they have not been marked as approved narration.

## Visual conversion

`tools/analog_audio.py` converts the original microphone (2917), speaker (2923),
and tape recorder (2965) from solid-fill DefineShape2 paths. Unsupported fills,
strokes, rotation, and malformed resources are rejected. The existing converted
complex waveform is reused. Pressure, voltage, and analog-audio labels are
Russian. The original left-cover bitmap is a background mask; its geometry is
retained with the adapted player's stage color instead of the original green.

Visual states follow the recovered score's channel and event order. Utterance
cue boundaries use ElevenLabs character timings. Positions within each cue
are mapped proportionally from score frames and remain provisional: frame
addresses alone do not capture script holds or jumps.

To build another silent review player, choose a new output directory:

```sh
python3 tools/build_lesson.py content/analog-audio.json \
  candidates/lessons/analog-audio-next --recovery recovered --visuals-only
```

To preview the existing recordings against that build without spending credits:

```sh
python3 tools/elevenlabs_audio.py preview-elevenlabs \
  --content content/analog-audio.json --lesson analog-audio \
  --candidate candidates/elevenlabs/analog-audio/review-1 \
  --player candidates/lessons/analog-audio-next --all
```

## Verification and remaining review

Automated checks cover source coverage, uninterrupted utterance grouping,
vector conversion, incomplete-input rejection, media hashes and timings, and
Chromium playback with networking disabled. Browser checks play each recording,
seek, navigate to lesson 2, return through history, reload the direct route, and
complete all seven recordings automatically. FFmpeg decodes all seven bundled
MP3s without errors. Desktop and mobile rendering were inspected.
The full suite passed 40 tests; final targeted runs passed all six third-lesson
checks and five first-lesson build checks. JavaScript syntax and diff whitespace
checks passed. Mypy was unavailable locally and in the offline package cache,
so static Python type checking was not run.

English source transcription used the existing local `base.en` Whisper model.
The relocated environment's audio decoder was incompatible, so source WAVs
were decoded with FFmpeg before transcription; no transcription service was used.

The Windows course cannot run on this host. Continuous comparison with the
original, human review of the translation and pronunciation, synchronization
review, and native Windows/macOS acceptance remain pending. These checks are
required before final acceptance; successful generation and browser tests do
not establish them.
