#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Recover the source Director container and inventory its resources.

Afterburner format interpretation follows ProjectorRays' dirfile.cpp and
stream.cpp (MPL-2.0). This is a static recovery tool, not a Director renderer.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def take(self, size):
        if size < 0 or self.pos + size > len(self.data):
            raise ValueError('Resource extends past the container boundary')
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def varint(self):
        value = 0
        for _ in range(5):
            byte = self.take(1)[0]
            value = (value << 7) | (byte & 127)
            if value > 0xffffffff:
                raise ValueError('Integer exceeds 32 bits')
            if byte < 128:
                return value
        raise ValueError('Unterminated Director integer')

    def tag(self, expected):
        if self.take(4)[::-1] != expected:
            raise ValueError(f'Expected Director chunk {expected!r}')


def inflate(data, expected=None):
    # Bound the expansion even for damaged or substituted input.
    limit = 64 * 1024 * 1024 if expected is None else expected
    if limit > 64 * 1024 * 1024:
        raise ValueError('Resource exceeds the recovery size limit')
    decoder = zlib.decompressobj()
    result = decoder.decompress(data, limit + 1)
    if len(result) > limit or not decoder.eof or decoder.unused_data:
        raise ValueError('Invalid or oversized compressed resource')
    if expected is not None and len(result) != expected:
        raise ValueError('Decompressed resource length mismatch')
    return result


def read_container(source):
    candidates = []
    offset = 0
    while (offset := source.find(b'XFIR', offset)) >= 0:
        if source[offset + 8:offset + 12] == b'MDGF':
            candidates.append(offset)
        offset += 4
    if len(candidates) != 1:
        raise ValueError('Expected exactly one embedded Director Afterburner movie')
    offset = candidates[0]
    size = struct.unpack_from('<I', source, offset + 4)[0] + 8
    if offset + size > len(source):
        raise ValueError('Truncated embedded Director movie')
    movie = source[offset:offset + size]
    r = Reader(movie)
    r.take(12)
    r.tag(b'Fver')
    version = r.take(r.varint())
    r.tag(b'Fcdr')
    codecs = Reader(inflate(r.take(r.varint())))
    count = struct.unpack('<H', codecs.take(2))[0]
    identifiers = [codecs.take(16).hex() for _ in range(count)]
    descriptions = codecs.take(len(codecs.data) - codecs.pos).split(b'\0')
    if len(descriptions) != count + 1 or descriptions[-1]:
        raise ValueError('Malformed compression descriptions')
    compression = [dict(id=i, guid=g, description=d.decode('ascii'))
                   for i, (g, d) in enumerate(zip(identifiers, descriptions))]
    r.tag(b'ABMP')
    packed_map = Reader(r.take(r.varint()))
    map_codec = packed_map.varint()
    if map_codec >= count or identifiers[map_codec] != '04e999ac7000360b0000080007377a34':
        raise ValueError('Unsupported resource-map compression')
    map_size = packed_map.varint()
    resources = Reader(inflate(packed_map.take(len(packed_map.data) - packed_map.pos), map_size))
    resources.varint()
    resources.varint()
    resource_count = resources.varint()
    rows = {}
    for _ in range(resource_count):
        rid, position, packed, unpacked, codec = [resources.varint() for _ in range(5)]
        tag = resources.take(4)[::-1].decode('ascii')
        if rid in rows or codec >= count:
            raise ValueError('Duplicate resource ID or invalid compression index')
        rows[rid] = dict(id=rid, tag=tag, offset=position, compressed_size=packed,
                         uncompressed_size=unpacked, compression=codec)
    if resources.pos != len(resources.data) or 2 not in rows:
        raise ValueError('Incomplete Director resource map')
    r.tag(b'FGEI')
    r.varint()
    body_offset = r.pos
    initial = Reader(inflate(r.take(rows[2]['compressed_size']), rows[2]['uncompressed_size']))
    cached = {}
    while initial.pos < len(initial.data):
        rid = initial.varint()
        if rid not in rows or rid in cached:
            raise ValueError('Invalid initial-load resource reference')
        cached[rid] = initial.take(rows[rid]['compressed_size'])
    chunks = {}
    for rid, row in rows.items():
        if rid == 2:
            data, state = initial.data, 'decoded'
        elif rid in cached:
            data, state = cached[rid], 'initial-load'
        else:
            chunk = Reader(movie)
            chunk.pos = body_offset + row['offset']
            data = chunk.take(row['compressed_size'])
            guid = identifiers[row['compression']]
            if guid == '04e999ac7000360b0000080007377a34':
                if not data and row['uncompressed_size']:
                    raise ValueError('Empty resource declares missing decoded content')
                data = inflate(data, row['uncompressed_size']) if data else data
                state = 'decoded'
            else:
                # Preserve proprietary SWA data; do not label it decoded audio.
                state = 'encoded'
        row['state'] = state
        chunks[rid] = data
    return movie, offset, version, compression, rows, chunks



