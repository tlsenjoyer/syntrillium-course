"""Convert the recap of recording, digitization, and playback."""
from digital_audio import compile_score, drawing as digital_drawing


def drawing(member, state, labels, frame):
    key = member['library_id'], member['member_number']
    if key not in ((9, 18), (9, 31), (10, 29)):
        item = digital_drawing(member, state, labels, frame)
        if key == (8, 42) and frame >= 6310:
            item['y'] -= 18
        return item
    raw = bytes.fromhex(state['record_hex'])
    if raw[28:36] != bytes(8):
        raise ValueError('Unconverted source rotation/skew in Digital Summary')
    opacity = 1 - raw[21] / 255 if raw[22] & 0x10 else 1
    x, y, width, height = (state[k] for k in ('x', 'y', 'width', 'height'))
    if key == (9, 18):
        return dict(kind='image', opacity=opacity, asset='sound-card',
                    x=x-width/2, y=y-height/2, width=width, height=height)
    if key == (9, 31):
        return dict(kind='symbol', opacity=opacity, x=x, y=y+8, value='←', font_size=30)
    return dict(kind='text', opacity=opacity, x=x+width/2, y=y-13,
                lines=[labels['digitizedAudio']], font_size=14)


def compile_visuals(composition, segments, labels):
    return compile_score(composition, segments, labels, 5985, 6377, (8, 9, 10), drawing, 'Digital Summary')
