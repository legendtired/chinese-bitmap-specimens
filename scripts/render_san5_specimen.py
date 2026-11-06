#!/usr/bin/env python3
"""Render only the verified fixed SAN5 DOS specimen from a local ZIKU.16P.

No font data is embedded. No source download, arbitrary-text rendering, font
export, or claim of a fully verified Unicode map is provided here.
The 16px advance and 2px gap are preview conventions, not verified game metrics.
"""
from pathlib import Path
import argparse
import hashlib

SOURCE_SHA256 = '94c3a14bec8930525d798e891d8b3493f64ca292e25ef36d8d7cd3ad18a46bd5'
SOURCE_BYTES = 384704
WIDTH, HEIGHT, BYTES_PER_GLYPH, SLOTS = 16, 14, 28, 13736
CHINESE = '視野無限廣，窗外有藍天。'
FULLWIDTH = '０１２３４５６７８９　ＡａＢｂ　ＧｇＭｍ　！？：＋－․'
# Physical positions, not bitmap data. Slot 4 follows old TCA U+2024;
# the modern CNS table uses U+FF0E at this position. Neither is halfwidth ASCII.
CHINESE_SLOTS = (3503, 3106, 3365, 2171, 4504, 1, 3416, 903, 1079, 5494, 795, 3)
FULLWIDTH_SLOTS = (234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 0,
                   266, 292, 267, 293, 0, 272, 298, 278, 304, 0, 9, 8, 7, 109, 110, 4)


def validate_source(data):
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Expected the documented 384704-byte ZIKU.16P and exact SHA-256; no output written.')


def decode_glyph(data, index):
    if not 0 <= index < SLOTS:
        raise ValueError('Glyph index outside the 13736 complete slots.')
    block = data[index * BYTES_PER_GLYPH:(index + 1) * BYTES_PER_GLYPH]
    if len(block) != BYTES_PER_GLYPH:
        raise ValueError('Incomplete glyph block.')
    return tuple(tuple(bool(block[y * 2 + x // 8] & (128 >> (x % 8)))
                       for x in range(WIDTH)) for y in range(HEIGHT))


def render(data):
    validate_source(data)
    from PIL import Image
    image = Image.new('RGBA', (432, 30), (255, 255, 255, 0))
    pixels = image.load()
    for top, slots in ((0, CHINESE_SLOTS), (16, FULLWIDTH_SLOTS)):
        for column, index in enumerate(slots):
            for y, row in enumerate(decode_glyph(data, index)):
                for x, ink in enumerate(row):
                    if ink:
                        pixels[column * WIDTH + x, top + y] = (0, 0, 0, 255)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    image = render(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental source or existing preview overwrite.
    with args.output.open('xb') as output:
        image.save(output, format='PNG')
    print('Wrote 432×30 fixed PNG; 16×14 source pixels, preview-only 16px advance and 2px gap; game metrics unverified. Fullwidth Latin is not ASCII.')


if __name__ == '__main__':
    main()
