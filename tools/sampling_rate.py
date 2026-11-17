"""Convert Sampling Rate score events using the existing waveform and sample square."""
from composition import SOURCE_SHA256
from digital_audio import drawing as digital_drawing


def drawing(member, state, labels, frame):
    key = member['library_id'], member['member_number']
    label = {(8, 50): 'samplingRate', (8, 51): 'cdQuality', (8, 52): 'audio8k',
             (8, 53): 'twiceFrequency', (8, 54): 'nyquistTheorem',
             (8, 55): 'nyquistFrequency'}.get(key)
    if label is None:
        return digital_drawing(member, state, labels, frame)
    raw = bytes.fromhex(state['record_hex'])
    if raw[28:36] != bytes(8):
        raise ValueError('Unconverted source rotation/skew in Sampling Rate')
    opacity = 1 - raw[21] / 255 if raw[22] & 0x10 else 1
    return dict(kind='text', opacity=opacity, x=state['x']+state['width']/2,
                y=state['y']+16, lines=labels[label], font_size=16)


def compile_visuals(composition, segments, labels):
    if composition['source_sha256'] != SOURCE_SHA256:
        raise ValueError('Sampling Rate requires the known source executable')
    members = {(m['library_id'], m['member_number']): m for m in composition['members']}
    states = [s for s in composition['score']['sprites'] if s['library_id'] in (8, 9)
              and s['start_frame'] < 4684 and s['end_frame'] >= 3697]
    visuals = []
    for index, segment in enumerate(segments):
        start = segment['source_start_frame']
        end = segments[index+1]['source_start_frame'] if index+1 < len(segments) else 4684
        changes = {start}
        for state in states:
            changes.update(f for f in (state['start_frame'], state['end_frame']+1) if start < f < end)
        frames = []
        for frame in sorted(changes):
            active = sorted((s for s in states if s['start_frame'] <= frame <= s['end_frame']
                             and s['width'] > 0 and s['height'] > 0), key=lambda s: s['channel'])
            frames.append(dict(at=(frame-start)/(end-start), items=[
                drawing(members[s['library_id'], s['member_number']], s, labels, frame) for s in active]))
        visuals.append(frames)
    return visuals
