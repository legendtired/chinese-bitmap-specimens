#!/usr/bin/env python3
"""Export the verified Panasonic FS-UV1 / FS-A1F 16px ROM to Unicode BDF.

Supply your own lawfully obtained ROM. No font data is embedded, no network is
used, and no right to redistribute the ROM or exported font is implied.
Default: 2,966 mapped Han. --include-symbols adds provisional EUC-JP mappings.
Python 3.9+ standard library only. Existing outputs are never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

EXPECTED_SIZE = 131072
EXPECTED_SHA256 = 'e4036415638e73d5894d850cab3a40cb63e76afa0391d0ad31321bf2ed61b7d7'


def slot_for(ku, ten):
    """JIS row/cell (one-based) to the physical 32-byte slot."""
    if not (1 <= ku <= 47 and 1 <= ten <= 94):
        raise ValueError('Only audited JIS rows 1-47 and cells 1-94 are supported.')
    return ku * 96 + ten - (512 if ku >= 16 else 0)


def decode_slot(data, slot):
    """Four 8x8 tiles: upper left, upper right, lower left, lower right."""
    if not 0 <= slot < 4096:
        raise ValueError('Slot outside the 128 KiB ROM.')
    start = slot * 32
    raw = data[start:start + 32]
    if len(raw) != 32:
        raise ValueError('Truncated glyph slot.')
    return [raw[(y // 8) * 16 + y % 8] * 256 +
            raw[(y // 8) * 16 + 8 + y % 8] for y in range(16)]


def recover(data, include_symbols=False):
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != EXPECTED_SIZE or digest != EXPECTED_SHA256:
        raise ValueError('Input does not match the verified 131072-byte ROM. '
                         'Refusing unverified offsets or a different dump. SHA256: ' + digest)
    glyphs = []
    for ku in range(1, 48):
        for ten in range(1, 95):
            slot = slot_for(ku, ten)
            if slot >= 4096:
                continue
            code = bytes((ku + 0xA0, ten + 0xA0))
            try:
                char = code.decode('euc_jp', errors='strict')
            except UnicodeDecodeError:
                continue
            if len(char) != 1 or char.encode('euc_jp') != code:
                raise ValueError('Non-round-trip mapping at JIS %d-%d.' % (ku, ten))
            han = 0x3400 <= ord(char) <= 0x9FFF
            if not han and not include_symbols:
                continue
            glyphs.append({'unicode': ord(char), 'ku': ku, 'ten': ten,
                           'slot': slot, 'han': han, 'rows': decode_slot(data, slot)})
    expected = 3489 if include_symbols else 2966
    if len(glyphs) != expected or len({g['unicode'] for g in glyphs}) != expected:
        raise ValueError('Unexpected mapping count; check the Python EUC-JP codec.')
    if sum(g['han'] for g in glyphs) != 2966 or any(g['han'] and not any(g['rows']) for g in glyphs):
        raise ValueError('Unexpected Han coverage or empty Han glyph.')
    if include_symbols and sum(not any(g['rows']) for g in glyphs) != 15:
        raise ValueError('Unexpected blank symbol slots.')
    return glyphs


def bdf_text(glyphs, include_symbols=False):
    lines = ['STARTFONT 2.1',
             'COMMENT Source: separately supplied Panasonic FS-UV1 / FS-A1F ROM.',
             'COMMENT Source SHA256 ' + EXPECTED_SHA256,
             'COMMENT Rights undetermined; local export does not authorize redistribution.',
             'COMMENT Han: 2965 JIS level-1 characters plus U+4EDD.',
             'COMMENT Historical glyph variants were not individually authenticated.',
             'COMMENT Baseline at cell bottom is an export convention, not source metadata.']
    if include_symbols:
        lines.append('COMMENT Symbols use provisional modern EUC-JP mapping, including 15 blank slots.')
    lines += ['FONT -Recovered-FSUV1-Medium-R-Normal--16-160-75-75-C-160-ISO10646-1',
              'SIZE 16 75 75', 'FONTBOUNDINGBOX 16 16 0 0',
              'STARTPROPERTIES 4', 'FONT_ASCENT 16', 'FONT_DESCENT 0',
              'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"', 'ENDPROPERTIES',
              'CHARS ' + str(len(glyphs))]
    for glyph in glyphs:
        lines += [f"STARTCHAR uni{glyph['unicode']:04X}",
                  f"COMMENT JIS {glyph['ku']}-{glyph['ten']}; physical slot {glyph['slot']}",
                  'ENCODING ' + str(glyph['unicode']), 'SWIDTH 1000 0', 'DWIDTH 16 0',
                  'BBX 16 16 0 0', 'BITMAP']
        lines += [f'{row:04X}' for row in glyph['rows']]
        lines.append('ENDCHAR')
    return '\n'.join(lines + ['ENDFONT', ''])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path, help='Separately obtained fs-a1f_kanjifont.rom')
    parser.add_argument('output', type=Path, help='New .bdf output path; never overwritten')
    parser.add_argument('--include-symbols', action='store_true',
                        help='Include provisional modern EUC-JP symbol mappings (3489 total, 15 blank)')
    parser.add_argument('--report', type=Path, help='Optional new JSON summary path; no glyph data')
    args = parser.parse_args()
    if args.output.suffix.lower() != '.bdf':
        parser.error('Output must use the .bdf extension.')
    if args.report and args.report.resolve() == args.output.resolve():
        parser.error('BDF and report paths must differ.')
    for path in [args.output] + ([args.report] if args.report else []):
        if path.exists():
            parser.error('Output already exists; choose a new filename: ' + str(path))
        if not path.parent.is_dir():
            parser.error('Output folder does not exist: ' + str(path.parent))
    try:
        glyphs = recover(args.rom.read_bytes(), args.include_symbols)
        output = bdf_text(glyphs, args.include_symbols)
        with args.output.open('x', encoding='ascii', newline='\n') as stream:
            stream.write(output)
        if args.report:
            report = {'sourceSha256': EXPECTED_SHA256, 'cell': [16, 16],
                      'glyphs': len(glyphs), 'han': 2966,
                      'nonempty': sum(bool(any(g['rows'])) for g in glyphs),
                      'blankUnicode': [f"U+{g['unicode']:04X}" for g in glyphs if not any(g['rows'])],
                      'mapping': 'modern EUC-JP; Han slots verified; symbol identities provisional' if args.include_symbols else 'JIS level-1 Han plus U+4EDD',
                      'asciiIncluded': False,
                      'outputSha256': hashlib.sha256(output.encode('ascii')).hexdigest()}
            with args.report.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
    except (OSError, ValueError) as error:
        sys.exit(str(error))
    print(f'Wrote {len(glyphs)} Unicode-mapped 16x16 glyphs to {args.output}.')
    if args.include_symbols:
        print('Warning: non-Han mappings are provisional; 15 mapped symbol slots are blank.')
    print('No halfwidth ASCII is exported. This does not grant redistribution rights.')


if __name__ == '__main__':
    main()
