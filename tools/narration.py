"""Validation for saved narration utterances and their source-segment cues."""


class NarrationError(ValueError):
    """Lesson narration grouping is incomplete or inconsistent."""


def anchor_position(text, anchor):
    position = text.find(anchor)
    if position < 0 or text.find(anchor, position + 1) >= 0:
        raise NarrationError(f'Missing or ambiguous visual cue anchor: {anchor}')
    return position


def validate_utterances(lesson, segments):
    utterances = lesson.get('utterances')
    if not isinstance(utterances, list) or not utterances:
        raise NarrationError('Lesson has no saved narration utterances')
    segment_ids = {str(segment['id']) for segment in segments}
    covered = []
    seen_ids = set()
    for utterance in utterances:
        uid = str(utterance.get('id'))
        if uid in seen_ids:
            raise NarrationError(f'Duplicate narration utterance ID: {uid}')
        seen_ids.add(uid)
        ids = [str(item) for item in utterance.get('segment_ids', [])]
        if not ids or any(item not in segment_ids for item in ids):
            raise NarrationError(f'Utterance {uid} has unknown source segments')
        text = str(utterance.get('russian', ''))
        if not text.strip():
            raise NarrationError(f'Utterance {uid} has no Russian text')
        cues = utterance.get('visual_cues', [])
        if [str(cue.get('segment_id')) for cue in cues] != ids:
            raise NarrationError(f'Utterance {uid} cues do not match its source segments')
        if cues[0].get('anchor'):
            raise NarrationError(f'Utterance {uid} first visual cue must start at the beginning')
        if any(not cue.get('anchor') for cue in cues[1:]):
            raise NarrationError(f'Utterance {uid} needs an anchor for each later visual cue')
        positions = []
        for cue in cues[1:]:
            anchor = str(cue['anchor'])
            try:
                positions.append(anchor_position(text, anchor))
            except NarrationError as error:
                raise NarrationError(f'Utterance {uid} {error}') from error
        if any(left >= right for left, right in zip(positions, positions[1:])):
            raise NarrationError(f'Utterance {uid} visual cue anchors are out of order')
        covered.extend(ids)
    if covered != [str(segment['id']) for segment in segments]:
        raise NarrationError('Saved narration utterances must cover every source segment exactly once')
    return utterances
