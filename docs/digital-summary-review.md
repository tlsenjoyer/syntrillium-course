# Lesson 7 · Digital Summary

Open [«Итоги: цифровой звук»](../player/index.html#lesson/digital-summary) from
the main menu, lesson list, or lesson 6's next-lesson control. Playback uses
bundled files and works offline.

The lesson covers original score frames 5985–6376 and all six narration
resources in source order. The [source inventory](../content/sources/digital-summary.json)
records the score spans and hashes. The [Russian content](../content/digital-summary.json)
includes the local Whisper `base.en` transcripts, Russian text, and four
complete utterances. Segment 2762 uses the general term «преобразователь» in
the recording explanation. Segment 1648 names the digital-to-analog converter
used for playback.

ElevenLabs generated about 27 seconds of Russian narration using voice
`3EuKHIEZbSzrHGNmdYsx`, model `eleven_v4_turbo`, and format `mp3_44100_128`.
The candidate is in `candidates/elevenlabs/digital-summary/review-1`. The
[bundled metadata](../player/lessons/digital-summary/generation.json) records
audio hashes, character alignment, and cue boundaries. Narration is a review draft.

The visual compiler uses the recovered microphone and sound-card Flash
illustrations, waveform, sample squares, and directional arrows. It places the
longer Russian labels above nearby arrows where needed. Cue boundaries use
ElevenLabs alignment. Animation timing within each cue follows score spans
and is provisional.

The automated checks cover score event coverage, audio hashes and cue
alignment, all four tracks playing through to completion offline, navigation
between lessons 6 and 7, and a direct route reload. All four MP3s decoded with
FFmpeg. Russian listening and synchronization review, continuous comparison
with the original Windows playback, and native Windows/macOS acceptance are pending.
