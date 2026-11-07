"""Rebuild only the approved fixed MS Ming 14px specimen from a local SHA-locked TTF.
No downloads, outline rasterization, arbitrary text or font/subset export.
"""
from pathlib import Path
import argparse
import hashlib
import struct
from PIL import Image

EXPECTED = '5e9d90f68aae316091bd1bec797c2bc4670a1186caaf601ecae2e7e5661ae353'
LINES = ['视野无限广，窗外有蓝天。', '視野無限廣，窗外有藍天。']


def render(source, output):
    data = Path(source).read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED:
        raise ValueError('Source SHA256 mismatch')
    u16 = lambda p: struct.unpack_from('>H', data, p)[0]
    u32 = lambda p: struct.unpack_from('>I', data, p)[0]
    tables = {}
    for i in range(u16(4)):
        tag, checksum, offset, size = struct.unpack_from('>4sIII', data, 12 + 16*i)
        assert offset + size <= len(data)
        raw = data[offset:offset+size]
        if tag == b'head':
            raw = raw[:8] + b'\0'*4 + raw[12:]
        raw += b'\0' * (-len(raw) % 4)
        assert sum(struct.unpack('>'+str(len(raw)//4)+'I', raw)) & 0xffffffff == checksum
        tables[tag] = offset
    cm = tables[b'cmap']
    cmap_start = None
    for i in range(u16(cm+2)):
        platform, encoding, offset = struct.unpack_from('>HHI', data, cm+4+8*i)
        if (platform, encoding) == (3, 1):
            cmap_start = cm + offset
    assert cmap_start is not None and u16(cmap_start) == 4
    nseg = u16(cmap_start+6)//2
    ends = cmap_start+14
    starts, deltas, offsets = ends+2*nseg+2, ends+4*nseg+2, ends+6*nseg+2
    mapping = {}
    wanted = {ord(c) for line in LINES for c in line}
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
    for si in range(u32(e+4)):
        pos = e+8+si*48
        arr, _, nsub, _ = struct.unpack_from('>IIII', data, pos)
        _, _, px, py, depth, _ = struct.unpack_from('>HHBBBb', data, pos+40)
        if (px, py) != (14, 14):
            continue
        assert depth == 1
        for sj in range(nsub):
            first, last, rel = struct.unpack_from('>HHI', data, e+arr+8*sj)
            sp = e+arr+rel
            fmt, imagefmt, offset = struct.unpack_from('>HHI', data, sp)
            size = u32(sp+8)
            metrics = struct.unpack_from('>BBbbBbbB', data, sp+12)
            assert fmt == 2 and imagefmt == 5 and size == 25
            assert metrics == (14,14,0,12,14,-7,0,14)
            for cp, gid in mapping.items():
                if first <= gid <= last:
                    location = edata+offset+(gid-first)*size
                    raw = data[location:location+size]
                    assert len(raw) == size
                    value = int.from_bytes(raw, 'big')
                    glyphs[cp] = [(value >> (4+(13-y)*14)) & 0x3fff for y in range(14)]
    assert set(glyphs) == wanted
    image = Image.new('1', (len(LINES[0])*14,32), 1)
    for li, line in enumerate(LINES):
        for ci, char in enumerate(line):
            for y, row in enumerate(glyphs[ord(char)]):
                for x in range(14):
                    if row >> (13-x) & 1:
                        image.putpixel((ci*14+x,li*18+y),0)
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    image.save(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    render(args.source, args.output)
