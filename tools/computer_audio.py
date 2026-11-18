"""Convert the Computer Audio and MIDI score, including the closing card."""
from digital_audio import compile_score, drawing as digital_drawing
from digital_summary import drawing as summary_drawing

COMPUTER_AUDIO_RANGE = (6377, 8022)
MIDI_RANGE = (8022, 9295)

COMPUTER_BITMAPS = {
    'record-arrow': (1376, 3086),
    'header-bracket': (1020, 3032),
    'data-bracket': (868, 3038),
}


def text(x, y, lines, size, opacity, anchor='middle'):
    item = dict(kind='text', x=x, y=y, lines=lines, font_size=size, opacity=opacity)
    if anchor != 'middle':
        item['anchor'] = anchor
    return item


def computer_drawing(member, state, labels, frame):
    library, number = member['library_id'], member['member_number']
    key = library, number
    if library < 10 or number == 29:
        if key == (8, 56):
            mask = source_image(state, 'stage-mask')
            # Keep the waveform mask inside the speaker's horizontal bounds.
            return dict(mask, x=mask['x'] + 14.5, width=80)
        item = summary_drawing(member, state, labels, frame)
        if key == (8, 37) and frame >= 6902:
            # Leave room for the jack labels as the scenes pan.
            item['x'] += 88 if frame < 7277 else 98
        if key == (8, 43):
            item['y'] -= 10
        return item
    opacity = source_opacity(state)
    x, y, width, height = (state[k] for k in ('x', 'y', 'width', 'height'))
    bitmap = {4: 'header-bracket', 7: 'data-bracket', 31: 'record-arrow'}.get(number)
    if bitmap:
        return source_image(state, bitmap)
    if number == 5:
        # Keep the original sample values and their column structure.
        rows = [' '.join(value.rjust(6).replace(' ', ' ') for value in line.split())
                for line in member['text']['value'].splitlines()]
        return dict(text(306, 180, rows, 13, opacity), monospace=True)
    if number == 39:
        samples = member['text']['value'].splitlines()[3:]
        return text(x + 30, y + 15, labels[str(number)] + samples, 13, opacity)
    if number in (8, 9):
        x, anchor = (254, 'end') if number == 8 else (266, 'start')
        return text(x, y + 17, labels[str(number)], 18, opacity, anchor)
    if 10 <= number <= 16:
        return text(260, y + 17, labels[str(number)], 18, opacity)
    if number == 38:
        return text(x + width/2, y + 14 - (27 if frame >= 7277 else 0),
                    labels[str(number)], 14, opacity)
    if number == 37:
        return text(x + width/2 + 28, y - 10, labels[str(number)], 15, opacity)
    if number == 41:
        return text(x + width/2, y - 22, labels[str(number)], 15, opacity)
    if number in (3, 34, 35, 36, 40):
        dx, dy, size = {3: (6, 10, 14), 34: (20, 13, 12), 35: (18, 9, 12),
                        36: (24, 9, 16), 40: (19, 16, 12)}[number]
        return text(x + dx, y + dy, labels[str(number)], size, opacity, 'start')
    size = {1: 23, 32: 13, 33: 16}.get(number, 16)
    center = {2: 49, 6: 48, 32: 95, 33: 271}.get(number, x + width/2)
    return text(center, y + size, labels[str(number)], size, opacity if center < 550 else 0)


def midi_drawing(member, state, labels, frame):
    library, number = member['library_id'], member['member_number']
    if library == 10:
        # The final size calculation carries over from Computer Audio.
        return computer_drawing(member, state, labels['computerAudio'], frame)
    if library == 8 or number == 6:
        return digital_drawing(member, state, labels, frame)
    asset = {
        7: 'quarter-note', 8: 'treble-clef', 12: 'stage-mask', 18: 'sound-card',
        32: 'cool-edit-2000', 33: 'cool-edit-pro',
    }.get(number)
    if asset:
        return source_image(state, asset)
    x, y, width = (state[k] for k in ('x', 'y', 'width'))
    size = {1: 22, 11: 18, 20: 16, 21: 30, 22: 16, 23: 23, 26: 27, 28: 22}.get(number, 18)
    center = {
        4: 114, 5: 114, 9: 114, 10: 114, 11: x + 17,
        13: 128, 14: 308, 15: 321, 16: 319, 17: 322,
        20: 84, 21: x + 28, 22: 433,
    }.get(number, x + width/2)
    return text(center, y + size, labels[str(number)], size, source_opacity(state))


def source_opacity(state):
    raw = bytes.fromhex(state['record_hex'])
    if raw[28:36] != bytes(8):
        raise ValueError('Unconverted source rotation/skew in Computer Audio or MIDI')
    return 1 - raw[21] / 255 if raw[22] & 0x10 else 1


def source_image(state, asset):
    x, y, width, height = (state[k] for k in ('x', 'y', 'width', 'height'))
    return dict(kind='image', asset=asset, x=x-width/2, y=y-height/2,
                width=width, height=height, opacity=source_opacity(state))


def compile_computer_visuals(composition, segments, labels):
    return compile_score(composition, segments, labels, *COMPUTER_AUDIO_RANGE,
                         (8, 9, 10), computer_drawing, 'Computer Audio')


def compile_midi_visuals(composition, segments, labels):
    return compile_score(composition, segments, labels, *MIDI_RANGE,
                         (8, 9, 10), midi_drawing, 'MIDI')
