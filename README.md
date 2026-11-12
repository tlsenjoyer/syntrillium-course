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
order. Container decompression does not decode Director images, audio or scores.

See [recovery findings and remaining work](docs/recovery.md) before using these
assets as lesson inputs. For Windows inspection, follow
[the project guide](docs/agents/windows-inspection.md).
