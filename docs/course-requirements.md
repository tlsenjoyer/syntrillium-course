# Russian course adaptation

Confirmed requirements from the design interview:

- Adapt the complete Syntrillium introductory audio course in `course.exe`.
- Preserve the original curriculum, lesson order, explanations, and examples;
  use natural Russian translation. Flag outdated material for user review.
- Scientific errors confirmed against the original may be corrected in Russian.
  Preserve the original wording, document the correction and evidence, and obtain
  explicit owner approval for each substantive correction before narration generation.
- Translate all learner-facing text, including interface text and labels inside
  diagrams and animations. Retain standard symbols and units where appropriate.
- Replace all spoken narration with Russian narration. Use ElevenLabs for
  production generation; keep provider access out of learner playback.
- Preserve the meaning and sequence of visualizations and animations. The user
  confirms that these are noninteractive.
- Animation timing and pauses may change to synchronize with Russian narration.
- Generate Russian narration as complete sentences or short coherent passages,
  even when they span multiple source segments. Repair existing split-sentence
  narration and prevent the same fragmentation in future generation.
- Play each narration utterance as one uninterrupted recording, with visual
  changes timed within it. Retain source segments for provenance and visual cues.
- Previous and next navigation move between narration utterances. Timeline
  seeking remains available within utterances.
- Save each narration utterance's complete Russian text and the source segments
  it covers in lesson content; review suggested groups before using them.
- Time visual changes to the relevant spoken words and check synchronization
  during narration review.
- The user reports that the original course contains no separate example audio.
- Deliver an installable desktop app for Windows, macOS, and Linux with all
  course content usable offline after installation.

Technical investigation and delivery choices remain open. These requirements
do not approve a particular reconstruction method or implementation plan.
