#!/usr/bin/env python3
"""Redraw one approved AIX/ISAS sample from three exact local PCFs.

No network, font installation, full-font export or embedded glyph arrays.
Requires Pillow. Source Unicode values are read directly, without CNS conversion.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image
from render_hpux_sung import parse

ROOT = Path(__file__).resolve().parents[1]
CHINESE = '視野無限廣，窗外有藍天。'
ASCII = '0123456789 AaBb GgMm !?:+-.'
SOURCE_NAMES = ('cns1ucs.pcf', 'cns2ucs.pcf', 'Roman27ucs.pcf')


def render(source):
    manifest = json.loads((ROOT / 'data/aix-isas-cns-sources.json').read_text())
    expected = {f['name']: f['pcfSha256'] for f in manifest['files']}
    fonts = {}
    for name in SOURCE_NAMES:
        blob = (source / name).read_bytes()
        if hashlib.sha256(blob).hexdigest() != expected[name]:
            raise ValueError('Unexpected PCF hash: ' + name)
        props, metrics, bitmaps, encoding = parse(blob)
        wanted = b'ISO8859' if name == 'Roman27ucs.pcf' else b'UCS2.CNS11643.1986'
        if props[b'CHARSET_REGISTRY'] != wanted:
            raise ValueError('Unexpected character encoding: ' + name)
        fonts[name] = (metrics, bitmaps, encoding)

    glyphs = {}
    for char in set(CHINESE + ASCII):
        code = ord(char)
        # Choose original Roman for ASCII explicitly. Never let CNS1 [] shadow it.
        names = ('Roman27ucs.pcf',) if 32 <= code <= 126 else SOURCE_NAMES[:2]
        matches = [fonts[n] for n in names if code in fonts[n][2]]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous sample codepoint: U+%04X' % code)
        metrics, bitmaps, encoding = matches[0]
        index = encoding[code]  # No default/fallback substitution, including CNS2 U+3000.
        metric, bitmap = metrics[index], bitmaps[index]
        width = 13 if 32 <= code <= 126 else 26
        if tuple(metric) != (width, 27, 0, width, width, 26, 1, 0):
            raise ValueError('Unexpected source metrics: U+%04X' % code)
        if char != ' ' and not bitmap.getbbox():
            raise ValueError('Blank sample glyph: U+%04X' % code)
        glyphs[char] = (metric, bitmap)

    lines = (CHINESE, ASCII)
    width = max(sum(glyphs[c][0][4] for c in line) for line in lines) + 8
    out = Image.new('RGBA', (width, 66), (255, 255, 255, 0))
    for line_index, line in enumerate(lines):
        x = 4
        for char in line:
            metric, bitmap = glyphs[char]
            out.paste(Image.new('RGBA', bitmap.size, (28, 31, 33, 255)),
                      (x + metric[2], 4 + line_index * 31), bitmap)
            x += metric[4]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Directory containing the three decompressed PCFs')
    parser.add_argument('output', type=Path, help='New output directory; must not exist')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must not already exist')
    rendered = render(args.source)
    args.output.mkdir(parents=True)
    rendered.save(args.output / 'aix_isas_cns_24.png')


if __name__ == '__main__':
    main()
