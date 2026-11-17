# Lessons 8 and 9 · Computer Audio and MIDI

Open [«Звук на компьютере»](../player/index.html#lesson/computer-audio) or
[«MIDI»](../player/index.html#lesson/midi) from the main menu or the lesson list.
The sequential controls connect lessons 7, 8, and 9. Playback uses bundled media.

- Computer Audio covers original score frames 6377–8021. All 27 source
  segments are grouped into 15 complete Russian utterances. The visuals follow
  the recording and playback paths, show the sample values and audio file
  header, and build up the CD-quality size calculation.
  [Source inventory](../content/sources/computer-audio.json) ·
  [Russian content](../content/computer-audio.json)
- MIDI covers frames 8022–9294. Its 20 source segments include the end-of-course
  narration and closing card, grouped into 12 Russian utterances. The menu
  return and quit sound are outside that range. The score carries the preceding
  file-size calculation into the MIDI introduction, then shows the file-size
  comparison, notation, synthesizer playback, and closing card.
  [Source inventory](../content/sources/midi.json) · [Russian content](../content/midi.json)

Both drafts retain the automatic Whisper `base.en` readings and the original
course's historical hardware examples and storage approximations. The closing
card preserves the historical Cool Edit address as plain text for offline review.

The visual compiler uses the recovered waveform, sound card, speaker, tape
recorder, arrow, and brackets. The MIDI note, clef, and historical logos are
transparent first-frame exports from the recovered Flash assets, rendered in
[Ruffle 0.7.1](https://ruffle.rs/downloads.html). Both lessons use the original
score event order. Timing within each narration cue remains provisional.

The 27 offline MP3 files were generated with ElevenLabs voice
`3EuKHIEZbSzrHGNmdYsx`, model `eleven_v4_turbo`, and format
`mp3_44100_128`. They use ElevenLabs character alignment for cue boundaries.
Bundled generation records contain the candidate audio hashes and cue times.
[Computer Audio generation](../player/lessons/computer-audio/generation.json) ·
[MIDI generation](../player/lessons/midi/generation.json)

FFmpeg decoded all 27 tracks. Offline Chromium played both lessons from the
main menu through the end and verified sequential navigation, browser history,
and a route reload.

The narration is bundled for review. Listening and synchronization review,
continuous comparison with the original Windows playback, and Windows/macOS
acceptance remain pending.
