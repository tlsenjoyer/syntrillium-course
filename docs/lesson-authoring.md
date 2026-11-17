# Authoring a Russian lesson

This workflow takes one original course topic through source review, Russian
content, visual conversion, narration approval, and offline player acceptance.
Use it for «Основы звука» first, then repeat it for subsequent lessons.
Run commands from the repository root.

The [requirements](course-requirements.md) and
[acceptance spec](russian-course-spec.md) define the result. Preserve the
curriculum, examples, visual meaning, and event order. Russian layout and timing
may differ. Narration uses complete reviewed utterances, as defined in
[ADR 0001](adr/0001-narration-utterances.md).

## Current first-lesson status

«Основы звука» has a [content draft](../content/sound-fundamentals.json)
covering 14 source segments in nine Russian narration utterances, and a
[source inventory](../content/sources/sound-fundamentals.json). Neither the
transcription nor the translation is approved. Russian audio and cue timings
have been promoted into the review player; final acceptance remains outstanding.

The builder can now create a separate silent first-lesson review player with
all nine utterances and 14 source visual cues. The main player includes all nine
topics. The first lesson bundles all nine
utterances promoted from `review-2`. Content approval, continuous original-playback
comparison, synchronization review, and platform acceptance remain outstanding. The steps below distinguish
review drafts from accepted learner content.

## 1. Establish source coverage and a rendered reference

