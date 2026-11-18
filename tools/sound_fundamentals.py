"""Source-specific Sound Fundamentals assets and draft visual reconstruction.

BITD layout reference: ScummVM engines/director/images.cpp and
castmember/bitmap.cpp. This is deliberately limited to this source's RGBA cones.
"""
import base64
import math
import struct
import zlib

from composition import SOURCE_SHA256
from waveforms import drawing


END_FRAME = 944  # The adaptation cuts the final source segment starting here.


class Bits:
    def __init__(self, data, offset=0):
        self.data, self.position = data, offset * 8

    def read(self, count, signed=False):
        if self.position + count > len(self.data) * 8:
            raise ValueError('Truncated ear Flash shape')
        value = 0
        for _ in range(count):
            value = value * 2 + ((self.data[self.position // 8] >> (7 - self.position % 8)) & 1)
            self.position += 1
        return value - (1 << count) if signed and count and value & (1 << (count - 1)) else value

    def rect(self):
        count = self.read(5)
        rect = [self.read(count, True) for _ in range(4)]
        self.position = (self.position + 7) // 8 * 8
        return rect


def ear_svg(data):
    """Convert the known monochrome DefineShape outline, without Flash runtime."""
    if len(data) < 12 or data[:4] != b'FWS\x04' or struct.unpack_from('<I', data, 4)[0] != len(data):
        raise ValueError('Unexpected ear Flash header')
    bits = Bits(data, 8)
    bounds = bits.rect()
    offset = bits.position // 8 + 4
    paths = []
    while offset < len(data):
        if offset + 2 > len(data):
            raise ValueError('Truncated ear Flash tag header')
        header, = struct.unpack_from('<H', data, offset)
        offset += 2
        tag, size = header >> 6, header & 63
        if size == 63:
            if offset + 4 > len(data):
                raise ValueError('Truncated ear Flash tag length')
            size, = struct.unpack_from('<I', data, offset)
            offset += 4
        body = data[offset:offset + size]
        if len(body) != size:
            raise ValueError('Truncated ear Flash tag')
        offset += size
        if tag != 2:
            continue
        shape = Bits(body, 2)
        shape.rect()
        start = shape.position // 8
        if body[start:start + 6] != b'\x01\x00\x00\x00\x00\x00':
            raise ValueError('Unexpected ear fill or line styles')
        shape.position += 48
        fill_bits, line_bits = shape.read(4), shape.read(4)
        path = []
        while True:
            if not shape.read(1):
                flags = shape.read(5)
                if not flags:
                    break
                if flags & 16:
                    raise ValueError('Unsupported additional ear styles')
                if flags & 1:
                    count = shape.read(5)
                    path.append(f'M{shape.read(count, True)} {shape.read(count, True)}')
                for flag, count in ((2, fill_bits), (4, fill_bits), (8, line_bits)):
                    if flags & flag:
                        shape.read(count)
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
        paths.append(' '.join(path))
    if len(paths) != 1:
        raise ValueError('Expected one ear outline')
    left, right, top, bottom = bounds
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left} {top} {right-left} {bottom-top}">'
            f'<path fill="#111" fill-rule="evenodd" d="{paths[0]}"/></svg>\n').encode()


def cone_bitmap(cast, encoded):
    """Return width, height and RGBA pixels from a known 32-bit Director BITD."""
    if len(cast) < 12:
        raise ValueError('Truncated speaker bitmap metadata')
    info_size, data_size = struct.unpack_from('>II', cast, 4)
    header = cast[12 + info_size:]
    if len(header) != data_size or len(header) != 28 or header[23] != 32:
        raise ValueError('Unexpected speaker bitmap metadata')
    pitch, top, left, bottom, right = struct.unpack_from('>Hhhhh', header)
    width, height = right - left, bottom - top
    if not 0 < width <= 64 or not 0 < height <= 256 or pitch & 0xfff != width * 4:
        raise ValueError('Unexpected speaker bitmap dimensions')
    size = width * height * 4
    raw = len(encoded) == size
    pixels = bytearray(encoded if raw else b'')
    offset = 0
    while not raw and offset < len(encoded):
        code = encoded[offset]
        offset += 1
        count = 257 - code if code & 128 else code + 1
        if code & 128:
            if offset >= len(encoded):
                raise ValueError('Truncated speaker bitmap repeat')
            pixels.extend(encoded[offset:offset + 1] * count)
            offset += 1
        else:
            if offset + count > len(encoded):
                raise ValueError('Truncated speaker bitmap literal')
            pixels.extend(encoded[offset:offset + count])
            offset += count
        if len(pixels) > size:
            raise ValueError('Speaker bitmap exceeds declared size')
    if len(pixels) != size:
        raise ValueError('Speaker bitmap has wrong decoded size')
    rgba = bytearray()
    for y in range(height):
        row = y * width * 4
        for x in range(width):
            indexes = [row + x * 4 + channel for channel in (1, 2, 3, 0)] if raw else [
                row + channel * width + x for channel in (1, 2, 3, 0)]
            rgba.extend(pixels[i] for i in indexes)
    return width, height, bytes(rgba)


def bitmap_svg(width, height, rgba):
    def chunk(tag, body):
        return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body))
    rows = b''.join(b'\0' + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
            f'<image width="{width}" height="{height}" href="data:image/png;base64,'
            + base64.b64encode(png).decode() + '"/></svg>\n').encode()


