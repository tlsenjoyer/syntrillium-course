## Problem Statement

The original course is Syntrillium's introductory audio course, distributed as a self-contained Windows executable. The user wants its complete educational content available in Russian on Windows and macOS, with the original visualizations and animations preserved and all course playback available offline. Translating narration alone would leave English interface text and diagram labels, and would risk losing synchronization between explanations and visuals.

## Solution

Create a Russian adaptation that preserves the original course's curriculum, lesson order, explanations, examples, and visual demonstrations. Translate all learner-facing text and replace spoken narration with natural Russian narration. Preserve each visualization's meaning and sequence while allowing timing changes to fit Russian speech.

Begin with recovery of the original course's content and structure, then deliver one representative, complete Russian lesson as the first milestone. Validate that lesson against the original course before scaling the method to the full curriculum. Deliver the finished course for offline use on Windows and macOS after initial download or installation; web versus desktop packaging remains an implementation choice.

## User Stories

1. As a Russian-speaking learner, I want the complete original curriculum, so that I can study the same introductory audio material.
2. As a learner, I want the original lesson order preserved, so that explanations build on the same foundations.
3. As a learner, I want all original explanations retained in natural Russian, so that translation does not remove educational detail.
4. As a learner, I want the original examples retained, so that abstract concepts keep their concrete illustrations.
5. As a learner, I want Russian navigation labels, so that I can move through the course without knowing English.
6. As a learner, I want Russian interface messages and instructions, so that I can understand how to use the course.
7. As a learner, I want Russian text within diagrams, so that I can understand the concepts they illustrate.
8. As a learner, I want Russian labels within animations, so that their changing content remains understandable.
9. As a learner, I want conventional symbols and units retained where appropriate, so that scientific notation stays recognizable.
10. As a learner, I want every spoken explanation in Russian, so that I can follow the course by listening.
11. As a learner, I want narration with intelligible pronunciation of audio terminology, so that technical explanations are clear.
12. As a learner, I want translations to use consistent terminology, so that the same concept remains recognizable across lessons.
13. As a learner, I want the original visualizations preserved faithfully, so that I can see the demonstrations that support the explanations.
14. As a learner, I want animations to preserve their original meaning and sequence, so that the illustrated relationships remain correct.
15. As a learner, I want narration synchronized with the relevant visual events, so that I can connect what I hear with what I see.
16. As a learner, I want adequate pauses and animation timing for Russian explanations, so that the course does not rush or cut off speech.
17. As a learner, I want translated text to fit within the interface and visuals, so that labels remain readable and unobscured.
18. As a learner using Windows, I want to run the Russian adaptation, so that I can study on my computer.
19. As a learner using macOS, I want to run the same Russian adaptation, so that I can study without a Windows environment.
20. As a learner, I want the entire course available offline after its initial download or installation, so that internet availability does not interrupt learning.
21. As a learner, I want narration and visualizations to remain available offline, so that offline playback preserves the complete lesson experience.
22. As the course owner, I want one representative Russian lesson validated first, so that I can assess translation, narration, visual fidelity, and timing before full conversion.
23. As the course owner, I want an inventory mapping recovered material to lessons, so that missing content can be identified before release.
24. As the course owner, I want outdated material flagged for my decision, so that curriculum changes remain deliberate.
25. As the course owner, I want reuse and reconstruction choices checked against the original course, so that implementation convenience does not silently change the content.

## Implementation Decisions

