# Lesson 4: Digital Audio

Open `player/index.html#lesson/digital-audio` to review «Цифровой звук».
It is enabled in the main menu and lesson list, and follows lesson 3 through
the next-lesson control. Playback uses bundled media without network access.

## Content and narration

The topic covers original score frames 3389–3696, before Sampling Rate at 3697.
All five original narration resources (2198, 2204, 2210, 2216, 2222) are retained
in order. The [source inventory](../content/sources/digital-audio.json) records
source audio hashes, durations, frame spans, and visual member references.
[Russian content](../content/digital-audio.json) retains automatic English
transcripts, translations, three complete utterances, and visual cue anchors.

Resources 2198 and 2204 form one sentence contrasting analog media with digital
storage. Resources 2216 and 2222 explain digitizing, sampling, and analog-to-digital
conversion together. The ASR text “computer store” is rendered as «компьютеры
хранят». No substantive scientific correction or additional curriculum was added.
Transcription and translation remain unreviewed drafts.

Three recordings (about 23 seconds, 331 Russian characters) were generated with
ElevenLabs voice `3EuKHIEZbSzrHGNmdYsx`, model `eleven_v4_turbo`, and format
`mp3_44100_128`. Candidate: `candidates/elevenlabs/digital-audio/review-1`.
The [bundled generation metadata](../player/lessons/digital-audio/generation.json)
retains settings, request IDs, audio hashes, character alignment, and cue times
under `candidate_utterances`. The recordings are available for review and have
not been marked as approved narration.

## Visual conversion and reproduction

`tools/digital_audio.py` preserves the recovered score's event and channel order:
analog waveform and loudspeaker, transition to a single waveform, successive
sample markers and scanning line, then Russian digitizing and conversion labels.
It reuses the existing waveform SVGs, speaker Flash conversion, and background
mask. The original sample square is reproduced with its score color and geometry.
The White Pop film loop (2927) is reconstructed as a three-frame white-circle
pulse. That reconstruction requires comparison with original playback.

Cue boundaries use ElevenLabs character alignment. Animation timing within each
cue is proportional to source score spans and remains provisional because script
holds and jumps are not playback timestamps.

Build another silent review player into a new directory:

```sh
python3 tools/build_lesson.py content/digital-audio.json \
  candidates/lessons/digital-audio-next --recovery recovered --visuals-only
python3 tools/elevenlabs_audio.py preview-elevenlabs \
  --content content/digital-audio.json --lesson digital-audio \
  --candidate candidates/elevenlabs/digital-audio/review-1 \
  --player candidates/lessons/digital-audio-next --all
```

The preview reuses existing recordings without spending credits. Generating
again with the same candidate resumes matching recordings; changing content
requires a new candidate.

## Verification and remaining review

Automated checks cover source coverage, uninterrupted utterance grouping,
rejection of missing source segments and unsupported visual members, sample
marker order and positions, translated labels, asset hashes, narration settings,
and character-aligned cue times. Browser checks exercise offline menu access,
each recording, seeking, navigation between lessons 3 and 4, history, direct-route
reload, and automatic completion. Desktop and mobile captures were inspected (mobile with the lesson list closed).
The full suite passed all 45 tests using the installed Chromium through
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`. All three MP3s decode without FFmpeg errors;
JavaScript syntax and diff whitespace checks passed. Targeted mypy checks of
`tools/digital_audio.py` and `tests/test_digital_audio.py` passed with
`--check-untyped-defs --follow-imports=silent`. Project-wide mypy remains failing
on existing typing errors and missing dependency stubs in the other tools/tests;
those unrelated failures were left unchanged.

Original audio was transcribed locally with cached Whisper `base.en`, using
FFmpeg decoding. No transcription service was used. Windows PowerShell is not
available on this host. Continuous original-playback comparison, listening review
of Russian pronunciation and translation, synchronization review, and native
Windows/macOS acceptance remain outstanding.
