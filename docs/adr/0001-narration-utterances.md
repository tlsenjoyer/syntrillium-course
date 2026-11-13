# Separate narration utterances from source segments

The original course's narration boundaries can divide a Russian sentence into
fragments. Generating each fragment independently produces unnatural sentence
endings and restarts. Generate complete sentences or short coherent passages as
narration utterances and play each utterance as one uninterrupted recording.

Retain source segments for provenance and visual material, allowing multiple
source segments to belong to one utterance. Time visual cues to the relevant
spoken words and check synchronization during narration review. Previous and
next navigation move between utterances; timeline seeking remains available
within them.

Lesson content explicitly records each utterance's complete Russian text and
the source segments it covers. Group suggestions may be automated, but the
reviewed groups are saved rather than inferred anew during generation.

This requires changing the generation and playback models, but avoids preserving
mid-sentence audio transitions by cutting a complete generated sentence back into
source-sized recordings. Concatenating independently generated fragments would
also preserve their unnatural intonation.
