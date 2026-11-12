"""Compile original Waveforms score states into ordinary SVG drawing commands.

This source-specific conversion profile never runs in the learner's browser.
The source's registration conventions were checked against Windows captures:
Flash/bitmaps use center registration; rich text and primitive shapes use top-left.
"""
from typing import Any

from composition import SOURCE_SHA256


def drawing(member, state, labels):
    number = member['member_number']
    x, y, width, height = (state[k] for k in ('x', 'y', 'width', 'height'))
    raw = bytes.fromhex(state['record_hex'])
    opacity = 1 - raw[21] / 255 if raw[22] & 0x10 else 1
    base = dict(opacity=opacity)
    if raw[28:36] != bytes(8):
        raise ValueError('Unconverted source rotation/skew in Waveforms')
    asset = {'sin': 'sine', 'backball': 'ball', 'complexwave1': 'complex-1',
             'complexwave2': 'complex-2'}.get(member['name'])
    if asset:
        return dict(base, kind='image', asset=asset, x=x - width / 2, y=y - height / 2,
                    width=width, height=height)
    texts = {
        7: [labels['zero'], 'Давление', 'не изменяется'],
        8: [labels['peak'], labels['high']],
        10: [labels['trough'], labels['low']],
        11: [labels['amplitude']], 12: [labels['peak']], 14: [labels['trough']],
        15: [labels['cycle']], 16: [labels['frequency']], 17: [labels['hertz']],
        28: ['0°'], 29: ['180°'], 30: ['360°'], 31: [labels['wavelength']],
        34: [labels['inPhase']], 36: [labels['outOfPhase']],
    }
    if number in texts:
        # Keep source placement and event order, expanding short English labels
        # into readable Russian lines. The stage has extra right-hand room.
        font_size = 22 if number in (34, 36) else 12
        return dict(base, kind='text', x=x + width / 2 if number != 7 else 483,
                    y=y + font_size, lines=texts[number], font_size=font_size)
    color = f'#{raw[2]:02x}{raw[24]:02x}{raw[26]:02x}' if raw[20] & 0x10 else '#111111'
    if number in (6, 9):
        return dict(base, kind='line', x1=x, y1=y, x2=x + (width if number == 6 else 0),
                    y2=y + (height if number == 9 else 0), color=color,
                    stroke_width=max(1, height if number == 6 else width))
    if number == 13:
        return dict(base, kind='ellipse', cx=x + width / 2, cy=y + height / 2,
                    rx=width / 2, ry=height / 2, color=color)
    if number == 27:
        return dict(base, kind='amplitude-bracket', x=x, y=y, width=width, height=height)
    if number == 32:
        return dict(base, kind='wavelength-bracket', x=x, y=y, width=width, height=height)
    if number in (33, 35):
        return dict(base, kind='symbol', x=x, y=y + height / 3,
                    value='+' if number == 33 else '=', font_size=height * 1.3)
    raise ValueError(f'Waveforms visual cast member {number} is not converted')


def compile_visuals(composition, segments, labels):
    if composition['source_sha256'] != SOURCE_SHA256:
        raise ValueError('Waveforms visual profile is only verified for the known source executable')
    members = {m['member_number']: m for m in composition['members'] if m['library_id'] == 8}
    states = [s for s in composition['score']['sprites'] if s['library_id'] == 8
              and s['start_frame'] < 2814 and s['end_frame'] >= 1003]
    result: list[list[dict[str, Any]]] = []
    for index, segment in enumerate(segments):
        start = segment['source_start_frame']
        end = segments[index + 1]['source_start_frame'] if index + 1 < len(segments) else 2814
        changes = {start}
        for state in states:
            changes.update(f for f in (state['start_frame'], state['end_frame'] + 1) if start < f < end)
        frames = []
        for frame in sorted(changes):
            active = sorted((s for s in states if s['start_frame'] <= frame <= s['end_frame']
                             and s['width'] > 0 and s['height'] > 0), key=lambda s: s['channel'])
            items = [drawing(members[s['member_number']], s, labels) for s in active]
            frames.append(dict(at=(frame - start) / (end - start), items=items))
        result.append(frames)
    return result
