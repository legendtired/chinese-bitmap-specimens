#!/usr/bin/env python3
"""Export native Sharp X68000 16x16 JIS glyphs from a verified local CGROM.
Offline and standard-library only. The ROM is data, never executed.
No ANK/ASCII, 24-dot output, resampling, substitutions, or fallback.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROM_SIZE = 786432
ROM_SHA256 = 'c4e47e1480af0b00b330a49650480c8caa34054a6e97db7ae03cbade9890185d'
ROW_GROUPS = ((0x21, 0x28), (0x30, 0x4F), (0x50, 0x74))
SLOTS = 7238
FRAME_BYTES = 32
BLANK_CODES = {(0x21, 0x21): 0x3000, (0x74, 0x25): 0x51DC, (0x74, 0x26): 0x7199}
MAPPING_SHA256 = '122b348f9bf155c42cb2ecdc215b01f447cb53a64508744223fee29ddcb19f06'
OUTPUT_NAME = 'sharp-x68000-16x16.bdf'


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
    # O_NOFOLLOW protects the final input component against replacement after
    # the check. O_NONBLOCK avoids blocking on a FIFO before fstat rejects it.
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
        raise ValueError('SHA-256 mismatch; unsupported or modified CGROM')
    return rom


def slot_index(row, cell):
    if not any(first <= row <= last for first, last in ROW_GROUPS) or not 0x21 <= cell <= 0x7E:
        raise ValueError('JIS row or cell outside the supported physical groups')
    group_row = row - 0x21 if row < 0x30 else row - 0x30 + 8
    return group_row * 94 + cell - 0x21


def unicode_for_jis(row, cell):
    slot_index(row, cell)
    try:
        character = bytes((row + 0x80, cell + 0x80)).decode('euc_jp')
    except UnicodeDecodeError:
        return None
    if len(character) != 1:
        raise ValueError('Unexpected multicharacter JIS mapping')
    return ord(character)


def extract(rom):
    """Return Unicode-sorted (codepoint, row-major frame) pairs.

    This low-level parser also accepts synthetic test data; the public export
    path always calls load_rom first and requires the exact known source hash.
    """
    if len(rom) != ROM_SIZE:
        raise ValueError('Incorrect ROM size')
    glyphs, blank_codes, mapping = {}, {}, []
    sequential, han = 0, 0
    for first, last in ROW_GROUPS:
        for row in range(first, last + 1):
            for cell in range(0x21, 0x7F):
                index = slot_index(row, cell)
                if index != sequential:
                    raise ValueError('Physical slot order mismatch')
                sequential += 1
                frame = rom[index * FRAME_BYTES:(index + 1) * FRAME_BYTES]
                codepoint = unicode_for_jis(row, cell)
                if codepoint is None:
                    if any(frame):
                        raise ValueError(f'Unmapped nonempty JIS slot {row:02X}{cell:02X}')
                    continue
                if not any(frame):
                    blank_codes[(row, cell)] = codepoint
                    if codepoint != 0x3000:
                        continue
                if codepoint in glyphs:
                    raise ValueError('Duplicate Unicode mapping')
                glyphs[codepoint] = frame
                mapping.append(f'{row:02X}{cell:02X}:{codepoint:04X}')
                if row >= 0x30:
                    han += 1
    if blank_codes != BLANK_CODES:
        raise ValueError('Unexpected blank/nonblank JIS slots')
    if sequential != SLOTS or len(glyphs) != 6877 or han != 6353:
        raise ValueError('Unexpected glyph count or physical layout')
    if sha256(('\n'.join(mapping) + '\n').encode('ascii')) != MAPPING_SHA256:
        raise ValueError('Unexpected Unicode mapping checksum')
    return sorted(glyphs.items())


def make_bdf(glyphs):
    glyphs = sorted(glyphs)
    seen = set()
    for codepoint, frame in glyphs:
        if not isinstance(codepoint, int) or not 0 <= codepoint <= 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
            raise ValueError('Invalid Unicode codepoint')
        if codepoint in seen or len(frame) != FRAME_BYTES:
            raise ValueError('Duplicate codepoint or incorrect 16x16 frame size')
        seen.add(codepoint)
    lines = ['STARTFONT 2.1',
             'COMMENT Sharp X68000 native 16x16 JIS glyphs; no ANK or 24-dot export.',
             'COMMENT Unicode mapping via euc_jp; no scaling, substitutions, or fallback.',
             'COMMENT Synthetic baseline ascent/descent 16/0; not recovered historic metrics.',
             'COMMENT No redistribution licence for the source CGROM has been established.',
             'FONT -sharp-x68000-medium-r-normal--16-160-72-72-c-160-iso10646-1',
             'SIZE 16 72 72', 'FONTBOUNDINGBOX 16 16 0 0', 'STARTPROPERTIES 6',
             'FONT_ASCENT 16', 'FONT_DESCENT 0', 'RESOLUTION_X 72', 'RESOLUTION_Y 72',
             'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"', 'ENDPROPERTIES',
             f'CHARS {len(glyphs)}']
    for codepoint, frame in glyphs:
        lines.extend([f'STARTCHAR U{codepoint:04X}', f'ENCODING {codepoint}',
                      'SWIDTH 1000 0', 'DWIDTH 16 0', 'BBX 16 16 0 0', 'BITMAP'])
        lines.extend(frame[start:start + 2].hex().upper() for start in range(0, FRAME_BYTES, 2))
        lines.append('ENDCHAR')
    return ('\n'.join(lines + ['ENDFONT', ''])).encode('ascii')


def export(rom_path, output):
    output = Path(output)
    # Reject existing directories, files, and links before reading the input.
    if output.exists() or output.is_symlink():
        raise ValueError('Output must be a new directory; existing paths are never overwritten')
    reject_symlinks(output)
    rom = load_rom(rom_path)
    glyphs = extract(rom)
    bdf = make_bdf(glyphs)
    report = {
        'source': {'size': ROM_SIZE, 'sha256': ROM_SHA256},
        'native_frame': [16, 16], 'synthetic_ascent_descent': [16, 0],
        'physical_slots': SLOTS, 'mapped_glyphs_including_ideographic_space': len(glyphs),
        'nonempty_mapped_glyphs': 6876, 'jis_level_1_2_nonempty_hanzi': 6353,
        'unmapped_nonempty_slots': 0, 'mapping_sha256': MAPPING_SHA256,
        'excluded_blank_jis_codes': ['7425', '7426'],
        'excluded_blank_unicode': ['U+51DC', 'U+7199'],
        'ank_ascii_exported': False, '24_dot_exported': False,
        'file': OUTPUT_NAME, 'sha256': sha256(bdf),
        'unicode_order_row_major_sha256': sha256(b''.join(frame for _, frame in glyphs)),
        'all_physical_slot_row_major_sha256': sha256(rom[:SLOTS * FRAME_BYTES]),
    }
    artifacts = {OUTPUT_NAME: bdf,
                 'export-report.json': (json.dumps(report, indent=2) + '\n').encode('utf-8')}
    # All input/layout checks finish before creating any output. Both mkdir and
    # exclusive file creation reject conflicts; there is no --force escape hatch.
    reject_symlinks(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in artifacts.items():
        with (output / name).open('xb') as handle:
            handle.write(data)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', required=True, type=Path, help='local, verified 768 KiB CGROM file')
    parser.add_argument('--output', required=True, type=Path, help='new local output directory (must not exist)')
    args = parser.parse_args(argv)
    try:
        report = export(args.rom, args.output)
    except (OSError, ValueError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    print(f'Exported {report["mapped_glyphs_including_ideographic_space"]} native 16x16 glyphs '
          f'(6353 Hanzi) to {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
