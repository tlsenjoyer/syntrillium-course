# SPDX-License-Identifier: MPL-2.0
"""Static Director 8 composition recovery; no Lingo or media rendering.

Format research: ProjectorRays chunk.cpp (MCsL/CAS*) and ScummVM's
engines/director/{score,frame}.cpp (VWLB/VWSC). Offsets below were checked
against the source course's bytes and independent decompiler metadata.
"""
import re
import struct
from typing import Any


SOURCE_SHA256 = 'c385ac83b9cad64cc988d37b8e5b3c30586fcf63c478d56d473a5dcf5c360725'
# The topic menu and decompiled "go navVar ... in button" scripts agree.
# These are entry addresses, not verified lesson boundaries or timestamps.
TOPICS = [
    ('Sound Fundamentals', 130), ('Waveforms', 1003), ('Analog Audio', 2814),
    ('Digital Audio', 3389), ('Sampling Rate', 3697), ('Bit Depth', 4684),
    ('Digital Summary', 5985), ('Computer Audio', 6377), ('MIDI', 8022),
]


def unpack(fmt, data, offset=0):
    if offset < 0 or offset + struct.calcsize(fmt) > len(data):
        raise ValueError('Truncated Director composition data')
    return struct.unpack_from(fmt, data, offset)


def slice_bytes(data, start, end):
    if not 0 <= start <= end <= len(data):
        raise ValueError('Invalid Director composition offsets')
    return data[start:end]


def key_table(rows, chunks):
    """Read and validate shared KEY* resource ownership links."""
    keys: list[tuple[int, int, str]] = []
    for row in rows.values():
        if row['tag'] == 'KEY*':
            data = chunks[row['id']]
            size, size2, count, used = unpack('<HHII', data)
            if size != 12 or size2 != 12 or used > count or len(data) != 12 + count * size:
                raise ValueError('Malformed Director key table')
            for i in range(used):
                target, owner, tag = unpack('<II4s', data, 12 + i * size)
                keys.append((target, owner, tag[::-1].decode('ascii')))
    return keys


def library_members(rows, chunks, members):
    """Resolve the score's (library, member number) to actual CASt resources."""
    keys = key_table(rows, chunks)
    data = one_chunk('MCsL', rows, chunks)
    table, _, count, per_cast, _ = unpack('>IHHHH', data)
    if per_cast != 4:
        raise ValueError('Unsupported Director cast-library layout')
    size, = unpack('>H', data, table)
    if size != count * per_cast + 1:
        raise ValueError('Incomplete Director cast-library table')
    offsets = unpack(f'>{size + 1}I', data, table + 2)
    base = table + 2 + 4 * (size + 1)
    if base + offsets[-1] != len(data) or list(offsets) != sorted(offsets):
        raise ValueError('Invalid Director cast-library offsets')

    def item(index):
        return slice_bytes(data, base + offsets[index], base + offsets[index + 1])

    by_resource = {m['resource_id']: m for m in members}
    resolved = []
    libraries = []
    for i in range(count):
        name = item(i * 4 + 1)
        if not name or name[0] + 1 > len(name):
            raise ValueError('Invalid Director library name')
        minimum, maximum, owner = unpack('>HHI', item(i * 4 + 4))
        matches = [target for target, cast, tag in keys if cast == owner and tag == 'CAS*']
        if len(matches) != 1 or rows.get(matches[0], {}).get('tag') != 'CAS*':
            raise ValueError('Missing or ambiguous Director library membership')
        cast_id = matches[0]
        cast = chunks[cast_id]
        if len(cast) != 4 * (maximum - minimum + 1):
            raise ValueError('Director library member range mismatch')
        library_id = i + 1
        libraries.append(dict(library_id=library_id,
                              name=name[1:1 + name[0]].decode('mac_roman'),
                              resource_id=cast_id, min_member=minimum, max_member=maximum))
        for index in range(minimum, maximum + 1):
            rid, = unpack('>I', cast, (index - minimum) * 4)
            if not rid:
                continue
            if rid not in by_resource:
                raise ValueError(f'Library references missing cast resource {rid}')
            resolved.append(dict(by_resource[rid], library_id=library_id, member_number=index))
    assigned = {m['resource_id'] for m in resolved}
    if assigned != set(by_resource):
        raise ValueError('Some recovered cast members have no library membership')
    return libraries, resolved


