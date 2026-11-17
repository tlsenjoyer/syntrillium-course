# Lesson 5: Sampling Rate

Open `player/index.html#lesson/sampling-rate` to review «Частота дискретизации».
It is enabled in the main menu, lesson list, and lesson 4's next-lesson control.
All media is bundled for offline playback.

## Content and narration

The topic covers original score frames 3697–4683, before Bit Depth at 4684.
All thirteen narration resources (2228 through 2300, in increments of six) are
retained in source order. The [source inventory](../content/sources/sampling-rate.json)
records audio hashes, durations, frame spans, and visual member references.
[Russian content](../content/sampling-rate.json) retains automatic English
transcripts, translations, ten complete utterances, and visual cue anchors.

Resources 2252/2258 combine the sample-density comparison into one sentence;
2264/2270 combine the frequency-range explanation; 2276/2282 keep the 8 kHz /
16,000 samples-per-second example uninterrupted. Automatic transcripts were
produced locally using cached Whisper `base.en` and FFmpeg decoding. Trailing
ASR punctuation in 2294 is omitted from Russian speech. The Nyquist labels use
“как минимум вдвое” to match the source narration's “at least twice.” The source's
simplified exact 8 kHz / 16 kHz example is retained without a scientific revision.
Transcription and translation remain unreviewed.

Ten recordings, totaling about 72 seconds, were generated using the authorized
ElevenLabs voice `3EuKHIEZbSzrHGNmdYsx`, model `eleven_v4_turbo`, and output format
`mp3_44100_128`. Candidate: `candidates/elevenlabs/sampling-rate/review-1`.
The [bundled metadata](../player/lessons/sampling-rate/generation.json) records
settings, request IDs, audio hashes, character alignment, and cue times under
`candidate_utterances`. Audio is available for review; it is not marked approved.

## Visual conversion

`tools/sampling_rate.py` preserves score event and channel order, reusing the
existing waveform and sample-square conversion. The diagram starts with 21
markers and adds intervening markers to reach 41 during the doubling explanation.
Six definitions cover sampling rate, CD quality, the 8 kHz example, the minimum
sampling rate, the Nyquist theorem, and Nyquist frequency. Russian labels retain
source placement with line wrapping for readable text.

Cue boundaries use ElevenLabs character alignment. Within-cue animation timing
is proportional to source frame spans and remains provisional: original scripts
can hold or jump frames.

Build a fresh silent review player and reuse the existing audio without spending
credits:

```sh
python3 tools/build_lesson.py content/sampling-rate.json \
  candidates/lessons/sampling-rate-next --recovery recovered --visuals-only
python3 tools/elevenlabs_audio.py preview-elevenlabs \
  --content content/sampling-rate.json --lesson sampling-rate \
  --candidate candidates/elevenlabs/sampling-rate/review-1 \
  --player candidates/lessons/sampling-rate-next --all
```

## Verification and remaining review

Automated checks cover source coverage, sentence grouping, sample-marker order,
all six translated definitions, rejection of missing source coverage and unknown
visuals, audio hashes, requested voice/model, and aligned cue boundaries.
Browser checks exercise offline menu access, all ten recordings, seeking,
lesson 4/5 navigation, browser history, route reload, and automatic completion.
Desktop and mobile captures were visually inspected, with no horizontal overflow.
The regression run passed the other 49 tests; all five lesson-five checks passed
on the final focused run after the seek assertion was changed to calculate the
actual within-utterance offset. All ten MP3 files decode with FFmpeg.
Targeted mypy checks pass for the new
compiler and tests; JavaScript syntax and diff whitespace checks pass.

Windows PowerShell is unavailable on this host. Continuous original-playback
comparison, Russian listening and translation review, synchronization review,
and native Windows/macOS acceptance remain outstanding.
