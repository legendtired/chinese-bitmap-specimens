#!/usr/bin/env python3
"""Export native FM Towns II FreshTV 20x20 Hanzi from a verified local ROM.
Offline and standard-library only. The ROM is data, never executed.
No symbols, ANK/ASCII, 16-dot output, resampling, substitutions, or fallback.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROM_SIZE = 524288
ROM_SHA256 = 'dca1f314ae2f5dc937706624990b8521016ee2231558f6cbe169bbc305efb774'
HEADER = bytes.fromhex('464f4e54322020200001001400142284')
BITMAP_BASE = 0x2810
HAN_ROWS = (0x30, 0x74)
HAN_SLOTS = 6486
HAN_GLYPHS = 6355
FRAME_BYTES = 60
ROW_BYTES = 3
MAPPING_SHA256 = '558ad35605838feb2cdc8b7ab25f622f72345dc571c047945e6cd1247a5601c9'
OUTPUT_NAME = 'fmtowns-f20-20x20.bdf'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def reject_symlinks(path):
    """Reject a symbolic link at any component, including dangling links."""
    path = Path(path).absolute()
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError(f'Symbolic links are not accepted: {component}')


def load_rom(path):
    path = Path(path)
    reject_symlinks(path)
    # O_NOFOLLOW protects the final component; O_NONBLOCK prevents a FIFO
    # from blocking before the regular-file check. Input is opened read-only.
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError as error:
        raise ValueError('Missing ROM file') from error
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('ROM input must be a regular file')
        if info.st_size != ROM_SIZE:
            raise ValueError(f'Incorrect ROM size: expected {ROM_SIZE} bytes')
        rom = handle.read(ROM_SIZE + 1)
    if len(rom) != ROM_SIZE or sha256(rom) != ROM_SHA256:
        raise ValueError('SHA-256 mismatch; unsupported or modified FMT_F20.ROM')
    return rom


def glyph_offset(row, cell):
    """Physical address of a level-1/2 Hanzi slot, not a Unicode index."""
    if not HAN_ROWS[0] <= row <= HAN_ROWS[1] or not 0x21 <= cell <= 0x7E:
        raise ValueError('JIS row or cell outside the supported Hanzi rows')
    return BITMAP_BASE + ((row - 0x21) * 94 + cell - 0x21) * FRAME_BYTES


def unicode_for_jis(row, cell):
    glyph_offset(row, cell)
    try:
        character = bytes((row + 0x80, cell + 0x80)).decode('euc_jp')
    except UnicodeDecodeError:
        return None
    if len(character) != 1 or not 0x4E00 <= ord(character) <= 0x9FFF:
        raise ValueError('Unexpected non-Hanzi JIS mapping')
    return ord(character)


def extract(rom):
    """Return Unicode-sorted (codepoint, native row-major frame) pairs.

    This low-level parser also accepts invented test data. The export entry
    point always calls load_rom first and requires the exact known source hash.
    """
    if len(rom) != ROM_SIZE:
        raise ValueError('Incorrect ROM size')
    if rom[:len(HEADER)] != HEADER:
        raise ValueError('Unexpected FONT2 header or native dimensions')
    glyphs, mapping = {}, []
    slots = 0
    for row in range(HAN_ROWS[0], HAN_ROWS[1] + 1):
        for cell in range(0x21, 0x7F):
            start = glyph_offset(row, cell)
            if start != 0x17288 + slots * FRAME_BYTES:
                raise ValueError('Physical Hanzi slot order mismatch')
            slots += 1
            frame = rom[start:start + FRAME_BYTES]
            if len(frame) != FRAME_BYTES:
                raise ValueError('Truncated native 20x20 frame')
            if any(frame[index] & 0x0F for index in range(2, FRAME_BYTES, ROW_BYTES)):
                raise ValueError(f'Nonzero right padding at JIS {row:02X}{cell:02X}')
            codepoint = unicode_for_jis(row, cell)
            if codepoint is None:
                if any(frame):
                    raise ValueError(f'Unmapped nonempty JIS slot {row:02X}{cell:02X}')
                continue
            if not any(frame):
                raise ValueError(f'Unexpected blank Hanzi at JIS {row:02X}{cell:02X}')
            if codepoint in glyphs:
                raise ValueError('Duplicate Unicode mapping')
            glyphs[codepoint] = frame
            mapping.append(f'{row:02X}{cell:02X}:{codepoint:04X}')
    if slots != HAN_SLOTS or len(glyphs) != HAN_GLYPHS:
        raise ValueError('Unexpected Hanzi count or physical layout')
    if sha256(('\n'.join(mapping) + '\n').encode('ascii')) != MAPPING_SHA256:
        raise ValueError('Unexpected Unicode mapping checksum')
    return sorted(glyphs.items())


def make_bdf(glyphs):
    glyphs = sorted(glyphs)
    seen = set()
    for codepoint, frame in glyphs:
        if not isinstance(codepoint, int) or not 0x4E00 <= codepoint <= 0x9FFF:
            raise ValueError('Invalid Hanzi Unicode codepoint')
        if codepoint in seen or len(frame) != FRAME_BYTES:
            raise ValueError('Duplicate codepoint or incorrect 20x20 frame size')
        if any(frame[index] & 0x0F for index in range(2, FRAME_BYTES, ROW_BYTES)):
            raise ValueError('Nonzero right padding in 20x20 frame')
        seen.add(codepoint)
    lines = ['STARTFONT 2.1',
             'COMMENT FM Towns II FreshTV native 20x20 JIS level-1/2 Hanzi only.',
             'COMMENT No symbols, ANK/ASCII, or 16-dot export; no scaling or fallback.',
             'COMMENT Unicode mapping via euc_jp; no guessed extension mappings.',
             'COMMENT Synthetic baseline ascent/descent 20/0; not recovered historic metrics.',
             'COMMENT No redistribution licence for the source ROM has been established.',
             'FONT -fujitsu-fmtowns_f20-medium-r-normal--20-200-72-72-c-200-iso10646-1',
             'SIZE 20 72 72', 'FONTBOUNDINGBOX 20 20 0 0', 'STARTPROPERTIES 6',
             'FONT_ASCENT 20', 'FONT_DESCENT 0', 'RESOLUTION_X 72', 'RESOLUTION_Y 72',
             'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"', 'ENDPROPERTIES',
             f'CHARS {len(glyphs)}']
    for codepoint, frame in glyphs:
        lines.extend([f'STARTCHAR U{codepoint:04X}', f'ENCODING {codepoint}',
                      'SWIDTH 1000 0', 'DWIDTH 20 0', 'BBX 20 20 0 0', 'BITMAP'])
        lines.extend(frame[start:start + ROW_BYTES].hex().upper()
                     for start in range(0, FRAME_BYTES, ROW_BYTES))
        lines.append('ENDCHAR')
    return ('\n'.join(lines + ['ENDFONT', ''])).encode('ascii')


def export(rom_path, output):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Output must be a new directory; existing paths are never overwritten')
    reject_symlinks(output)
    rom = load_rom(rom_path)
    glyphs = extract(rom)
    bdf = make_bdf(glyphs)
    report = {
        'source': {'size': ROM_SIZE, 'sha256': ROM_SHA256},
        'native_frame': [20, 20], 'bytes_per_row': ROW_BYTES,
        'synthetic_ascent_descent': [20, 0], 'resolution_dpi': [72, 72],
        'hanzi_physical_slots': HAN_SLOTS,
        'jis_level_1_2_nonempty_hanzi': len(glyphs),
        'unmapped_blank_hanzi_slots': HAN_SLOTS - len(glyphs),
        'unmapped_nonempty_hanzi_slots': 0, 'right_padding_bits_zero': True,
        'mapping_sha256': MAPPING_SHA256,
        'symbols_exported': False, 'ank_ascii_exported': False, '16_dot_exported': False,
        'file': OUTPUT_NAME, 'sha256': sha256(bdf),
        'unicode_order_row_major_sha256': sha256(b''.join(frame for _, frame in glyphs)),
        'hanzi_physical_slot_row_major_sha256': sha256(rom[0x17288:0x762B0]),
    }
    artifacts = {OUTPUT_NAME: bdf,
                 'export-report.json': (json.dumps(report, indent=2) + '\n').encode('utf-8')}
    # All input/layout checks finish before any output. New directory and
    # exclusive file creation reject conflicts; there is no force option.
    reject_symlinks(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in artifacts.items():
        with (output / name).open('xb') as handle:
            handle.write(data)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', required=True, type=Path, help='local, verified 512 KiB FMT_F20.ROM')
    parser.add_argument('--output', required=True, type=Path, help='new local output directory (must not exist)')
    args = parser.parse_args(argv)
    try:
        report = export(args.rom, args.output)
    except (OSError, ValueError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    print(f'Exported {report["jis_level_1_2_nonempty_hanzi"]} native 20x20 Hanzi to {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