Follow the [README recovery and audio-export instructions](../README.md#recover-the-original-resources).
Reuse an existing valid recovery rather than overwriting it. Retain executable
and audio hashes, resource IDs, source-segment order, visual member references,
and topic boundaries in the source inventory. For this lesson, the topic starts
at frame 130 and the next topic starts at 1003. Frame addresses are not playback
timestamps: original scripts may hold or jump frames.

Inspect original playback using the
[Windows inspection guide](agents/windows-inspection.md). Capture successive
visual states and record their relationship to the spoken explanation. A static
inventory or screenshot does not establish complete animation behavior. Listen
to the exported original audio as well; the screenshot helper does not record it.

Output: traceable source coverage and reference evidence sufficient to check
every explanation and visual event. Record any missing evidence explicitly.

## 2. Review transcription, translation, and utterances

Use the [local transcription instructions](../README.md#transcribe-original-audio-locally)
when a source transcript is missing. Automatic transcription remains a draft
until checked by listening. Preserve the automatic transcript for provenance;
record verified readings and corrections in review notes.

Author Russian segment text, diagram labels, complete narration utterances,
their covered segment IDs, and visual cue anchors in the lesson content file.
Review groups explicitly; do not regenerate grouping implicitly during audio
production. Keep the complete utterance text and segment captions consistent.

Scientific corrections are permitted after comparison confirms an error in the
original. For each substantive correction, retain the original wording, the
corrected Russian wording, the reason and supporting evidence, and explicit
owner approval before generating narration. Until approval, keep it unresolved
in review notes. This permission does not authorize adding or rewriting the
curriculum. Transcription mistakes are resolved by checking the recording.

For «Основы звука», resolve the segment 1910 transcription uncertainty
(“Horsing” versus “forcing”) and review the segment 1934 ear-receptor wording.
Then approve translation, terminology, utterance boundaries, and cue anchors.
Update review flags only after those reviews. The current draft test explicitly
expects unreviewed flags; update its readiness assertions when review is complete.

Output: reviewed content with no unresolved wording that could invalidate a
paid narration run. No scientific correction is approved merely by this guide.

## 3. Convert visuals and build staged playback data

Reuse extracted assets where they can be localized and played faithfully.
Reconstruction or rendered animation clips are allowed when needed, after
comparison with the original. Translate visible labels and preserve proportions,
meaning, and event order. For this lesson, convert the speaker-cone bitmaps,
ear graphic, and runtime pressure-wave animation.

Build a new staged player without making a speech request:

```sh
python3 tools/build_lesson.py content/sound-fundamentals.json \
  candidates/lessons/sound-fundamentals --recovery recovered --visuals-only
```

Open `candidates/lessons/sound-fundamentals/index.html`. Existing output is never
overwritten; use a new path for a rebuild. The first-lesson compiler validates
source coverage separately from Waveforms, converts all nine original RGBA
speaker-cone BITDs and the original ear Flash outline, and reuses the recovered
ball and sine assets already bundled in `player/assets/`. It preserves the
source score's visual order and label placement. Particle motion is a draft
longitudinal-wave reconstruction, and mapping score spans onto source narration
durations is provisional. Compare both against continuous original playback
before approving visual fidelity. The final waveform/particle arrangement is
also a reconstruction requiring that comparison.

The staged player runs silently for utterances without approved audio, supports
pause and seeking, and identifies the draft and provisional timing in Russian.
No silence file is generated or presented as approved narration.

The output must include the lesson's `lesson.js`, bundled visual assets, and
utterance cues that refer to the reviewed source segments. Prepare a separate
staged player directory with the player shell and these lesson-specific files.
Existing narration preview and promotion accept this directory through
`--player`. Keep the current Waveforms player intact while preparing the lesson.

Output: staged lesson visuals and cue data suitable for candidate narration
review. Estimated cue timings are provisional until checked against the audio.

## 4. Generate, preview, and approve narration

Follow the [ElevenLabs setup](../README.md#generate-lesson-narration-with-elevenlabs).
Keep credentials in the environment or ignored local env files. Select a voice
and model for the candidate. After content review, this existing command can
generate the first utterance; replace `VOICE_ID` and `MODEL_ID` before running:

```sh
python3 tools/elevenlabs_audio.py generate-elevenlabs \
  --content content/sound-fundamentals.json --lesson sound-fundamentals \
  --voice-id VOICE_ID --model-id MODEL_ID --utterances 1892 \
  --candidate candidates/elevenlabs/sound-fundamentals/review-1
```

Generation spends service credits. Reuse the same candidate path to resume a
matching partial run; use a new candidate for changed text or generation settings.
After approving the initial voice sample, request the remaining utterances with
`--all` instead of `--utterances 1892`.

After step 3, preview against the staged player:

```sh
python3 tools/elevenlabs_audio.py preview-elevenlabs \
  --content content/sound-fundamentals.json --lesson sound-fundamentals \
  --candidate candidates/elevenlabs/sound-fundamentals/review-1 \
  --player candidates/lessons/sound-fundamentals --utterances 1892
```

Open the candidate's `preview/index.html`. Listen for pronunciation, natural
delivery, complete speech, and pauses. Check visual events against the relevant
spoken words throughout each utterance. Missing or unusable alignment requires
manual cue-time correction before preview and promotion can succeed.

Promote only the explicitly reviewed selection:

```sh
python3 tools/elevenlabs_audio.py promote-elevenlabs \
  --content content/sound-fundamentals.json --lesson sound-fundamentals \
  --candidate candidates/elevenlabs/sound-fundamentals/review-1 \
  --player candidates/lessons/sound-fundamentals --utterances 1892
```

Repeat review and promotion for every utterance. Candidate audio is not approved
learner audio until this review is complete. Always provide `--content`; its
current default points to Waveforms.

## 5. Integrate the lesson and verify acceptance

The first lesson is now bundled at `player/lessons/sound-fundamentals/`, and the
main `player/index.html` enables all nine topics. Selection, previous/next lesson
controls, fragment routes, and browser history follow
[ADR 0002](adr/0002-lesson-navigation-and-routes.md); changing lessons stops old
narration. Browser checks cover offline
first-lesson playback, asset paths, switching, reloads, and history.

The bundled first lesson initially uses the nine utterances promoted from
`review-2`. For subsequent narration promotions into this integrated copy, use
`--player player/lessons/sound-fundamentals` instead of the staged player path.
The staged player remains the standalone source for candidate previews.
Integration does not approve translation, visual fidelity, synchronization, or
target-platform acceptance; complete the reviews below before accepting it.

Lesson 3 has its own [production and review record](analog-audio-review.md).
Its bundled narration remains candidate audio pending listening review.
Lesson 4 likewise has a [production and review record](digital-audio-review.md)
and bundled candidate narration, accessible from the main menu.
Lesson 5 has a [production and review record](sampling-rate-review.md) and ten
bundled candidate utterances, also accessible from the main menu.

Lesson 6 has a [production and review record](bit-depth-review.md) and thirteen
bundled candidate utterances, accessible from the main menu and lesson 5.

Lesson 7 has a [production and review record](digital-summary-review.md) and four
bundled candidate utterances, accessible from the main menu and lesson 6.

Lessons 8 and 9 share a [production and review record](final-lessons-review.md)
and bundle 15 and 12 candidate utterances respectively. Both are accessible from
the main menu, the lesson list, and the preceding lesson.

Useful existing checks:

```sh
python3 -m unittest discover -s tests -p test_sound_fundamentals.py
python3 -m unittest discover -s tests -p test_sound_fundamentals_build.py
python3 -m unittest discover -s tests
mypy --check-untyped-defs tools tests
```

The first checks verify draft source coverage, utterance validity, asset
conversion, rejection of incomplete inputs, and silent offline transport and
history when Playwright is installed. They do not prove translation accuracy,
visual fidelity, or narration readiness.
Player checks require Playwright and an installed browser; a skipped check is
not playback evidence.

Before accepting the lesson, record evidence for each of these checks:

- Every original explanation, example, and visual event is accounted for;
  any scientific correction has its explicit approval record.
- Interface text, captions, and diagram labels are Russian and fit their layout.
- Every narration utterance plays uninterrupted, with correct pronunciation
  and visual synchronization, including after seeking and navigation.
- Comparison with original playback confirms visual meaning and event order.
- A fresh launch with networking disabled completes the lesson on both Windows
  and macOS, using only bundled media.

Record platform/browser versions, reviewers, reference evidence, results, and
remaining failures with the lesson review. Passing integrity tests or one host's
browser checks cannot substitute for the human and target-platform reviews.
