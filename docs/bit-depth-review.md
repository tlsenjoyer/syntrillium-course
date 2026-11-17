# Lesson 6: Bit Depth

Open `player/index.html#lesson/bit-depth` to review «Разрядность». It is enabled
in the main menu, lesson list, and lesson 5's next-lesson control. All media is
bundled for offline playback.

## Content and narration

The topic covers original score frames 4684–5984, before Digital Summary at
5985. All eighteen original narration resources are retained in source order:
2306–2378 in steps of six, then 2390, 2396, 2402, 2408 and 2414.
The [source inventory](../content/sources/bit-depth.json) records audio hashes,
durations, frame spans and visual references. The [Russian content](../content/bit-depth.json)
retains automatic English transcripts, translations and thirteen complete
narration utterances with visual cue anchors.

Transcription used cached local Whisper `base.en`. The opening explanation,
two-bit example, additional-bit explanation and CD/DVD examples each combine
related source segments into uninterrupted speech. ASR mistakes in 2312, 2354
and 2360 are interpreted using context and the original diagrams. The original
CD/DVD quality examples are retained. Transcription and translation remain
unreviewed.

Thirteen recordings totaling about 97 seconds were generated using the
authorized ElevenLabs voice `3EuKHIEZbSzrHGNmdYsx`, model `eleven_v4_turbo`,
and `mp3_44100_128` format. Candidate:
`candidates/elevenlabs/bit-depth/review-1`.
The [bundled metadata](../player/lessons/bit-depth/generation.json) retains
request IDs, hashes, character alignment and cue times under
`candidate_utterances`. Narration is available for review and is not marked
approved.

## Visual conversion

`tools/bit_depth.py` preserves score event and channel order using the existing
waveform, primitive lines and sample square. Localized labels cover bit depth,
single-bit values, one/two/three-bit tables, and the CD/DVD amplitude counts.
State numbers align with the original binary digit rows. The source waveform
occupies four levels in the two-bit example and seven of eight possible levels
in the three-bit example; the source's eight reference lines are retained.

Cue boundaries use ElevenLabs character alignment. Within-cue event timing is
proportional to score frame spans and remains provisional because original
scripts can hold or jump frames.

To rebuild a fresh silent player and preview existing narration without spending
credits, choose a new output directory:

```sh
python3 tools/build_lesson.py content/bit-depth.json \
  candidates/lessons/bit-depth-next --recovery recovered --visuals-only
python3 tools/elevenlabs_audio.py preview-elevenlabs \
  --content content/bit-depth.json --lesson bit-depth \
  --candidate candidates/elevenlabs/bit-depth/review-1 \
  --player candidates/lessons/bit-depth-next --all
```

## Verification and remaining review

Automated checks cover source coverage, complete utterances, translated labels,
binary table sizes and row alignment, occupied amplitude levels, rejection of
missing coverage and unknown visuals, audio and vector hashes, the requested
voice/model, and aligned cue boundaries. Offline browser checks exercise menu
access, all thirteen recordings, seeking, lesson 5/6 navigation, browser history,
route reload and automatic completion. Desktop and mobile screenshots are
inspected for layout and overflow. All thirteen MP3s decode with FFmpeg.

The full regression suite passes all 53 tests using the installed Chromium
(`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium`). Targeted mypy checks
pass for the new compiler and tests, and JavaScript syntax and diff whitespace
checks pass. Broader mypy analysis still reports five existing errors in shared
tooling (ElevenLabs typing, Flash path typing and the optional Piper import).

Windows PowerShell is unavailable on this host. Continuous original-playback
comparison, Russian listening and translation review, synchronization review,
and native Windows/macOS acceptance remain outstanding.
