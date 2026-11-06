#!/usr/bin/env python3
"""Offline Palm m515 system ASCII plus optional CJKOS XiMing composition.
Contains no font data; never executes or flashes firmware.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import cjkos_to_bdf as cjkos

ROM_SHA256 = '47bb591f77390eae3b94669e1cb77ac8f8f5acced3d1cff35acd1ae205248f20'
ROM_SHA1 = 'a0767ea26cc493a3f687525d173903fef89f1acb'
XIMING_SHA256 = 'a8de69c5cf30d53a3433c63c1fea1f02a54f21e380ebfe1d312514a51eabf091'
NFNT_SHA256 = '1070e21fcb60a4b58f456364af8917ce8d9508c1f88f9894f9aec62b050d790a'
BASE = 0x10000000


def parse_nfnt(data):
    """Decode printable ASCII with original pixels, advance and source metrics."""
    if len(data) < 26:
        raise ValueError('Truncated NFNT header')
    keys = ('fontType firstChar lastChar maxWidth kernMax nDescent fRectWidth '
            'fRectHeight owTLoc ascent descent leading rowWords').split()
    h = dict(zip(keys, struct.unpack_from('>13H', data)))
    if (h['fontType'] != 0x9000 or not 0 <= h['firstChar'] <= 32 <= 126 <= h['lastChar'] <= 255
            or h['kernMax'] or h['nDescent'] or not 0 < h['fRectHeight'] <= 32
            or not 0 < h['rowWords'] <= 256
            or h['ascent'] + h['descent'] != h['fRectHeight']):
        raise ValueError('Unsupported NFNT geometry')
    count = h['lastChar'] - h['firstChar'] + 1
    rowbytes = h['rowWords'] * 2
    loc = 26 + rowbytes * h['fRectHeight']
    ow = 16 + 2 * h['owTLoc']
    if ow != loc + 2 * (count + 2) or len(data) != ow + 2 * (count + 2):
        raise ValueError('Invalid NFNT table bounds')
    positions = struct.unpack_from('>' + 'H' * (count + 2), data, loc)
    if any(a > z for a, z in zip(positions, positions[1:])) or positions[-1] > rowbytes * 8:
        raise ValueError('Invalid NFNT bitmap locations')
    glyphs = {}
    for cp in range(32, 127):
        idx = cp - h['firstChar']
        start, end = positions[idx:idx + 2]
        bearing, advance = struct.unpack_from('>bb', data, ow + 2 * idx)
        if bearing != 0 or not 0 < advance <= h['maxWidth'] or end - start != advance:
            raise ValueError('Unexpected ASCII metrics')
        pixels = tuple(tuple((data[26 + y * rowbytes + x // 8] >> (7 - x % 8)) & 1
                       for x in range(start, end)) for y in range(h['fRectHeight']))
        if (cp == 32) != (not any(any(row) for row in pixels)):
            raise ValueError('Unexpected empty ASCII glyph')
        glyphs[cp] = dict(pixels=pixels, advance=advance, width=end-start,
                          height=h['fRectHeight'], bearing_x=bearing)
    return glyphs, h


def load_system_latin(path):
    rom = Path(path).read_bytes()
    if len(rom) != 4194304 or hashlib.sha256(rom).hexdigest() != ROM_SHA256:
        raise ValueError('Not the documented Palm m515 OS4.1 ROM')
    db = 0x196B5E
    if rom[db:db+20] != b'Latin Locale Module\0' or rom[db+60:db+68] != b'locmpsys':
        raise ValueError('Unexpected locale database')
    count = struct.unpack_from('>H', rom, db + 76)[0]
    resources = {}
    for j in range(count):
        typ, rid, addr = struct.unpack_from('>4sHI', rom, db + 78 + 10*j)
        resources[typ, rid] = addr - BASE
    idx = resources[b'fnti', 32000]
    nfonts = struct.unpack_from('>H', rom, idx)[0]
    index = [struct.unpack_from('>4sH', rom, idx+2+i*6) for i in range(nfonts)]
    if index[0] != (b'NFNT', 32000):
        raise ValueError('fontID 0 does not resolve to NFNT 32000')
    off = resources[index[0]]
    header = struct.unpack_from('>13H', rom, off)
    length = 16 + 2*header[8] + 2*(header[2]-header[1]+3)
    raw = rom[off:off+length]
    if hashlib.sha256(raw).hexdigest() != NFNT_SHA256:
        raise ValueError('Unexpected system font resource')
    glyphs, metrics = parse_nfnt(raw)
    return glyphs, dict(rom_sha256=ROM_SHA256, rom_sha1=ROM_SHA1,
        database='Latin Locale Module', database_offset=hex(db),
        font_index_offset=hex(idx), font_id=0, resource_type='NFNT', resource_id=32000,
        font_offset=hex(off), font_sha256=NFNT_SHA256, source_metrics=metrics)


def glyph_blocks(glyphs, y_offset, em_height=12):
    blocks = []
    for cp, g in sorted(glyphs.items()):
        w, h = g['width'], g['height']; digits = 2*((w+7)//8); pad = digits*4-w
        blocks += [f'STARTCHAR latin-U{cp:04X}', f'ENCODING {cp}',
            f'SWIDTH {round(g["advance"]*1000/em_height)} 0', f'DWIDTH {g["advance"]} 0',
            f'BBX {w} {h} {g["bearing_x"]} {y_offset}', 'BITMAP']
        for row in g['pixels']:
            v = 0
            for bit in row: v = (v << 1) | bit
            blocks.append(f'{v << pad:0{digits}X}')
        blocks += ['ENDCHAR']
    return blocks


def standalone_bdf(glyphs, info):
    h = info['source_metrics']; height = h['fRectHeight']
    lines = ['STARTFONT 2.1', 'COMMENT Original Palm m515 OS4.1 stdFont; source baseline retained.',
        'FONT -archive-PalmM515Std-medium-r-normal--11-110-72-72-p-0-ISO10646-1',
        f'SIZE {height} 72 72', f'FONTBOUNDINGBOX {h["maxWidth"]} {height} 0 {-h["descent"]}',
        'STARTPROPERTIES 4', f'FONT_ASCENT {h["ascent"]}', f'FONT_DESCENT {h["descent"]}',
        'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"', 'ENDPROPERTIES', 'CHARS 95']
    return '\n'.join(lines + glyph_blocks(glyphs, -h['descent'], height) + ['ENDFONT', ''])


def compose_bdf(original_bdf, glyphs):
    """Append 95 ASCII blocks; every original CJK block/metric is unchanged."""
    if set(glyphs) != set(range(32, 127)):
        raise ValueError('Expected exactly 95 printable ASCII characters')
    if 'FONTBOUNDINGBOX 12 12 0 0\n' not in original_bdf or 'FONT_ASCENT 12\nFONT_DESCENT 0\n' not in original_bdf:
        raise ValueError('Unexpected CJKOS export metrics')
    if any(f'\nENCODING {cp}\n' in original_bdf for cp in glyphs):
        raise ValueError('ASCII would replace an original mapping')
    lines = original_bdf.splitlines()
    count_line = next(i for i,s in enumerate(lines) if s.startswith('CHARS '))
    count = int(lines[count_line].split()[1]); lines[count_line] = f'CHARS {count+95}'
    # Font identity declares the composition; no CJK glyph metadata is changed.
    for i, line in enumerate(lines):
        if line.startswith('FONT '):
            lines[i] = line.replace('-CJKOSbig5-', '-CJKOSXiMingM515Std-').replace('-72-72-c-', '-72-72-p-')
    lines.insert(1, 'COMMENT Explicit CJKOS XiMing + compatible Palm m515 system Latin composition; not original runtime layout.')
    lines.insert(2, 'COMMENT CJK glyph blocks and cell-bottom baseline unchanged; Latin 11px cell bottom-aligned in 12px cell.')
    if lines[-1] != 'ENDFONT': raise ValueError('Invalid BDF end')
    return '\n'.join(lines[:-1] + glyph_blocks(glyphs, 0) + ['ENDFONT',''])


def export(rom, cjkos_path, output):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Output directory must be new')
    for parent in output.parents:
        if parent.is_symlink(): raise ValueError('Symlink output parent is not allowed')
    latin, info = load_system_latin(rom)
    han, han_info = cjkos.load_font(cjkos_path)
    if han_info['source_sha256'] != XIMING_SHA256:
        raise ValueError('This composition only accepts the retained XiMing source')
    original, han_report = cjkos.render_bdf(han, han_info)
    files = {'palm-m515-std-ascii.bdf': standalone_bdf(latin, info),
             'cjkos-ximing-original.bdf': original,
             'cjkos-ximing-m515-std-combined.bdf': compose_bdf(original, latin)}
    report = dict(latin_source=info, chinese_source=han_report,
        ascii_glyphs=95, original_cjk_slots=len(han), combined_slots=len(han)+95,
        combined_encoded_glyphs=han_report['encoded_glyphs']+95,
        original_chinese_metrics_preserved=True, latin_pixels_and_advances_preserved=True,
        layout='Composition only: retain CJK cell-bottom baseline and 12px advance; bottom-align original 11px Latin cell. Not verified original CJKOS runtime layout.',
        source_rights='Original rights apply; public availability is not redistribution permission.',
        sha256={name:hashlib.sha256(data.encode('ascii')).hexdigest() for name,data in files.items()})
    output.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        with (output/name).open('x', encoding='ascii') as f: f.write(data)
    with (output/'report.json').open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2); f.write('\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', type=Path, required=True)
    p.add_argument('--cjkos', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a=p.parse_args()
    try: print(json.dumps(export(a.rom,a.cjkos,a.output),ensure_ascii=False,indent=2))
    except (OSError,ValueError,struct.error,KeyError) as e: p.exit(1,f'Error: {e}\n')
if __name__ == '__main__': main()
