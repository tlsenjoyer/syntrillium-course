"""Convert Sampling Rate score events, including the reconstructed wave."""
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
    states = [s for s in composition['score']['sprites'] if s['library_id'] in (8, 9, 11)
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
            items = [drawing(members[s['library_id'], s['member_number']], s, labels, frame)
                     for s in active if s['library_id'] != 11]
            if any(s['library_id'] == 11 for s in active):
                # Use the source red-line layer's timing and join the visible sample centers.
                samples = [i for i in items if i.get('asset') == 'sample']
                centers = sorted((i['x'] + i['width'] / 2, i['y'] + i['height'] / 2) for i in samples)
                first_sample = items.index(samples[0])
                items[first_sample:first_sample] = [
                    dict(kind='line', opacity=1, x1=x1, y1=y1, x2=x2, y2=y2,
                         color='#ff0000', stroke_width=1)
                    for (x1, y1), (x2, y2) in zip(centers, centers[1:])]
            frames.append(dict(at=(frame-start)/(end-start), items=items))
        visuals.append(frames)
    return visuals
