"""Convert the known Analog Audio score and its solid-fill Flash illustrations."""
import struct

from composition import SOURCE_SHA256
from sound_fundamentals import Bits
from waveforms import drawing as waveform_drawing


FLASH_ASSETS = {'mic': 2917, 'speaker': 2923, 'tape-recorder': 2965}


def solid_flash_svg(data):
    """Decode this source's DefineShape2 paths; reject other fill/line formats."""
    if len(data) < 12 or data[:4] != b'FWS\x04' or struct.unpack_from('<I', data, 4)[0] != len(data):
        raise ValueError('Unexpected Analog Audio Flash header')
    bits = Bits(data, 8)
    left, right, top, bottom = bits.rect()
    offset = bits.position // 8 + 4
    paths = []
    while offset < len(data):
        if offset + 2 > len(data):
            raise ValueError('Truncated Analog Audio Flash tag')
        header, = struct.unpack_from('<H', data, offset)
        offset += 2
        tag, size = header >> 6, header & 63
        if size == 63:
            if offset + 4 > len(data):
                raise ValueError('Truncated Analog Audio Flash tag length')
            size, = struct.unpack_from('<I', data, offset)
            offset += 4
        body = data[offset:offset + size]
        if len(body) != size:
            raise ValueError('Truncated Analog Audio Flash body')
        offset += size
        if tag != 22:
            if tag in (2, 32, 83):
                raise ValueError('Unsupported Analog Audio shape format')
            continue
        shape = Bits(body, 2)
        shape.rect()

        def styles():
            shape.position = (shape.position + 7) // 8 * 8
            if shape.read(8) != 1 or shape.read(8) != 0:
                raise ValueError('Expected one solid Analog Audio fill')
            color = '#%02x%02x%02x' % tuple(shape.read(8) for _ in range(3))
            if shape.read(8) != 0:
                raise ValueError('Unsupported Analog Audio line styles')
            fill_bits, line_bits = shape.read(4), shape.read(4)
            if fill_bits != 1 or line_bits:
                raise ValueError('Unexpected Analog Audio style indices')
            return color, fill_bits, line_bits

        color, fill_bits, line_bits = styles()
        path = []
        while True:
            if not shape.read(1):
                flags = shape.read(5)
                if not flags:
                    break
                if flags & 16:
                    paths.append((color, ' '.join(path)))
                    path = []
                if flags & 1:
                    count = shape.read(5)
                    path.append(f'M{shape.read(count, True)} {shape.read(count, True)}')
                for flag, count in ((2, fill_bits), (4, fill_bits), (8, line_bits)):
                    if flags & flag:
                        shape.read(count)
                if flags & 16:
                    color, fill_bits, line_bits = styles()
            else:
                straight, count = shape.read(1), shape.read(4) + 2
                if straight:
                    dx = dy = 0
                    if shape.read(1):
                        dx, dy = shape.read(count, True), shape.read(count, True)
                    elif shape.read(1):
                        dy = shape.read(count, True)
                    else:
                        dx = shape.read(count, True)
                    path.append(f'l{dx} {dy}')
                else:
                    cx, cy, ax, ay = [shape.read(count, True) for _ in range(4)]
                    path.append(f'q{cx} {cy} {cx + ax} {cy + ay}')
        paths.append((color, ' '.join(path)))
    if not paths or right <= left or bottom <= top:
        raise ValueError('Analog Audio Flash contains no usable shapes')
    svg = ''.join(f'<path fill="{color}" fill-rule="evenodd" d="{path}"/>' for color, path in paths)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left} {top} {right-left} {bottom-top}">'
            f'{svg}</svg>\n').encode()


def drawing(member, state, labels):
    key = member['library_id'], member['member_number']
    if key in ((8, 6), (8, 38)):
        return waveform_drawing(member, state, labels)
    raw = bytes.fromhex(state['record_hex'])
    if raw[28:36] != bytes(8):
        raise ValueError('Unconverted source rotation/skew in Analog Audio')
    opacity = 1 - raw[21] / 255 if raw[22] & 0x10 else 1
    x, y, width, height = (state[k] for k in ('x', 'y', 'width', 'height'))
    asset = {(8, 39): 'leftcover', (8, 40): 'mic', (8, 43): 'speaker',
             (9, 6): 'tape-recorder'}.get(key)
    if asset:
        return dict(kind='image', opacity=opacity, asset=asset, x=x-width/2, y=y-height/2,
                    width=width, height=height)
    label = {(8, 41): 'pressure', (8, 42): 'voltage', (8, 44): 'analogAudio'}.get(key)
    if label:
        # Embedded Flash labels register at their center, unlike Director rich text.
        return dict(kind='text', opacity=opacity, x=x, y=y+5, lines=[labels[label]],
                    font_size=20 if key == (8, 44) else 14)
    if key == (9, 30):
        return dict(kind='symbol', opacity=opacity, x=x, y=y+8, value='→', font_size=30)
    raise ValueError(f'Analog Audio visual cast member {key} is not converted')


def compile_visuals(composition, segments, labels):
    if composition['source_sha256'] != SOURCE_SHA256:
        raise ValueError('Analog Audio requires the known source executable')
    members = {(m['library_id'], m['member_number']): m for m in composition['members']}
    states = [s for s in composition['score']['sprites'] if s['library_id'] in (8, 9)
              and s['start_frame'] < 3389 and s['end_frame'] >= 2814]
    visuals = []
    for index, segment in enumerate(segments):
        start = segment['source_start_frame']
        end = segments[index+1]['source_start_frame'] if index+1 < len(segments) else 3389
        changes = {start}
        for state in states:
            changes.update(f for f in (state['start_frame'], state['end_frame']+1) if start < f < end)
        frames = []
        for frame in sorted(changes):
            active = sorted((s for s in states if s['start_frame'] <= frame <= s['end_frame']
                             and s['width'] > 0 and s['height'] > 0), key=lambda s: s['channel'])
            frames.append(dict(at=(frame-start)/(end-start), items=[
                drawing(members[s['library_id'], s['member_number']], s, labels) for s in active]))
        visuals.append(frames)
    return visuals
