"""Convert Bit Depth score events using the existing waveform and sample square."""
from composition import SOURCE_SHA256
from digital_audio import drawing as digital_drawing


STATE_X = 143
BIT_X = (224.5, 288.5, 348.5, 412.5)
TABLE_Y = 128
ROW_STEP = 22
# shortcut: calibrated to «четвёртый» in the bundled narration, retime if the recording changes.
FOURTH_BIT_FRAME = 5240


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
    font_size: float = 19 if label == 'singleBit' else 16
    x = state['x'] + state['width'] / 2
    y = state['y'] + font_size
    if label.startswith('states'):
        x, y, font_size = STATE_X, TABLE_Y, ROW_STEP / 1.15
    elif label in ('bit1', 'bit2', 'bit3'):
        x, y, font_size = BIT_X[int(label[-1]) - 1], TABLE_Y, ROW_STEP / 1.15
    elif label in ('zero', 'one'):
        y = TABLE_Y + round((y - TABLE_Y) / ROW_STEP) * ROW_STEP
        font_size = ROW_STEP / 1.15
    return dict(kind='text', opacity=opacity, x=x, y=y, lines=labels[label], font_size=font_size)


def four_bit_table(labels):
    headers = [labels['states8'][0], *(labels[f'bit{bit}'][0] for bit in range(1, 4)), 'Бит 4']
    rows = [[str(state + 1)] + [labels['one' if state & (1 << bit) else 'zero'][0]
                              for bit in range(4)] for state in range(16)]
    return [dict(kind='text', opacity=1, x=x, y=90, lines=list(column), font_size=14 / 1.15)
            for x, column in zip((STATE_X, *BIT_X), zip(headers, *rows))]


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
        if start < FOURTH_BIT_FRAME < end:
            changes.add(FOURTH_BIT_FRAME)
        for state in states:
            changes.update(f for f in (state['start_frame'], state['end_frame']+1) if start < f < end)
        frames = []
        for frame in sorted(changes):
            active = sorted((s for s in states if s['start_frame'] <= frame <= s['end_frame']
                             and s['width'] > 0 and s['height'] > 0), key=lambda s: s['channel'])
            if FOURTH_BIT_FRAME <= frame <= 5340:
                items = four_bit_table(labels)
            else:
                items = [drawing(members[s['library_id'], s['member_number']], s, labels, frame) for s in active]
            frames.append(dict(at=(frame-start)/(end-start), items=items))
        visuals.append(frames)
    return visuals
