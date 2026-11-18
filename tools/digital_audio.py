"""Convert the Digital Audio score, reusing the original waveform and speaker."""
from composition import SOURCE_SHA256
from analog_audio import drawing as analog_drawing
from waveforms import drawing as waveform_drawing


def drawing(member, state, labels, frame):
    key = member['library_id'], member['member_number']
    if key in ((8, 6), (8, 9), (8, 37)):
        return waveform_drawing(member, state, labels)
    if key not in ((8, 45), (8, 47), (8, 48), (8, 49)):
        return analog_drawing(member, state, labels)
    raw = bytes.fromhex(state['record_hex'])
    if raw[28:36] != bytes(8):
        raise ValueError('Unconverted source rotation/skew in Digital Audio')
    opacity = 1 - raw[21] / 255 if raw[22] & 0x10 else 1
    x, y, width, height = (state[k] for k in ('x', 'y', 'width', 'height'))
    if key == (8, 47):
        return dict(kind='image', opacity=opacity, asset='sample', x=x, y=y,
                    width=width, height=height)
    if key == (8, 45):
        # shortcut: reconstruct the source's three-frame white-circle pulse; verify against Windows playback.
        scale = (2/3, 1, 2/3)[(frame-3513) % 3]
        return dict(kind='ellipse', opacity=opacity, cx=x, cy=y,
                    rx=width/2*scale, ry=height/2*scale, color='#ffffff')
    label = 'sampling' if key == (8, 48) else 'conversion'
    return dict(kind='text', opacity=opacity, x=x+width/2, y=y+19,
                lines=[labels[label]], font_size=19)


def compile_visuals(composition, segments, labels):
    # The player's stage edge clips the scrolling waveform.
    return compile_score(composition, segments, labels, 3389, 3697, (8, 9), drawing, 'Digital Audio',
                         excluded_members=((8, 39),))


def compile_score(composition, segments, labels, entry, boundary, libraries, draw, topic, *,
                  excluded_members=()):
    if composition['source_sha256'] != SOURCE_SHA256:
        raise ValueError(f'{topic} requires the known source executable')
    members = {(m['library_id'], m['member_number']): m for m in composition['members']}
    states = [s for s in composition['score']['sprites'] if s['library_id'] in libraries
              and (s['library_id'], s['member_number']) not in excluded_members
              and s['start_frame'] < boundary and s['end_frame'] >= entry]
    visuals = []
    for index, segment in enumerate(segments):
        start = segment['source_start_frame']
        end = segments[index+1]['source_start_frame'] if index+1 < len(segments) else boundary
        changes = {start}
        for state in states:
            changes.update(f for f in (state['start_frame'], state['end_frame']+1) if start < f < end)
        frames = []
        for frame in sorted(changes):
            active = sorted((s for s in states if s['start_frame'] <= frame <= s['end_frame']
                             and s['width'] > 0 and s['height'] > 0), key=lambda s: s['channel'])
            frames.append(dict(at=(frame-start)/(end-start), items=[
                draw(members[s['library_id'], s['member_number']], s, labels, frame) for s in active]))
        visuals.append(frames)
    return visuals
