# Lesson player controls and layout

Agreed scope for refining the single-lesson offline sample:

- Keep icon-only playback controls with Russian tooltips and accessible names.
  Make play/pause more prominent than previous/next narration utterance controls.
  At the end, show a single replay arrow in that same control.
- Use a captions icon with a visible on/off state; preserve the saved preference.
- Remove the completion message and separate replay button.
- Place a small course breadcrumb above the left-aligned lesson title, followed
  by lesson number and duration, all above the visualization.
- Move previous/next lesson navigation to the lesson footer. Include the adjacent
  lesson titles. Unavailable lessons remain disabled without extra status text.
- Opening a lesson leaves narration paused until the learner presses Play.
- Use a 270px desktop syllabus sidebar. When collapsed, remove its column and
  center the lesson. Retain the single-column mobile layout.
- Leave visualization sizing, annotations, and educational content unchanged.

These are reversible interface choices; they do not require an architectural
change or new domain terminology. Lesson availability still follows ADR 0002.
