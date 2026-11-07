"""Redraw only the approved fixed YP-T6 specimen from SHA-locked local resource.bin.
No downloads, firmware execution, arbitrary text, font export or glyph-data output.
"""
from pathlib import Path
import argparse
import hashlib
from PIL import Image

SOURCE_SHA256 = '39c90743c732fb1e08014c64812cbf178858b3eaa12b232a4a5a89a42bd5aebb'
LINES = ['视野无限广，窗外有蓝天。', '視野無限廣，窗外有藍天。', '0123456789 AaBb GgMm !?:+-.']


def render(source, output):
    raw = Path(source).read_bytes()
    if len(raw) != 3168312 or hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('YP-T6 resource.bin SHA256 or size mismatch')
    assert raw[63:67] == b'STMP'
    blocks = [raw[i:i+512] for i in range(67, len(raw), 512)]
    assert len(blocks) == 6188 and len(blocks[-1]) == 501
    assert all(len(b) == 512 and b[-2:] == b'\xde\xde' for b in blocks[:-1])
    data = b''.join(b[:-2] for b in blocks[:-1]) + blocks[-1]
    assert hashlib.sha256(data).hexdigest() == 'fc7e365559c632c2bca581d81ad4875b99721cad54809ef61263d57ef82f8a7f'

    def u(offset):
        assert 0 <= offset <= len(data)-3
        return int.from_bytes(data[offset:offset+3], 'little')

    def table(base, end):
        count = u(base)
        last = base + 3 + 6*count
        result = {}
        for i in range(count):
            ident = u(base+3+6*i)
            offset = base + 3*u(base+6+6*i)
            assert ident not in result and offset == last and u(offset) == ident
            size, kind = u(offset+3), u(offset+6)
            last = offset+9+((size+2)//3)*3
            assert last <= end
            result[ident] = (offset+9, size, kind, last)
        assert last == end
        return result

    root = table(0, len(data))
    assert len(root) == 1230
    maps = table(root[1048][0], root[1048][3])
    pages = table(root[1050][0], root[1050][3])
    glyphs = {}
    for cp in {ord(c) for line in LINES for c in line}:
        page = u(root[1047][0]+(cp>>8)*3)
        assert page & 0x10000
        mapped = u(maps[(page & 0xffff)+1][0]+(cp & 255)*3)
        assert mapped != 1  # Shared default glyph is not coverage.
        entry = pages[(mapped>>8)+1]
        slots = table(entry[0], entry[3])
        offset, size, kind, _ = slots[(mapped & 255)+1]
        width, height = u(offset), u(offset+3)
        assert kind == 3 and height == 16 and size == 6+width*2
        pixels = data[offset+6:offset+size]
        assert len(pixels) == width*2
        glyphs[cp] = (width, height, pixels)
    assert [sum(glyphs[ord(c)][0] for c in line) for line in LINES] == [168, 168, 211]
    image = Image.new('RGBA', (211, 56), (0, 0, 0, 0))
    for li, line in enumerate(LINES):
        x0 = 0
        for char in line:
            width, height, pixels = glyphs[ord(char)]
            for y in range(height):
                for x in range(width):
                    if pixels[(y//8)*width+x] & (1 << (y%8)):
                        image.putpixel((x0+x, li*20+y), (0, 0, 0, 255))
            x0 += width
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Local resource.bin with the documented SHA256')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    render(args.source, args.output)
