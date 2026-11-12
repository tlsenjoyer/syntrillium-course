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
  2.82125 seconds. This single probe does not classify all ediM resources or
  establish narration-to-lesson mapping.

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

## Remaining recovery before choosing a representative lesson

1. Decode the score (`VWSC`), labels (`VWLB`), library membership and script
   behavior into ordered lesson composition, placement and timing. Match cast
   media references to those events; a resource inventory alone is insufficient.
2. Recover all visible text, including XMED rich text and text embedded in
   bitmaps/Flash. Inventory English narration and match it to score segments.
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
