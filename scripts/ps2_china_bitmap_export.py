#!/usr/bin/env python3
"""Offline PS2 SCPH-50009 ROM2 bitmap specimen / optional local BDF export.
Standard library only. Contains no font payload. Firmware is read, never run.
All output uses 24x24 storage cells, not inferred console runtime metrics.
"""
import argparse
import binascii
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import zlib

ROM_SIZE = 2097152
ROM_SHA256 = 'fe61257af2cd2675256c2dcc5ffd78eae1a22d24f816571c2f927a93ed3bcc2d'
MODULES = {
    'FNTHANCH': (0xD0, 6912, '26e3532a0609f8051aa9b3755a20ed07cc4ce5aa94560392896175e0d9895281'),
    'GB18030': (0x1BD0, 2058552, 'd9e535e7497b8e444e642715e420ccb0d7118bec05ec71f36e585670db4fd5a4'),
}
PHRASE = '视野无限广，窗外有蓝天。'
EXTRA = '片版牌局'
TRADITIONAL = '視野無限廣，窗外有藍天。'
ASCII = '0123456789 AaBb GgMm !?:+-.'
CELL = 24
FRAME_BYTES = 72
ID = 'ps2_scph50009_24'
MAPPING_SHA256 = {'gb2312': '34e0e683935693242385c15945497ec2624afc4033ad1d86938d16e1465843a9', 'gbk': 'c4f78ed3a32c73a0347d5247af88662af433ae6730e82d5bee7880fcc7a2d77d'}  # Unicode/source-slot hashes, not glyph data.


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def reject_symlinks(path):
    p = Path(path).absolute()
    for component in (p, *p.parents):
        require(not component.is_symlink(), 'Symbolic links are not accepted')


def read_source(path):
    path = Path(path)
    reject_symlinks(path)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    with os.fdopen(os.open(path, flags), 'rb') as handle:
        info = os.fstat(handle.fileno())
        require(stat.S_ISREG(info.st_mode), 'Input must be a regular ROM2 file')
        require(info.st_size == ROM_SIZE, 'Expected complete 2097152-byte ROM2; 512KiB underdumps are unsupported')
        data = handle.read(ROM_SIZE + 1)
    validate_source(data)
    return data


def romdir(data):
    """Parse this ROM2's directory at zero, tracking 16-byte-aligned modules."""
    require(len(data) >= 96, 'Truncated ROMDIR')
    result = {}
    offset = 0
    for position in range(0, min(len(data), 4096), 16):
        raw_name, ext_size, size = struct.unpack_from('<10sHI', data, position)
        if raw_name == bytes(10):
            break
        name = raw_name.split(b'\0', 1)[0].decode('ascii')
        require(name not in result, 'Duplicate ROMDIR name')
        require(offset + size <= len(data), 'ROMDIR module extent exceeds source')
        result[name] = (offset, size)
        offset += (size + 15) & ~15
    else:
        raise ValueError('Unterminated ROMDIR')
    require(result.get('RESET') == (0, 0), 'Unexpected ROMDIR first module')
    require(result.get('ROMDIR') == (0, 96), 'Unexpected ROMDIR table extent')
    require(result.get('EXTINFO') == (96, 108), 'Unexpected EXTINFO extent')
    return result


def validate_source(data):
    require(len(data) == ROM_SIZE and sha256(data) == ROM_SHA256,
            'Unsupported or modified ROM2: size/SHA-256 mismatch')
    directory = romdir(data)
    for name, (offset, size, digest) in MODULES.items():
        require(directory.get(name) == (offset, size), 'Unexpected module location: ' + name)
        require(sha256(data[offset:offset + size]) == digest, 'Module hash mismatch: ' + name)


def slot_index(lead, trail):
    """Only the four verified source blocks; no guessed GB18030 ranges."""
    if 0xA1 <= lead <= 0xA9 and 0xA1 <= trail <= 0xFE:
        return (lead - 0xA1) * 94 + trail - 0xA1
    if 0xB0 <= lead <= 0xF7 and 0xA1 <= trail <= 0xFE:
        return 846 + (lead - 0xB0) * 94 + trail - 0xA1
    if 0x81 <= lead <= 0xA0 and 0x40 <= trail <= 0xFE and trail != 0x7F:
        return 7614 + (lead - 0x81) * 190 + trail - 0x40 - (trail >= 0x80)
    if 0xAA <= lead <= 0xFE and 0x40 <= trail <= 0xA0 and trail != 0x7F:
        return 13694 + (lead - 0xAA) * 96 + trail - 0x40 - (trail >= 0x80)
    return None


def mapping(repertoire='gbk'):
    require(repertoire in ('gb2312', 'gbk'), 'Unsupported repertoire')
    result = {}
    for lead in range(0x81, 0xFF):
        for trail in range(0x40, 0xFF):
            index = slot_index(lead, trail)
            if index is None:
                continue
            try:
                c = bytes((lead, trail)).decode(repertoire)
            except UnicodeDecodeError:
                continue
            require(len(c) == 1 and ord(c) not in result, 'Ambiguous Unicode mapping')
            result[ord(c)] = index
    require(len(result) == {'gb2312': 7445, 'gbk': 21638}[repertoire], 'Unexpected codec mapping count')
    digest = sha256(''.join(f'{cp:04X}:{slot}\n' for cp, slot in sorted(result.items())).encode('ascii'))
    if repertoire in MAPPING_SHA256:
        require(digest == MAPPING_SHA256[repertoire], 'Codec mapping differs from audited mapping')
    return result


