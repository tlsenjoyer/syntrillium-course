# Original course recovery

This is an initial recovery step for issue #1, not first-milestone acceptance.
No Russian lesson, narration, player, offline package or macOS validation is
included. The source executable remains unchanged.

## Reproducible static inventory

Run the recovery command in the root README. It produces a hash inventory and
keeps encoded/unsupported resources visible rather than silently dropping them.

- Executable SHA-256: `c385ac83b9cad64cc988d37b8e5b3c30586fcf63c478d56d473a5dcf5c360725`.
- Embedded movie: offset 1,824,106, length 2,748,581 bytes, Director 8.0#178.
- Movie SHA-256: `22da91b72ebe249ca6045ff3cd58e83d8d806b67cdcf6a1e35f3a78c2dba00ce`.
- 880 resource-map entries; 441 cast members, 68 BITD resources,
  111 XMED resources, 151 ediM resources, 38 Lscr resources and 12 cast libraries.
- 15 uncompressed Flash files recovered from XMED resources. Header and file
  length checks pass; rendering, localization and coverage remain unverified.
- Cast member names and media links are recovered from CASt and KEY*.
  A missing key target is marked `present: false`, not treated as an extracted
  file. Such entries include optional thumbnails and sound metadata. The
  inventory does not yet distinguish optional links from required lesson media.
- Proprietary SWA-compressed `snd ` data is preserved as encoded bytes. The
  container's `decoded` state means container decompression only. Audio
  classification, full narration coverage and durations remain unverified.
- An exploratory `ffprobe` of ediM resource 2000 recognizes MP3 and estimates
  2.82125 seconds. Subsequent probing identifies all 151 ediM resources as MP3;
  the audio export below decodes every one rather than relying on probing alone.

The extractor supports this movie's little-endian Afterburner container, zlib
resource map and initial-load segment. It is not a general Director decompiler.
Output is rejected for truncated input, invalid map lengths and invalid cast
information. It refuses existing destinations. All 879 resources not marked encoded were
compared byte for byte with an independent ProjectorRays chunk dump; all matched. All output is generated locally;
there are no learner playback dependencies yet.

## Decompilation evidence

