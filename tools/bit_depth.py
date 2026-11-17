"""Convert Bit Depth score events using the existing waveform and sample square."""
from composition import SOURCE_SHA256
from digital_audio import drawing as digital_drawing


def drawing(member, state, labels, frame):
    key = member['library_id'], member['member_number']
    label = {(10, number): name for number, name in enumerate((
        'bitDepth', 'singleBit', 'bit1', 'zero', 'one', 'bit2', 'states2',
        'states4', 'states8', 'bit3', 'cdQuality', 'dvdQuality'), 17)}.get(key)
    if label is None:
        return digital_drawing(member, state, labels, frame)
    raw = bytes.fromhex(state['record_hex'])
    if raw[28:36] != bytes(8):
        raise ValueError('Unconverted source rotation/skew in Bit Depth')
    opacity = 1 - raw[21] / 255 if raw[22] & 0x10 else 1
    font_size: float = 19 if key[1] in (18, 19, 22, 26) else 16
    # Align state numbers with the source's 22-pixel binary-digit rows.
    table = key[1] in (23, 24, 25)
    if table:
        font_size = 22 / 1.15
    return dict(kind='text', opacity=opacity, x=state['x']+state['width']/2-(16 if table else 0),
                y=state['y']+(29 if table else font_size), lines=labels[label], font_size=font_size)


def compile_visuals(composition, segments, labels):
    if composition['source_sha256'] != SOURCE_SHA256:
        raise ValueError('Bit Depth requires the known source executable')
    members = {(m['library_id'], m['member_number']): m for m in composition['members']}
    states = [s for s in composition['score']['sprites'] if s['library_id'] in (8, 9, 10)
              and s['start_frame'] < 5985 and s['end_frame'] >= 4684]
    visuals = []
    for index, segment in enumerate(segments):
        start = segment['source_start_frame']
        end = segments[index+1]['source_start_frame'] if index+1 < len(segments) else 5985
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