- The approved approach is content recovery followed by a cross-platform course player. The executable is the source artifact; its native playback engine need not be ported.
- Reverse engineering and decompilation may use Director-specific tooling, REA, or both. Tool selection should follow the evidence rather than require a particular product.
- Recover and inventory text, narration, images, embedded animations, lesson structure, navigation, placement, and timing. Extracted files alone do not establish the complete lesson composition.
- Establish a rendered reference of the original course for comparison. Its runtime behavior remains unverified in the current workspace.
- Separate recovery/conversion tooling from the content consumed by the learner-facing player. Keep lesson ordering and synchronization explicit in the recovered content representation; the exact schema is not yet chosen.
- The first delivery milestone is one complete representative Russian lesson, covering visible text, narration, visualization playback, timing, navigation needed to access it, and offline operation. Choose the lesson after inventory reveals the relevant media types; an unrepresentatively simple lesson must not stand in for unresolved playback requirements.
- Full-course conversion follows validation of that first lesson. The overall scope remains the complete original course.
- All learner-facing English text is translated, including text embedded in images or animation assets. Preserve conventional symbols and units where appropriate. Layout and typography may change to accommodate Russian text.
- All spoken narration is replaced with Russian narration. ElevenLabs is a candidate for generation, not a committed dependency. Generation may happen during production; learner playback must work offline without a narration service.
- The user confirms that the visualizations are noninteractive and that the original course has no separate example audio. Asset references discovered during extraction must be classified rather than assumed to represent extra sound demonstrations.
- Reuse extracted animations where fidelity, localization, and playback permit. Test Flash playback compatibility before adopting an emulator. Reconstruction or rendered animation clips are permitted where needed, provided meaning and sequence remain faithful.
- Adjust animation duration and pauses to synchronize with Russian narration. Exact English playback duration is not a fidelity requirement.
- Web versus desktop packaging, the player framework, codecs, supported operating-system versions, and narration voice remain open implementation choices. Decide from the sample lesson and offline/cross-platform verification rather than inventing constraints now.
- Existing repository content consists of the source executable, glossary, requirements, and agent configuration. There is no existing player, application interface, test suite, or architectural decision record to extend.

## Testing Decisions

- Confirmed primary test boundary: the complete lesson as experienced through the delivered course player. Exercise the real translated content, narration, visualizations, and navigation together rather than mocking the media pipeline.
- A good test asserts learner-visible behavior or educational fidelity. Avoid tests tied to a particular component tree, extraction algorithm, or internal animation implementation.
- At that boundary, verify that the representative lesson can be opened and completed, with Russian interface text, Russian labels within visuals, complete Russian narration, and visual events aligned with the corresponding explanation. Check for clipping, omitted content, and interrupted speech.
- Compare the sample lesson against the rendered original for educational content, visual meaning, event order, and completeness. Permit the explicitly approved translation, typography, layout, and timing changes. Include human review of translation, technical pronunciation, and perceptual synchronization; automated playback checks cannot establish those qualities by themselves.
- Verify the delivered sample on both Windows and macOS. After initial download or installation, disable networking and verify access, complete playback, local narration, and all visualizations. Exercise a fresh launch in the offline state so an already-running online session cannot mask dependencies.
- Repeat the same learner-facing acceptance checks across the complete converted curriculum. Reconcile lesson order and coverage with the recovered inventory, including all narration and visible text.
- Recovery/conversion tools and content packaging support the primary boundary. Add targeted content-integrity checks for missing media or broken lesson references where failures could silently omit material; these supplement the end-to-end boundary rather than require a separate unit-test framework for every module.
- There is no prior test infrastructure in this repo. Select an automation harness after the delivery platform is chosen. Automated checks on one host do not establish Windows and macOS compatibility; report any unavailable platform validation explicitly.
- First-milestone acceptance requires a complete representative Russian lesson, comparison against the original, and offline playback verified on both target platforms. Full-course acceptance additionally requires complete curriculum coverage and the same localization and preservation checks throughout.

## Out of Scope

- Inventing new lessons, exercises, quizzes, or sound demonstrations.
- Silent modernization or rewriting of the original curriculum. Flag outdated content for the user's decision.
- Interactive visualization controls; the original visualizations are noninteractive.
- Additional languages beyond Russian.
- Mobile-platform support as a release requirement.
- Accounts, billing, cloud synchronization, analytics, or other unrelated platform features.
- A dependency on internet access or an external speech service during course playback.
- Reproducing the original executable's internal implementation or requiring the original Windows runtime for learner use.

## Further Notes

- Static inspection identifies the source as a Macromedia Director 8 Windows projector. An embedded Director movie and 15 Flash assets with valid headers have been extracted into temporary investigation storage. Their successful extraction does not yet establish correct rendering or complete animation coverage.
- Metadata references many audio resources and bitmaps. The exact mapping to lessons, audio durations, script text, and timeline remains unverified. Temporary extracted artifacts need reproducible recovery before they become build inputs.
- Candidate tools: [ProjectorRays](https://github.com/ProjectorRays/ProjectorRays) for Director decompilation; [REA](https://github.com/morluto/rea) for further reverse engineering; [Ruffle](https://ruffle.rs/) for testing playback of recovered Flash assets. These are investigation options, not validated compatibility claims.
- The user approved the overall extraction-first approach, permits either reverse-engineering tool, and confirmed the learner-facing testing boundary. Publish this spec to GitHub Issues with the `ready-for-agent` label.
