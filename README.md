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
