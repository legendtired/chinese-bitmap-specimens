"""Render only the approved fixed PSP Chinese specimen from SHA-locked local inputs.
No downloads, firmware execution, arbitrary text, font export or glyph-data output.
Unicode ranges come from intraFont, not an independently recovered Sony mapping.
"""
from pathlib import Path
import argparse
import hashlib
import re
from PIL import Image

SOURCE_SHA256 = '05c9991fc82c96672026d5e71da595d0a5b028a74607d726e613099db8a3699a'
MAPPING_SHA256 = '3f8692c9c9e63ddb475cb7d0288c73354ca02a25d542bf421f3b9759a0f4a5b2'
LINES = ['视野无限广，窗外有蓝天。', '視野無限廣，窗外有藍天。']


def render(source, mapping_source, output):
    data = Path(source).read_bytes()
    mapping_bytes = Path(mapping_source).read_bytes()
    if len(data) != 1023372 or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('BWFont SHA256 or size mismatch')
    if hashlib.sha256(mapping_bytes).hexdigest() != MAPPING_SHA256:
        raise ValueError('intraFont mapping source SHA256 mismatch')
    table = mapping_bytes.decode('utf-8').split('bw_charmap_compr[] = {')[1].split('};')[0]
    values = [int(x, 0) for x in re.findall(r'0x[0-9a-f]+|\d+', table)]
    assert len(values) == 330
    wanted = {ord(c) for line in LINES for c in line}
    offsets = {}
    count = 0
    previous_end = -1
    for first, length in zip(values[::2], values[1::2]):
        assert length > 0 and first > previous_end
        for cp in wanted:
            if first <= cp < first + length:
                offsets[cp] = (count + cp - first) * 36
        previous_end = first + length - 1
        count += length
    assert count == 28427 and count * 36 == len(data) and set(offsets) == wanted
    image = Image.new('1', (192, 38), 1)
    for li, line in enumerate(LINES):
        for ci, char in enumerate(line):
            start = offsets[ord(char)]
            raw = data[start:start+36]
            assert any(raw)
            for y in range(18):
                row = int.from_bytes(raw[y*2:y*2+2], 'big')
                for x in range(16):
                    if row & (1 << (15-x)):
                        image.putpixel((ci*16+x, li*20+y), 0)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Local gb3s1518.bwfon with the documented SHA256')
    parser.add_argument('--mapping-source', required=True, help='Local intraFont.c at the documented fixed commit')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    render(args.source, args.mapping_source, args.output)