def decode_rows(frame):
    require(len(frame) == FRAME_BYTES, 'Each glyph must contain exactly 72 bytes')
    return tuple(int.from_bytes(frame[y:y + 3], 'big') for y in range(0, FRAME_BYTES, 3))


def decode(data, repertoire='gbk'):
    validate_source(data)
    offset = MODULES['GB18030'][0]
    result = {cp: decode_rows(data[offset + index * FRAME_BYTES:offset + (index + 1) * FRAME_BYTES])
              for cp, index in mapping(repertoire).items()}
    start = MODULES['FNTHANCH'][0]
    for cp in range(0x20, 0x7F):
        index = cp - 0x20
        result[cp] = decode_rows(data[start + index * FRAME_BYTES:start + (index + 1) * FRAME_BYTES])
    return result


def png_data(glyphs, texts, gap=0, line_gap=4):
    require(bool(texts) and all(texts), 'Need nonempty text rows')
    widths = [len(text) * (CELL + gap) - gap for text in texts]
    width = max(widths)
    height = len(texts) * CELL + (len(texts) - 1) * line_gap
    pixels = bytearray(bytes((255, 255, 255, 0)) * (width * height))
    for line, text in enumerate(texts):
        top = line * (CELL + line_gap)
        for y in range(CELL):
            for x in range(widths[line]):
                k = ((top + y) * width + x) * 4
                pixels[k:k + 4] = b'\xff\xff\xff\xff'
        for j, c in enumerate(text):
            require(ord(c) in glyphs, f'No verified source glyph for U+{ord(c):04X}')
            for y, row in enumerate(glyphs[ord(c)]):
                for x in range(CELL):
                    if row & (1 << (23 - x)):
                        k = ((top + y) * width + j * (CELL + gap) + x) * 4
                        pixels[k:k + 4] = b'\0\0\0\xff'
    raw = b''.join(b'\0' + pixels[y * width * 4:(y + 1) * width * 4] for y in range(height))
    def chunk(tag, payload):
        return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', binascii.crc32(tag + payload) & 0xFFFFFFFF)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')


def bdf(glyphs):
    lines = ['STARTFONT 2.1', 'COMMENT Native PS2 ROM pixels; rights remain with their owners.',
             'COMMENT STORAGE-CELL CONVENTION ONLY: DWIDTH 24, ascent 24, descent 0.',
             'COMMENT Console runtime advance and baseline are unverified; ASCII ink is at most 12 wide.',
             'FONT -historical-ps2_china-medium-r-normal--24-0-75-75-c-240-iso10646-1',
             'SIZE 24 75 75', 'FONTBOUNDINGBOX 24 24 0 0', 'STARTPROPERTIES 3',
             'FONT_ASCENT 24', 'FONT_DESCENT 0', 'DEFAULT_CHAR 32', 'ENDPROPERTIES', f'CHARS {len(glyphs)}']
    for cp, rows in sorted(glyphs.items()):
        lines += [f'STARTCHAR uni{cp:04X}', f'ENCODING {cp}', 'SWIDTH 960 0', 'DWIDTH 24 0', 'BBX 24 24 0 0', 'BITMAP']
        lines += [f'{row:06X}' for row in rows]
        lines += ['ENDCHAR']
    return '\n'.join(lines + ['ENDFONT', ''])


def write_outputs(output, files):
    output = Path(output)
    reject_symlinks(output)
    require(not output.exists() or output.is_dir(), 'Output is not a directory')
    require(all(Path(name).name == name and name not in ('.', '..') for name in files), 'Invalid output name')
    require(all(not ((output / name).exists() or (output / name).is_symlink()) for name in files),
            'Output exists; refusing all writes')
    output.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for name, payload in files.items():
            path = output / name
            with path.open('xb') as handle:
                created.append(path)
                handle.write(payload)
    except Exception:
        for path in created:
            path.unlink()
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', help='Complete, exact-SHA local SCPH-50009 ROM2 dump, not the 512KiB underdump')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--repertoire', choices=('gbk', 'gb2312'), default='gbk')
    ap.add_argument('--export-bdf', action='store_true', help='Also create a local mapped Unicode BDF; redistribution rights are not implied')
    args = ap.parse_args()
    data = read_source(args.source)
    gs = decode(data, args.repertoire)
    files = {f'{ID}.png': png_data(gs, [PHRASE, ASCII], gap=1)}
    for name, text in [('phrase', PHRASE), ('diagnostic', EXTRA), ('traditional', TRADITIONAL), ('ascii', ASCII)]:
        if all(ord(c) in gs for c in text):
            files[f'ps2-china-{name}-1x.png'] = png_data(gs, [text])
    report = {'rom_sha256': sha256(data), 'module_sha256': {n: s[2] for n, s in MODULES.items()},
              'repertoire': args.repertoire, 'mapped_doublebyte': len(gs) - 95,
              'mapped_han': sum(0x4E00 <= cp <= 0x9FFF for cp in gs),
              'printable_ascii': 95, 'storage_cell': [24, 24], 'runtime_advance': None,
              'ascii_origin': 'FNTHANCH in the same hash-verified ROM2; no other font used',
              'layout': 'Full storage cells plus 1px specimen gap, not console runtime layout',
              'gb18030_unverified': 'Remaining symbols, four-byte/BMP extension and supplementary-plane mappings not exported',
              'specimen_sha256': sha256(files[f'{ID}.png'])}
    files['ps2-china-report.json'] = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if args.export_bdf:
        files[f'ps2-china-{args.repertoire}-storage-cells.bdf'] = bdf(gs).encode('ascii')
    write_outputs(args.output, files)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
