#!/usr/bin/env python3
"""Rebuild only SC_Song13's fixed specimen with user-selected external Arial13.

Reads two SHA-locked local sources. No downloads, firmware execution, outline
rasterization, arbitrary text, or font/subset export. Chinese and Arial have
different sources; this is not an original system pairing or device screenshot.
"""
from pathlib import Path
import argparse
import hashlib
import struct
from PIL import Image

SOURCE_SHA256 = '648b674639a9a83d35ca65934561dd38ee8d623afec2ee4e632ae6f7d53e0d55'
ARIAL_SHA256 = '2477ea0d6bae65eba347eb8a9ef9785bf01b58279c903b10da12d1cbc673a5de'
ARIAL_UID = 0x100001f4
LINES = ['视野无限广，窗外有蓝天。', '視野無限廣，窗外有藍天。']
ASCII = '0123456789 AaBb GgMm !?:+-.'


def checked_bytes(path, expected, size):
    data = Path(path).read_bytes()
    if len(data) != size or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Source size or SHA256 mismatch')
    return data


def chinese(data):
    """Decode fixed sample characters from original 13ppem EBDT/EBLC only."""
    if len(data) != 4686044 or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('SC_Song source mismatch')
    u16 = lambda p: struct.unpack_from('>H', data, p)[0]
    u32 = lambda p: struct.unpack_from('>I', data, p)[0]
    tables = {}
    for i in range(u16(4)):
        tag, checksum, offset, length = struct.unpack_from('>4sIII', data, 12 + 16*i)
        assert offset + length <= len(data)
        raw = data[offset:offset+length]
        if tag == b'head':
            raw = raw[:8] + b'\0'*4 + raw[12:]
        raw += b'\0' * (-len(raw) % 4)
        assert sum(struct.unpack('>'+str(len(raw)//4)+'I', raw)) & 0xffffffff == checksum
        tables[tag] = offset
    cm = tables[b'cmap']
    cm_start = None
    for i in range(u16(cm+2)):
        platform, encoding, offset = struct.unpack_from('>HHI', data, cm+4+8*i)
        if (platform, encoding) == (3, 1):
            cm_start = cm + offset
    assert cm_start is not None and u16(cm_start) == 4
    nseg = u16(cm_start+6)//2
    ends = cm_start+14
    starts, deltas, offsets = ends+2*nseg+2, ends+4*nseg+2, ends+6*nseg+2
    wanted = {ord(c) for line in LINES for c in line}
    mapping = {}
    for i in range(nseg):
        start, end, delta, ro = u16(starts+2*i), u16(ends+2*i), u16(deltas+2*i), u16(offsets+2*i)
        for cp in wanted:
            if start <= cp <= end:
                gid = u16(offsets+2*i+ro+2*(cp-start)) if ro else cp
                if gid or not ro:
                    gid = (gid+delta) & 0xffff
                if gid:
                    mapping[cp] = gid
    assert set(mapping) == wanted
    e, edata = tables[b'EBLC'], tables[b'EBDT']
    assert u32(e) == u32(edata) == 0x20000
    glyphs = {}
    matched = 0
    for si in range(u32(e+4)):
        pos = e+8+si*48
        arr, _, nsub, _ = struct.unpack_from('>IIII', data, pos)
        _, _, px, py, depth, _ = struct.unpack_from('>HHBBBb', data, pos+40)
        if (px, py) != (13, 13):
            continue
        matched += 1
        assert depth == 1
        for sj in range(nsub):
            first, last, rel = struct.unpack_from('>HHI', data, e+arr+8*sj)
            sp = e+arr+rel
            fmt, imagefmt, offset = struct.unpack_from('>HHI', data, sp)
            size = u32(sp+8)
            metrics = struct.unpack_from('>BBbbBbbB', data, sp+12)
            assert fmt in (2, 5) and imagefmt == 5 and size == 22
            assert metrics[:5] == (13, 13, 0, 11, 13)
            gids = list(range(first, last+1)) if fmt == 2 else list(struct.unpack_from('>'+str(u32(sp+20))+'H', data, sp+24))
            assert len(set(gids)) == len(gids) and min(gids) == first and max(gids) == last
            index = {gid: i for i, gid in enumerate(gids)}
            for cp, gid in mapping.items():
                if gid in index:
                    assert cp not in glyphs
                    location = edata+offset+index[gid]*size
                    raw = data[location:location+size]
                    assert len(raw) == size
                    value = int.from_bytes(raw, 'big')
                    rows = [(value >> (7+(12-y)*13)) & 0x1fff for y in range(13)]
                    assert any(rows)
                    glyphs[cp] = (11, 13, 0, 13, 13, rows)
    assert matched == 1 and set(glyphs) == wanted
    return glyphs


def arial(data):
    """Decode fixed ASCII sample from existing Eon.gdr Arial's actual 13px layer."""
    if len(data) != 143493 or hashlib.sha256(data).hexdigest() != ARIAL_SHA256:
        raise ValueError('Arial source mismatch')
    p = struct.unpack_from('<I', data, 32)[0]
    count = struct.unpack_from('<I', data, p)[0]
    p += 4
    glyphs = {}
    chosen = 0
    wanted = set(map(ord, ASCII))
    for _ in range(count):
        head = struct.unpack_from('<I7BII', data, p)
        p += 19
        sections = [struct.unpack_from('<HHII', data, p+i*12) for i in range(head[-1])]
        p += 12*head[-1]
        if head[0] != ARIAL_UID:
            continue
        chosen += 1
        assert head[1:] == (0, 0, 1, 13, 11, 15, 15, 0, 2)
        for start, end, offset, bitmap in sections:
            n = struct.unpack_from('<I', data, offset)[0]
            assert n == end-start+1
            length = struct.unpack_from('<I', data, bitmap)[0]
            packed = data[bitmap+4:bitmap+4+length]
            assert len(packed) == length
            for cp in wanted:
                if not start <= cp <= end:
                    continue
                at, asc, height, left, advance, right, pad = struct.unpack_from('<H5bB', data, offset+4+(cp-start)*8)
                assert at != 65535 and cp not in glyphs
                width = advance-left-right
                assert width >= 0 and height >= 0 and pad == 0
                bit = at*8
                def take(n):
                    nonlocal bit
                    assert bit+n <= len(packed)*8
                    value = sum(((packed[(bit+k)//8] >> ((bit+k)%8)) & 1) << k for k in range(n))
                    bit += n
                    return value
                rows = []
                while len(rows) < height:
                    repeat = take(1) == 0
                    nr = take(4)
                    assert 0 < nr <= height-len(rows)
                    for _ in range(1 if repeat else nr):
                        row = 0
                        for _ in range(width):
                            row = (row << 1) | take(1)
                        rows.extend([row] * (nr if repeat else 1))
                assert cp == 32 or any(rows)
                glyphs[cp] = (asc, height, left, advance, width, rows)
    # Exact native family link: Arial table, UID, and x/y scaling 1x1.
    assert data[p:p+10] == b'\x09\0\0\0\x16Arial'
    family_flags, face_count = struct.unpack_from('<BI', data, p+10)
    assert family_flags == 1 and face_count == 24
    faces = [struct.unpack_from('<IBB', data, p+15+i*6) for i in range(face_count)]
    assert faces.count((ARIAL_UID, 1, 1)) == 1
    assert chosen == 1 and set(glyphs) == wanted
    return glyphs


def render(source, arial_source, output):
    han = chinese(checked_bytes(source, SOURCE_SHA256, 4686044))
    latin = arial(checked_bytes(arial_source, ARIAL_SHA256, 143493))
    lines = [(line, han) for line in LINES] + [(ASCII, latin)]
    width = max(sum(gs[ord(c)][3] for c in line) for line, gs in lines)
    # 13px row frames and 4px specimen gaps. Arial13 and SC_Song13 both have
    # ascent 11; per-glyph bearings/advances are kept. This is a layout choice,
    # not a claim about either device's display or original line spacing.
    image = Image.new('RGBA', (width, 47), (0, 0, 0, 0))
    for li, (line, glyphs) in enumerate(lines):
        x0, baseline = 0, li*17+11
        for ch in line:
            asc, height, left, advance, width, rows = glyphs[ord(ch)]
            for y, row in enumerate(rows):
                for x in range(width):
                    if row >> (width-1-x) & 1:
                        px, py = x0+left+x, baseline-asc+y
                        assert 0 <= px < image.width and li*17 <= py < li*17+13
                        image.putpixel((px, py), (0, 0, 0, 255))
            x0 += advance
    with Path(output).open('xb') as stream:
        image.save(stream, format='PNG')
    return image


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Exact local sunfon.ttf')
    parser.add_argument('--arial-source', required=True, help='Exact local Eon.gdr')
    parser.add_argument('--output', required=True, help='New fixed PNG path; never overwritten')
    args = parser.parse_args()
    render(args.source, args.arial_source, args.output)