def one_chunk(tag, rows, chunks):
    matches = [r['id'] for r in rows.values() if r['tag'] == tag]
    if len(matches) != 1:
        raise ValueError(f'Expected one Director {tag} resource')
    return chunks[matches[0]]


def labels(data):
    count, = unpack('>H', data)
    base = 2 + 4 * (count + 1)
    entries = [unpack('>HH', data, 2 + i * 4) for i in range(count + 1)]
    if base + entries[-1][1] != len(data):
        raise ValueError('Incomplete Director label text')
    result = []
    for index, (frame, offset) in enumerate(entries[:-1]):
        text = slice_bytes(data, base + offset, base + entries[index + 1][1])
        name, _, comment = text.decode('mac_roman').partition('\r')
        result.append(dict(frame=frame, name=name, comment=comment.replace('\r', '\n')))
    return result


def text_body(data):
    # XMED rich text has an ASCII section directory embedded in its serialized
    # stream. Section 0002 contains a length-prefixed byte string. Do not search
    # arbitrary XMED (e.g. Flash) or mistake member names for the visible text.
    if not data.startswith(b'FFFF0000000600040001'):
        return None
    match = re.search(rb'\x030002[0-9A-F]{8}00000000\x00([0-9A-F]+),', data)
    if not match:
        raise ValueError('Unsupported XMED rich-text body')
    end = match.end() + int(match[1], 16)
    value = slice_bytes(data, match.end(), end)
    if data[end:end + 1] != b'\x03':
        raise ValueError('XMED text length crosses section boundary')
    return dict(value=value.decode('cp1252').replace('\r', '\n'),
                encoding='cp1252', glyph_mapping_verified=False,
                offset=match.end(), byte_length=len(value))


