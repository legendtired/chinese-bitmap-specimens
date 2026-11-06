#!/usr/bin/env python3
"""Decode one verified MStar 18x18 stored bitmap; no source font included.

Offline only. Does not execute firmware, rasterize outlines, grant font rights,
or overwrite output. Variable-width mode uses the source bbox width with no
extra gap; fixed mode uses the 18px stored cell. Neither is a hardware capture.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

SOURCE_SHA256 = 'b2860bdb2486c5901bcebe3b29d4e009ec9151915c4d9640a8009d039903f0bf'
EXPECTED_HEADER = (0x466f4e74, 1, 7804, 18, 18, 1, 0, 128, 31344, 3649, 56, 53238, 437024)


def decode(data):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported source SHA256; only the verified Simp_ch_18X18.bin is accepted.')
    if len(data) != 490262 or struct.unpack_from('<13I', data) != EXPECTED_HEADER:
        raise ValueError('Invalid source length/header.')
    h = EXPECTED_HEADER
    mapping = {}
    for i in range(h[9]):
        first, last, index = struct.unpack_from('<HHH', data, h[8] + 6*i)
        if first > last:
            raise ValueError('Invalid Unicode range.')
        for code in range(first, last+1):
            if code in mapping or index+code-first >= h[2] or 0xd800 <= code <= 0xdfff:
                raise ValueError('Overlapping/out-of-range Unicode mapping.')
            mapping[code] = index+code-first
    if len(mapping) != h[2] or set(mapping.values()) != set(range(h[2])):
        raise ValueError('Incomplete glyph mapping.')
    result = []
    for code, index in sorted(mapping.items()):
        start = h[11] + index*h[10]
        glyph = data[start:start+54]
        # Keep the complete 18x18 stored rectangle, clearing only byte-padding bits.
        rows = [int.from_bytes(glyph[y*3:y*3+3], 'big') >> 6 for y in range(18)]
        box = list(data[h[7]+4*index:h[7]+4*index+4])
        result.append({'code': code, 'index': index, 'rows': rows, 'source_bbox': box})
    han = [g for g in result if 0x4e00 <= g['code'] <= 0x9fff]
    gb = {c for c in range(0x4e00, 0xa000) if chr(c).encode('gb2312', errors='ignore')}
    if {g['code'] for g in han} != gb or any(not any(g['rows']) for g in han):
        raise ValueError('GB2312 Hanzi coverage failed.')
    return result


def bdf_text(glyphs, layout="variable"):
    if layout not in ("variable", "fixed"):
        raise ValueError("Unknown layout mode.")
    out = ['STARTFONT 2.1', 'COMMENT Original stored pixels; no outline rasterization or fallback.',
           'COMMENT No font use or redistribution permission is granted.',
           f'COMMENT Layout {layout}: source-supported mode with zero additional gap; no hardware spacing claim.',
           'COMMENT Full stored BBX and common y=0 baseline retained as export convention.',
           'COMMENT SOURCE_BBOX records original x,width,y,height bytes; variable advance uses width.',
           f'COMMENT Source SHA256 {SOURCE_SHA256}',
           f'FONT -Recovered-MStarStoredBitmap-Medium-R-Normal--18-180-72-72-{"P-0" if layout == "variable" else "C-180"}-ISO10646-1',
           'SIZE 18 72 72', 'FONTBOUNDINGBOX 18 18 0 0', 'STARTPROPERTIES 5',
           'FONT_ASCENT 18', 'FONT_DESCENT 0', 'PIXEL_SIZE 18',
           'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"', 'ENDPROPERTIES',
           f'CHARS {len(glyphs)}']
    for g in glyphs:
        advance = g['source_bbox'][1] if layout == 'variable' else 18
        out += [f"STARTCHAR uni{g['code']:04X}", f"ENCODING {g['code']}",
                f"COMMENT SOURCE_INDEX {g['index']}",
                'COMMENT SOURCE_BBOX ' + ' '.join(map(str, g['source_bbox'])),
                f'SWIDTH {round(advance*1000/18)} 0', f'DWIDTH {advance} 0', 'BBX 18 18 0 0', 'BITMAP',
                *[f'{row << 6:06X}' for row in g['rows']], 'ENDCHAR']
    return '\n'.join([*out, 'ENDFONT', ''])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path, nargs='?')
    p.add_argument('--inspect', action='store_true')
    p.add_argument('--layout', choices=('variable','fixed'), default='variable',
                   help='Source-supported width mode, zero additional gap (default: variable)')
    p.add_argument('--text', help='Export only these actual Unicode characters; no replacements')
    a = p.parse_args(argv)
    try:
        glyphs = decode(a.source.read_bytes())
        if a.text is not None:
            wanted = {ord(c) for c in a.text}
            present = {g['code'] for g in glyphs}
            missing = wanted-present
            if missing:
                raise ValueError('Missing code points: ' + ', '.join(f'U+{c:04X}' for c in sorted(missing)))
            glyphs = [g for g in glyphs if g['code'] in wanted]
            if not glyphs:
                raise ValueError('Empty requested subset.')
        if a.inspect:
            print(json.dumps({'sha256': SOURCE_SHA256, 'mapped_glyphs': len(glyphs),
                'hanzi': sum(0x4e00 <= g['code'] <= 0x9fff for g in glyphs),
                'storage_cell': [18,18], 'source_max_hanzi_ink': [14,14],
                'layout': a.layout, 'additional_gap': 0, 'hardware_layout_verified': False}, ensure_ascii=False, indent=2))
        else:
            if a.output is None:
                raise ValueError('OUTPUT is required unless --inspect is used.')
            with a.output.open('x', encoding='ascii', newline='\n') as f:
                f.write(bdf_text(glyphs, a.layout))
            print(f'Exported {len(glyphs)} mapped stored glyphs to {a.output}. Font rights unchanged.')
    except (OSError, ValueError, struct.error) as e:
        p.error(str(e))


if __name__ == '__main__':
    main()