[ProjectorRays](https://github.com/ProjectorRays/ProjectorRays) commit
`6f9bceb` successfully decompiled the extracted movie and dumped Lingo scripts
and metadata in this workspace. Build requires a C++17 compiler, Boost headers,
zlib and mpg123. With an installed binary, reproduce from a fresh recovery:

```sh
mkdir -p /tmp/syntrillium-decompiled
projectorrays decompile recovered/movie.dcr --dump-scripts --dump-json \
  --output /tmp/syntrillium-decompiled
```

Outputs appear under `movie/casts/`, `movie/chunks/` and `movie.dir`. Those
outputs are investigation artifacts, not committed learner content. The recovery
script's container interpretation follows ProjectorRays' `dirfile.cpp`,
`stream.cpp` and `chunk.cpp` and is marked MPL-2.0 accordingly.

## Rendered reference and navigation

On 2026-11-12 the original executable launched on the Windows 11 host through
WSL2. Windows processes require sandbox escalation for WSL interoperability.
Both the WSL UNC source and a Windows-local temporary copy launched successfully.

The projector creates a small window titled `course` as well as the actual
window titled `A Short Course in Digital Audio` in the same process. Selecting
`Process.MainWindowHandle` captured the small host window. Enumerating visible
windows by process ID and title found the rendered course. `PrintWindow` of
that handle captured the menu. Its native screenshot was visually inspected;
window-relative mouse messages opened the topic menu. This establishes menu
rendering/navigation only, not lesson sound or animation fidelity.

[Original topic menu](references/original-topic-menu.png) is the selected rendered
reference. It shows the following order. Entry frames come independently from
the decompiled `go navVar ... in button` scripts, which set `navVar` before a
shared navigation script jumps to it. These are Director frame addresses, not
elapsed seconds, durations or verified lesson boundaries.

| Original topic | Entry frame |
| --- | ---: |
| Sound Fundamentals | 130 |
| Waveforms | 1003 |
| Analog Audio | 2814 |
| Digital Audio | 3389 |
| Sampling Rate | 3697 |
| Bit Depth | 4684 |
| Digital Summary | 5985 |
| Computer Audio | 6377 |
| MIDI | 8022 |

## Static composition and decoded audio

The standard recovery command now also writes `composition.json`. Its library
membership and cast names agree with ProjectorRays' MCsL, CAS* and CASt output.
Score format interpretation was researched against the primary implementations
in [ScummVM score.cpp](https://github.com/scummvm/scummvm/blob/master/engines/director/score.cpp)
and [frame.cpp](https://github.com/scummvm/scummvm/blob/master/engines/director/frame.cpp).

- All 441 cast resources are assigned to 12 libraries with member numbers.
- The score declares and decodes 9,416 frames, with nominal playback at 15 fps
  and a 500×375 stage. The file has 1,006 score channels (including six main
  channels) and 150 displayed sprite channels.
- Recovered spans include 4,949 sprite states, 141 sound references, 16 frame
  script references, two transition states and two palette states. Sprite spans
  retain their complete 48-byte records as well as registration-point coordinates,
  dimensions, cast references and detail indices. Detail indices are **not**
  script IDs: the 1,281 nonempty score detail records remain referenced by byte
  offsets in the preserved VWSC resource. Their behavior lists are not decoded.
- All 96 rich-text resources have length-checked text bodies. The other 15 XMED
  resources are the already-recovered Flash candidates. Formatting and original
  font glyph mapping are not applied. CP1252 text decoding is provisional,
  particularly the non-ASCII glyph in `director trademark`; inspect the rendered
  original before using those characters in translation. Embedded bitmap/Flash
  labels are not recovered as text by this step.
- All labels are retained, including numeric navigation markers and comments.
  The nine topic entry addresses above are emitted only for the known executable
  SHA-256. A different source cannot silently inherit this navigation profile.
- The End marker at frame 9,293 has a frame-script library value of `16388`
  (`0x4004`) and member 1. It is retained in `unresolved_cast_references` rather
  than guessed to be library 4. Other score cast references resolve successfully.

These are static score states, not executed animation or a complete lesson
composition. Lingo changes sprite properties and playback position. In
particular, `animation background script` holds frames while sound channel 1
is busy. Converting frame addresses directly to seconds would lose that behavior.
The first score sound starts at frame 131 and references Audio member 5,
`course005`; numeric resource IDs and names are not curriculum ordering.

With FFmpeg installed, run the optional audio export documented in the README.
It validates resource hashes before writing output, decodes all 151 ediM
resources to PCM WAV, and records hashes, sample counts, rates and durations in
`audio.json`. The combined decoded duration is approximately 648.19 seconds;
this includes menu/exit resources and is **not** a measured course runtime.
All 141 static score sound references point to exported WAVs. Roles still need
classification by listening. MP3 encoder delay and any Director-specific trim
behavior have not been compared with original playback.

The only unexported sound member is Audio member 1, `quit`, with encoded `snd `
resource 1870. It remains explicit as unsupported rather than being omitted.
The separate `quit2` score sound has an ediM resource and exports successfully.

On 2026-11-12 a fresh background inspection confirmed the original main menu
and all nine topic labels in order. Opening Waveforms displayed the pressure,
amplitude and zero-line visualization; later playback had advanced to Analog
Audio. Screenshots were visually inspected in `/tmp`. The background workflow
worked once the real stage was available; it did not require foreground capture.
This adds visual navigation evidence, not continuous audiovisual comparison.
The instance launched for this inspection was closed afterward.

Waveforms is a promising representative lesson: its entry interval references
15 rich-text members and four Flash members (`sin`, `complexwave1`,
`complexwave2`, `backball`), as well as scripted sprite motion. Those counts use
the provisional interval from its entry to Analog Audio's entry and do not
establish exact lesson boundaries or complete rendered coverage.

## Remaining recovery and delivery work

1. Decode score detail behavior lists and script behavior into executed lesson
   composition and timing. Static spans and labels are now recovered, but are
   insufficient to reproduce runtime animation and narration holds.
2. Recover text embedded in bitmaps/Flash and verify rich-text glyph mapping.
   Transcribe and classify the exported English audio, then verify its mapping
   and trimming against rendered score segments.
3. Capture continuous original lesson playback with audio and known positions.
   Still images cannot establish event order, pauses or synchronization.
4. Exercise Flash rendering before choosing reuse, reconstruction or rendered
   clips. Several visuals also depend on Director scripting; SWFs alone cannot
   be assumed to cover the complete course.
5. Choose a lesson covering the recovered media types, translate its complete
   text/narration, build offline playback, and compare with the original.
   Human translation/pronunciation review and fresh offline launches on Windows
   and macOS remain acceptance requirements. No macOS environment is available
   in this workspace.

Potentially dated statements are visible in member names (for example CD/DVD
bit-depth guidance, Cool Edit, Windows 95/98/NT and cooledit.com). Recover exact
wording and context before presenting curriculum-change decisions to the owner.
No curriculum statements have been modernized or rewritten.
