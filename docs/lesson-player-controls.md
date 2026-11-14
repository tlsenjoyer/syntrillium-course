# Lesson player controls and layout

Agreed scope for refining the single-lesson offline sample:

- Keep icon-only playback controls with Russian tooltips and accessible names.
  Give all playback buttons the same size; distinguish Play/Pause with color.
  At the end, show a single replay arrow in that same control.
- Use a captions icon with a visible on/off state; preserve the saved preference.
- Remove the completion message and separate replay button.
- Place a small course breadcrumb above the left-aligned lesson title, followed
  by lesson number and duration, all above the visualization.
- Move previous/next lesson navigation to the lesson footer. Include the adjacent
  lesson titles. Unavailable lessons remain disabled without extra status text.
- Opening a lesson leaves narration paused until the learner presses Play.
- The course title in the header links to the main menu, stopping narration.
- Use a 270px desktop syllabus sidebar. When collapsed, remove its column and
  center the lesson. Retain the single-column mobile layout.
- Preserve visualization proportions, annotations, and educational content.

## Laptop layout refinement

The reference laptop uses a 1920×1080 display at 1.6 display scaling. Its
nonmaximized browser screenshot corresponds to approximately 1200×565 CSS pixels.
At 100% browser zoom, prioritize the visualization, playback controls, and captions
together in that viewport:

- Keep the animation panel's full available width. Increase its height on short
  desktop windows so the diagram grows without stretching or cropping.
- Compact the course header and lesson heading on these windows; put the course
  return link beside the title and metadata.
- Reduce playback controls and their spacing. All buttons use 36px targets with
  20px icons; preserve equal 44px targets for coarse pointers.
- Use 16px captions with tighter spacing on short desktop windows, reserving
  two lines. Keep larger captions in other layouts and allow longer text to flow.
- Leave adjacent-lesson navigation below the playback area; it may require
  scrolling. Very short or narrow windows also retain normal document scrolling.

These are reversible interface choices; they do not require an architectural
change or new domain terminology. Lesson availability still follows ADR 0002.

## Animated course navigation

The next refinement prioritizes lesson space and focus, with a persistent burger
for course navigation. Both the burger and panel animate together. Navigation
starts open by default, including on narrow screens. Opening and closing it does
not interrupt narration. Keyboard access and reduced-motion feedback are required.

Selected after comparing a sliding drawer, a push sidebar, and a compact floating
panel: the 270px sidebar pushes the lesson on desktop and recenters it when
closed. The panel slides and wipes away as the burger changes from a close icon
to three lines, using a coordinated 380ms transition. At 850px and below, the
panel overlays the lesson so the diagram retains its width. Escape closes it;
closed navigation leaves the keyboard order immediately. Reduced motion uses a
brief fade with an immediate layout change. Preserve the course palette and
content. These are reversible interface choices, not a new ADR.