def score(data):
    length, wrapper, table = unpack('>IiI', data)
    if length != len(data) or wrapper != -3:
        raise ValueError('Unsupported Director score wrapper')
    count, slots, _ = unpack('>III', data, table)
    if slots != count + 1 or count < 2:
        raise ValueError('Invalid Director score detail table')
    offsets = unpack(f'>{slots}I', data, table + 12)
    base = table + 12 + slots * 4
    if list(offsets) != sorted(offsets) or base + offsets[-1] != len(data):
        raise ValueError('Invalid Director score detail offsets')
    header = base + offsets[0]
    length, first, declared, version, record_size, channels, displayed = unpack('>IIIHHHH', data, header)
    if version != 13 or record_size != 48 or first != 20 or channels < 6:
        raise ValueError('Unsupported Director score channel layout')
    if header + length != base + offsets[1]:
        raise ValueError('Director score length crosses detail boundary')
    end = header + length
    pos = header + first
    state = bytearray(channels * record_size)
    previous: dict[tuple[str, int], tuple[bytes | None, dict[str, Any] | None]] = {}
    spans: dict[str, list[dict[str, Any]]] = dict(
        sprites=[], sounds=[], scripts=[], tempos=[], transitions=[], palettes=[])
    details = [dict(index=i, offset=base + offsets[i], size=offsets[i + 1] - offsets[i])
               for i in range(1, count) if offsets[i + 1] > offsets[i]]

    def update(kind, channel, record, frame, value):
        key = (kind, channel)
        old_record, event = previous.get(key, (None, None))
        if record == old_record:
            return
        if event is not None:
            event['end_frame'] = frame - 1
        event = None
        if value is not None:
            event = dict(start_frame=frame, end_frame=None, channel=channel, **value)
            spans[kind].append(event)
        previous[key] = (record, event)

    frame = 0
    while pos < end:
        frame_size, = unpack('>H', data, pos)
        stop = pos + frame_size
        if frame_size < 2 or stop > end:
            raise ValueError('Invalid Director frame size')
        pos += 2
        changed: set[int] = set()
        while pos < stop:
            size, offset = unpack('>HH', data, pos)
            pos += 4
            if size == 0 or offset + size > len(state) or pos + size > stop:
                raise ValueError('Invalid Director channel delta')
            state[offset:offset + size] = data[pos:pos + size]
            changed.update(range(offset // 48, (offset + size - 1) // 48 + 1))
            pos += size
        if pos != stop:
            raise ValueError('Incomplete Director frame')
        frame += 1
        for channel in sorted(changed):
            record = bytes(state[channel * 48:(channel + 1) * 48])
            if channel == 1:
                update('tempos', 0, record, frame,
                       dict(raw_value=record[6], record_hex=record.hex()))
            elif channel in (2, 5):
                kind = 'transitions' if channel == 2 else 'palettes'
                update(kind, 0, record, frame, dict(record_hex=record.hex()))
            elif channel in (0, 3, 4):
                lib, number, detail = unpack('>HHI', record)
                kind = 'scripts' if channel == 0 else 'sounds'
                number_in_kind = 0 if channel == 0 else 5 - channel
                value = dict(library_id=lib, member_number=number,
                             detail_index=detail, record_hex=record.hex()) if number else None
                update(kind, number_in_kind, record, frame, value)
            elif channel >= 6:
                lib, number, detail, y, x, height, width = unpack('>HHIhhhh', record, 4)
                value = None
                if record[0]:
                    value = dict(library_id=lib, member_number=number, detail_index=detail,
                                 x=x, y=y, width=width, height=height,
                                 sprite_type=record[0], record_hex=record.hex())
                update('sprites', channel - 5, record, frame, value)
    if frame != declared:
        raise ValueError('Director score frame count mismatch')
    for _, event in previous.values():
        if event is not None:
            event['end_frame'] = frame
    return dict(frame_count=frame, channel_count=channels, displayed_channels=displayed,
                details=details, **spans)


def recover_composition(rows, chunks, members, source_sha256):
    libraries, members = library_members(rows, chunks, members)
    for member in members:
        for media in member['media']:
            if media['tag'] == 'XMED' and media['present']:
                text = text_body(chunks[media['resource_id']])
                if text is not None:
                    member['text'] = dict(text, resource_id=media['resource_id'])
    timeline = score(one_chunk('VWSC', rows, chunks))
    known = {(m['library_id'], m['member_number']) for m in members}
    unresolved = sorted({(s['library_id'], s['member_number'])
                         for kind in ('sprites', 'sounds', 'scripts') for s in timeline[kind]
                         if (s['library_id'], s['member_number']) not in known})
    configuration = one_chunk('DRCF', rows, chunks)
    top, left, bottom, right = unpack('>hhhh', configuration, 4)
    frame_rate, = unpack('>B', configuration, 55)
    return dict(
        source_sha256=source_sha256, libraries=libraries, members=members,
        nominal_frame_rate=frame_rate, stage=dict(width=right - left, height=bottom - top),
        labels=labels(one_chunk('VWLB', rows, chunks)),
        topics=[dict(title=title, entry_frame=frame) for title, frame in TOPICS]
        if source_sha256 == SOURCE_SHA256 else [],
        score=timeline, unresolved_cast_references=[dict(library_id=lib, member_number=num)
                                                  for lib, num in unresolved],
        limitations=[
            'Static score spans are inclusive frame addresses, not playback seconds.',
            'Lingo can hold or jump frames and change sprite properties at runtime.',
            'Sprite coordinates are registration points, not necessarily top-left corners.',
            'Score detail offsets refer to the original VWSC resource, retained in resources/.',
            'Rich text is recovered without its formatting; bitmap/Flash text is not decoded.',
            'Non-ASCII text uses provisional CP1252 decoding; original font glyph mapping is unverified.',
            'Sound references are not classified as narration solely by being in the score.',
            'Topic entries are source-specific; lesson ends and rendered fidelity remain unverified.',
        ])
