#!/usr/bin/env python3
"""Export saved 1-bit Unicode bitmap strikes, never rasterize outline fonts.

Requires freetype-py. Fonts are supplied locally by the user; no network access,
font data, or redistribution permission is included. Outputs are never replaced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def bitmap_rows(buffer, width, height, pitch):
    """Copy MSB-first native pixels, removing only byte padding beyond BBX."""
    if width < 0 or height < 0 or pitch < 0:
        raise ValueError('Negative dimensions/pitch are not supported; no conversion written.')
    count = (width + 7) // 8
    if pitch < count or len(buffer) < pitch * height:
        raise ValueError('Truncated native bitmap buffer.')
    rows = []
    for y in range(height):
        row = bytearray(buffer[y * pitch:y * pitch + count])
        if width % 8 and row:
            row[-1] &= 0xff << (8 - width % 8) & 0xff
        rows.append(row.hex().upper())
    return rows


def describe_face(face, index):
    return {
        'face': index,
        'family': (face.family_name or b'').decode('utf-8', errors='replace'),
        'style': (face.style_name or b'').decode('utf-8', errors='replace'),
        'strikes': [
            {'strike': i, 'ppemX': s.x_ppem / 64, 'ppemY': s.y_ppem / 64,
             'reportedWidth': s.width, 'reportedHeight': s.height}
            for i, s in enumerate(face.available_sizes)
        ],
    }


def collect_glyphs(face, ft, wanted=None):
    face.select_charmap(ft.FT_ENCODING_UNICODE)
    glyphs, unavailable = [], []
    for code, glyph_index in face.get_chars():
        if not glyph_index or (wanted is not None and code not in wanted):
            continue
        # Control codes are not display glyphs; FreeType may synthesize their advances.
        if code < 32 or 0x7f <= code <= 0x9f or code > 0x10ffff or 0xd800 <= code <= 0xdfff:
            continue
        try:
            # Unlike FT_LOAD_DEFAULT/RENDER, this refuses outline fallback.
            face.load_glyph(glyph_index, ft.FT_LOAD_SBITS_ONLY)
        except ft.FT_Exception:
            unavailable.append(code)
            continue
        slot = face.glyph
        if slot.format != ft.FT_GLYPH_FORMAT_BITMAP:
            raise ValueError(f'U+{code:04X} is not a native bitmap; refusing outline fallback.')
        bitmap = slot.bitmap
        if bitmap.width and bitmap.rows and bitmap.pixel_mode != ft.FT_PIXEL_MODE_MONO:
            raise ValueError(f'U+{code:04X} is not 1-bit; grayscale/color conversion is unsupported.')
        if slot.advance.x % 64 or slot.advance.y != 0:
            raise ValueError(f'U+{code:04X} has unsupported fractional/vertical advance.')
        glyphs.append({
            'code': code, 'advance': slot.advance.x // 64,
            'bbx': [bitmap.width, bitmap.rows, slot.bitmap_left, slot.bitmap_top - bitmap.rows],
            'rows': bitmap_rows(bitmap.buffer, bitmap.width, bitmap.rows, bitmap.pitch),
        })
    if wanted is not None:
        unavailable = sorted(wanted - {g['code'] for g in glyphs})
    if not glyphs:
        raise ValueError('No mapped native bitmap glyphs at this strike; no outline fallback used.')
    return glyphs, unavailable


def bdf_text(glyphs, ppem, ascender, descender, source_sha, face_index, strike_index):
    left = min(g['bbx'][2] for g in glyphs)
    bottom = min(g['bbx'][3] for g in glyphs)
    right = max(g['bbx'][2] + g['bbx'][0] for g in glyphs)
    top = max(g['bbx'][3] + g['bbx'][1] for g in glyphs)
    ascent = max(0, top, ascender)
    descent = max(0, -bottom, -descender)
    lines = [
        'STARTFONT 2.1',
        'COMMENT Saved native 1-bit bitmap pixels; no outline rasterization or fallback.',
        'COMMENT This conversion does not grant font use or redistribution rights.',
        f'COMMENT Source SHA256 {source_sha}; face {face_index}; strike {strike_index}.',
        f'FONT -Recovered-EmbeddedBitmap-Medium-R-Normal--{ppem}-{ppem * 10}-72-72-P-0-ISO10646-1',
        f'SIZE {ppem} 72 72',
        f'FONTBOUNDINGBOX {right - left} {top - bottom} {left} {bottom}',
        'STARTPROPERTIES 4', f'FONT_ASCENT {ascent}', f'FONT_DESCENT {descent}',
        'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"', 'ENDPROPERTIES',
        f'CHARS {len(glyphs)}',
    ]
    for g in glyphs:
        lines.extend([
            f"STARTCHAR uni{g['code']:04X}", f"ENCODING {g['code']}",
            f"SWIDTH {round(g['advance'] * 1000 / ppem)} 0", f"DWIDTH {g['advance']} 0",
            'BBX ' + ' '.join(map(str, g['bbx'])), 'BITMAP', *g['rows'], 'ENDCHAR',
        ])
    return '\n'.join([*lines, 'ENDFONT', ''])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('font', type=Path)
    p.add_argument('output', type=Path, nargs='?', help='New .bdf file; never overwrite')
    p.add_argument('--list', action='store_true', help='List collection faces and saved bitmap strikes')
    p.add_argument('--face', type=int, default=0, help='Collection face index, default 0')
    selection = p.add_mutually_exclusive_group()
    selection.add_argument('--ppem', type=int, help='Exact square native strike size, not a resize request')
    selection.add_argument('--strike', type=int, help='Exact index from --list')
    p.add_argument('--text', help='Export only these Unicode characters; default is all mapped native glyphs')
    a = p.parse_args(argv)
    try:
        import freetype as ft
    except ImportError:
        p.error('Install dependency first: python3 -m pip install freetype-py==2.5.1')
    try:
        if a.face < 0:
            raise ValueError('--face must be zero or greater.')
        if not a.font.is_file():
            raise ValueError('Input font does not exist.')
        first = ft.Face(str(a.font))
        if a.list:
            print(json.dumps([describe_face(ft.Face(str(a.font), i), i)
                              for i in range(first.num_faces)], ensure_ascii=False, indent=2))
            return
        if a.output is None or (a.ppem is None and a.strike is None):
            p.error('Export requires OUTPUT and exactly one of --ppem or --strike; use --list first.')
        if a.output.exists():
            raise ValueError('Output already exists. Choose a new name; nothing was replaced.')
        if a.face >= first.num_faces:
            raise ValueError('Face index out of range; use --list.')
        face = ft.Face(str(a.font), a.face)
        if a.ppem is not None:
            matches = [i for i, s in enumerate(face.available_sizes)
                       if s.x_ppem == a.ppem * 64 and s.y_ppem == a.ppem * 64]
            if len(matches) != 1:
                raise ValueError('No unique exact bitmap strike. Use --list and --strike; no resizing performed.')
            strike = matches[0]
        else:
            strike = a.strike
        if strike < 0 or strike >= len(face.available_sizes):
            raise ValueError('Strike index out of range; no saved bitmap strike selected.')
        size = face.available_sizes[strike]
        if size.y_ppem <= 0 or size.y_ppem % 64:
            raise ValueError('Fractional or invalid ppem is unsupported.')
        face.select_size(strike)
        glyphs, unavailable = collect_glyphs(face, ft, None if a.text is None else set(map(ord, a.text)))
        sha = hashlib.sha256(a.font.read_bytes()).hexdigest()
        content = bdf_text(glyphs, size.y_ppem // 64, face.size.ascender // 64,
                           face.size.descender // 64, sha, a.face, strike)
        with a.output.open('x', encoding='ascii', newline='\n') as out:
            out.write(content)
        print(json.dumps({
            'output': str(a.output), 'sourceSha256': sha, 'face': a.face, 'strike': strike,
            'ppemX': size.x_ppem / 64, 'ppemY': size.y_ppem / 64,
            'glyphCount': len(glyphs), 'unavailableCount': len(unavailable),
            'unavailable': [f'U+{u:04X}' for u in unavailable],
            'method': 'Native 1-bit display bitmap; Unicode cmap only; controls omitted; no outlines/fallback/resizing.',
        }, ensure_ascii=False, indent=2))
    except (ValueError, OSError, ft.FT_Exception) as exc:
        p.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
