"""Redraw only the approved fixed MR-100 specimen from a SHA-locked local FNT.
No download, firmware execution, arbitrary text, font export or glyph-data output.
"""
from pathlib import Path
import argparse
import hashlib
import struct
from PIL import Image

SOURCE_SHA256 = 'e81b038173cabc11680e8e3f11a528c5b668420853014a94e8b9ce95de248a4e'
LINES = ['视野无限广，窗外有蓝天。', '視野無限廣，窗外有藍天。', '0123456789 AaBb GgMm !?:+-.']


def render(source, output):
    data = Path(source).read_bytes()
    if len(data) != 1781424 or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('MR100.fnt SHA256 or size mismatch')
    tag, info, cmap, records = struct.unpack_from('<4I', data)
    count = struct.unpack_from('<I', data, info + 17*4)[0]
    assert tag == 49 and count == 20278
    assert info-cmap == count*8 and cmap-records == count*52
    wanted = {ord(c) for line in LINES for c in line}
    glyphs = {}
    # Read only the fixed sample entries from the font's own Unicode table.
    # The incomplete U+3164 slot is not needed and must never be padded.
    for cp, gid in struct.iter_unpack('<II', data[cmap:info]):
        if cp not in wanted:
            continue
        r = struct.unpack_from('<13i', data, records + gid*52)
        size, width, height, stride, flag, offset = r[:6]
        assert size == 52 and 2 <= width <= 12 and height == 12
        assert stride == (width+7)//8 and flag == 256
        assert (width, height) == r[9:11]
        assert offset == struct.unpack_from('<I', data, 16+gid*4)[0]
        raw = data[offset:offset+stride*height]
        assert len(raw) == stride*height
        glyphs[cp] = (width, height, stride, raw)
    assert set(glyphs) == wanted
    widths = [sum(glyphs[ord(c)][0] for c in line) for line in LINES]
    assert widths == [144, 144, 171]
    image = Image.new('RGBA', (171, 44), (255, 255, 255, 0))
    for li, line in enumerate(LINES):
        x0 = 0
        for char in line:
            width, height, stride, raw = glyphs[ord(char)]
            for y in range(height):
                row = int.from_bytes(raw[y*stride:(y+1)*stride], 'big')
                assert row & ((1 << (stride*8-width))-1) == 0
                for x in range(width):
                    if row & (1 << (stride*8-1-x)):
                        image.putpixel((x0+x, li*16+y), (0, 0, 0, 255))
            x0 += width
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Local MR100.fnt with the documented SHA256')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    render(args.source, args.output)