def compile_visuals(composition, segments, labels, cone_sizes):
    if composition['source_sha256'] != SOURCE_SHA256:
        raise ValueError('Sound Fundamentals requires the known source executable')
    members = {m['member_number']: m for m in composition['members'] if m['library_id'] == 8}
    states = [s for s in composition['score']['sprites'] if s['library_id'] == 8
              and s['start_frame'] < END_FRAME and s['end_frame'] >= 130]
    states.sort(key=lambda s: s['channel'])
    result = []
    for index, segment in enumerate(segments):
        start = segment['source_start_frame']
        end = segments[index + 1]['source_start_frame'] if index + 1 < len(segments) else END_FRAME
        frames = []
        for frame in range(start, end):
            active = [s for s in states if s['start_frame'] <= frame <= s['end_frame']]
            shows_wave = any(s['member_number'] == 5 for s in active)
            items = []
            for state in active:
                number = state['member_number']
                if 18 <= number <= 26:
                    width, height = cone_sizes[number]
                    items.append(dict(kind='image', asset=f'cone-{number}', x=state['x'] - width / 2,
                                      y=state['y'] - height / 2, width=width, height=height, opacity=1))
                elif number == 3:
                    items.append(dict(kind='image', asset='ear', x=state['x'] - state['width'] / 2,
                                      y=state['y'] - state['height'] / 2, width=state['width'],
                                      height=state['height'], opacity=1))
                elif number == 4:
                    items.append(dict(kind='pressure-arrow', x=state['x'], y=state['y'],
                                      width=state['width'], height=state['height'], opacity=1))
                elif state['width'] > 0 and state['height'] > 0:
                    item = drawing(members[number], state, labels)
                    if number == 1 and not shows_wave:
                        # shortcut: reconstructed runtime motion; calibrate against continuous original playback before approval.
                        phase = (frame - 315) * math.tau / 32 - (state['x'] - 80) / 45
                        item['x'] += 12 * math.sin(phase)
                    items.append(item)
            if shows_wave:
                wave = next(item for item in items if item.get('asset') == 'sine')
                balls = sorted((item for item in items if item.get('asset') == 'ball'),
                               key=lambda item: item['x'])
                # The sine asset starts at a crest and spans two cycles.
                crest = wave['x'] + wave['width'] * 7 / 400
                wavelength = wave['width'] * 196.5 / 400
                for index, ball in enumerate(balls):
                    phase = 2 * math.tau * (index + 0.5) / len(balls)
                    # Compress horizontal spacing at crests while keeping the same molecules.
                    x = crest + wavelength * (phase - 0.7 * math.sin(phase)) / math.tau
                    y = wave['y'] + wave['height'] * 0.7 + (ball['y'] - 180) * 0.45
                    ball.update(x=round(x - 5, 2), y=round(y - 5, 2), width=10, height=10)
            frames.append(dict(at=(frame - start) / (end - start), items=items))
        result.append(frames)
    return result