def member_inventory(rows, chunks):
    """Retain cast names and KEY* links; missing targets stay explicit."""
    media = {}
    for row in rows.values():
        if row['tag'] != 'KEY*':
            continue
        data = chunks[row['id']]
        size, size2, count, used = struct.unpack_from('<HHII', data)
        if size != 12 or size2 != 12 or used > count or len(data) != 12 + count * size:
            raise ValueError('Malformed Director key table')
        for index in range(used):
            target, owner, tag = struct.unpack_from('<II4s', data, 12 + index * size)
            media.setdefault(owner, []).append(dict(
                resource_id=target, tag=tag[::-1].decode('ascii'), present=target in rows))
    members = []
    for row in rows.values():
        if row['tag'] != 'CASt':
            continue
        data = chunks[row['id']]
        kind, info_size, specific_size = struct.unpack_from('>III', data)
        if len(data) != 12 + info_size + specific_size:
            raise ValueError('Cast member size mismatch')
        name = ''
        if info_size:
            info = Reader(data[12:12 + info_size])
            table = struct.unpack('>I', info.take(4))[0]
            info.pos = table
            count = struct.unpack('>H', info.take(2))[0]
            offsets = [struct.unpack('>I', info.take(4))[0] for _ in range(count)]
            length = struct.unpack('>I', info.take(4))[0]
            values = info.take(length)
            if offsets != sorted(offsets) or any(i > length for i in offsets):
                raise ValueError('Invalid cast information offsets')
            if count > 1:
                end = offsets[2] if count > 2 else length
                value = Reader(values[offsets[1]:end])
                if value.data:
                    name = value.take(value.take(1)[0]).decode('mac_roman')
        members.append(dict(resource_id=row['id'], type=kind, name=name,
                            media=media.get(row['id'], [])))
    return members


def digest(data):
    return hashlib.sha256(data).hexdigest()


def recover(source, destination):
    data = source.read_bytes()
    movie, offset, version, compression, rows, chunks = read_container(data)
    members = member_inventory(rows, chunks)
    # Parse everything before creating output. Existing output is never replaced.
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'resources').mkdir()
    (destination / 'flash').mkdir()
    (destination / 'movie.dcr').write_bytes(movie)
    flash = []
    for rid, row in rows.items():
        content = chunks[rid]
        path = f'resources/{rid:05d}.bin'
        (destination / path).write_bytes(content)
        row.update(path=path, stored_size=len(content), sha256=digest(content))
        if row['tag'] != 'XMED' or row['state'] == 'encoded':
            continue
        start = 0
        while (start := content.find(b'FWS', start)) >= 0:
            if start + 8 <= len(content):
                length = int.from_bytes(content[start + 4:start + 8], 'little')
                if 8 <= length <= len(content) - start and 1 <= content[start + 3] <= 50:
                    asset = content[start:start + length]
                    path = f'flash/{rid:05d}-{start}.swf'
                    (destination / path).write_bytes(asset)
                    flash.append(dict(resource_id=rid, offset=start, path=path,
                                      size=length, sha256=digest(asset), rendering_verified=False))
            start += 3
    inventory = dict(
        source=dict(name=source.name, size=len(data), sha256=digest(data)),
        movie=dict(path='movie.dcr', executable_offset=offset, size=len(movie),
                   sha256=digest(movie), version_bytes=version.hex()),
        compression=compression, counts=dict(sorted(Counter(r['tag'] for r in rows.values()).items())),
        resources=list(rows.values()), members=members, flash=flash,
        limitations=['Resource IDs are not lesson ordering.',
                     'Proprietary sound compression is preserved, not decoded.',
                     'Flash headers do not establish playback compatibility or animation coverage.',
                     'Text bodies, library membership, score timing and lesson composition require further recovery.'])
    (destination / 'inventory.json').write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
    return inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path, help='New output directory; must not already exist')
    args = parser.parse_args()
    try:
        inventory = recover(args.source, args.destination)
    except (OSError, ValueError, zlib.error, struct.error) as error:
        parser.exit(1, f'Recovery failed: {error}\n')
    print(f"Recovered {len(inventory['resources'])} resources and {len(inventory['flash'])} Flash candidates")


if __name__ == '__main__':
    main()
