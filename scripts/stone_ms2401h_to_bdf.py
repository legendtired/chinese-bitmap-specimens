#!/usr/bin/env python3
"""Export four native 32x32 Stone MS-2401H Hanzi sets from user-supplied ROMs.
Offline, standard-library only. ROMs are read as data, never executed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

SOURCES = {
    'ALPS_BIOS-ST-M27C256B.BIN': (32768, 'cda234a6616968391b58a492a863f4cbd00bc84ee748fea977c5f1db5978de28'),
    'CA1-FC-MB834000A.BIN': (524288, 'ad4d1643edcab0fdf2499cb8efe573eab046b6784a38f92067bf5b6d34a4a170'),
    'CA2-FC-MB838000-20P.BIN': (1048576, '5b15ade423aba5167309c0fbc4cae803a6b16c4462e56f0589325feee1fba8f5'),
    'CA3-FC-MB838000-20P.BIN': (1048576, 'fb3fecc8cca6e6a5c20d18d9db5d1e745c24b74fd3ef305c99efbce28f88dc2d'),
}
LAYOUT = {1: (0x17F380, 0x185D40, 0x21CC71), 2: (0x1031E0, 0x109BA0, 0x17F367),
          3: (0x21CC90, 0x223650, 0x2AB71C), 4: (0x080000, 0x0869C0, 0x1031C1)}
FRAME_HASHES = {
    1: '7be69d680d3e902e79a012509a1c833fb421c8f756aaf875538366989772fbba',
    2: 'fdf6e45ccfe66bdc7940404ccd90edb84f1eaa0473ab79dd12805aaa70f87423',
    3: 'd9c8609674f763a570153e01596e09d118d689e1e78d817e3682dc5e0699c8eb',
    4: '6071fa0a1ad795a3f2aa9b8d945f09f62f0bddad1465e28bfbfb0e2a7aca1d21',
}
SLOTS = 6768
GAPS = set(range(3755, 3760))  # GB2312 D7FA-D7FE, unassigned


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_sources(directory):
    result = {}
    for name, (size, expected) in SOURCES.items():
        path = directory / name
        if not path.is_file() or path.stat().st_size != size:
            raise ValueError(f'{name}: missing file or incorrect size (expected {size} bytes)')
        data = path.read_bytes()
        if len(data) != size or sha256(data) != expected:
            raise ValueError(f'{name}: SHA-256 mismatch; unsupported ROM revision')
        result[name] = data
    return result


def decode(payload, lookup):
    """BIOS MSB-first rank coding; zero-initialized 128-byte strip frame."""
    if len(lookup) != 256:
        raise ValueError('Lookup must contain exactly 256 bytes')
    cursor, rank, total = 0, 0, len(payload) * 8
    result = bytearray()

    def take(count):
        nonlocal cursor
        value = 0
        for _ in range(count):
            value = (value << 1) | ((payload[cursor // 8] >> (7 - cursor % 8)) & 1)
            cursor += 1
        return value

    while cursor < total:
        if take(1):
            if total - cursor < 3:
                break
            count = take(3) + 1
            if total - cursor < count:
                break
            rank = take(count)
        result.append(lookup[rank])
    if any(result[128:]):
        raise ValueError('Nonzero decompression overrun past 128-byte frame')
    return bytes(result[:128]).ljust(128, b'\x00')


def row_major(frame):
    if len(frame) != 128:
        raise ValueError('Expected a 128-byte native frame')
    return bytes(frame[column * 32 + row] for row in range(32) for column in range(4))


def unicode_for_slot(index):
    if not 0 <= index < SLOTS:
        raise ValueError('Hanzi slot index out of range')
    code = bytes((0xB0 + index // 94, 0xA1 + index % 94))
    if index in GAPS:
        return None
    return ord(code.decode('gb2312'))


def extract(sources, style):
    if style not in LAYOUT:
        raise ValueError('Supported styles are 1, 2, 3, 4')
    bios = sources['ALPS_BIOS-ST-M27C256B.BIN']
    rom = b'\x00' * 0x80000 + b''.join(sources[name] for name in list(SOURCES)[1:])
    desc = bios[0x59A6 + style * 7:0x59AD + style * 7]
    table = (desc[0] << 20) + (int.from_bytes(desc[5:7], 'little') << 4)
    base = (desc[0] << 20) + (int.from_bytes(desc[1:3], 'little') << 4)
    expected_table, expected_base, end = LAYOUT[style]
    if (table, base) != (expected_table, expected_base) or table + SLOTS * 4 != base:
        raise ValueError('Unexpected descriptor/table layout')
    lookup = bios[0x59C9 + style * 256:0x59C9 + (style + 1) * 256]
    frames, previous = [], base
    for index in range(SLOTS):
        record = rom[table + index * 4:table + index * 4 + 4]
        address = base + (int.from_bytes(record[:2], 'little') << 4) + record[2]
        length = record[3]
        if address != previous or not length or address + length > end:
            raise ValueError(f'Invalid payload bounds or continuity at slot {index}')
        frame = row_major(decode(rom[address:address + length], lookup))
        if (not any(frame)) != (index in GAPS):
            raise ValueError(f'Unexpected blank/nonblank slot {index}')
        frames.append(frame)
        previous = address + length
    if previous != end or sha256(b''.join(frames)) != FRAME_HASHES[style]:
        raise ValueError('Decoded frame checksum or data boundary mismatch')
    return [(unicode_for_slot(i), frame) for i, frame in enumerate(frames) if i not in GAPS]


def extract_symbols(sources):
    """BIOS 0x5731-0x574c selects shared style 0 for GB rows A1-AB.
    Only standard GB2312 rows A1-A9 are exported; extended western sets stay out.
    """
    bios = sources['ALPS_BIOS-ST-M27C256B.BIN']
    rom = b'\x00' * 0x80000 + b''.join(sources[name] for name in list(SOURCES)[1:])
    desc = bios[0x59A6:0x59AD]
    table = (desc[0] << 20) + (int.from_bytes(desc[5:7], 'little') << 4)
    base = (desc[0] << 20) + (int.from_bytes(desc[1:3], 'little') << 4)
    if (table, base) != (0x2AB730, 0x2AD320):
        raise ValueError('Unexpected shared-symbol descriptor')
    lookup = bios[0x59C9:0x5AC9]
    frames, glyphs, previous = [], [], base
    for index in range(9 * 94):
        record = rom[table + index * 4:table + index * 4 + 4]
        address = base + (int.from_bytes(record[:2], 'little') << 4) + record[2]
        length = record[3]
        if address != previous or not length or address + length > 0x2B493D:
            raise ValueError(f'Invalid symbol bounds at slot {index}')
        frame = row_major(decode(rom[address:address + length], lookup))
        frames.append(frame)
        previous = address + length
        try:
            char = bytes((0xA1 + index // 94, 0xA1 + index % 94)).decode('gb2312')
        except UnicodeDecodeError:
            continue
        if (not any(frame)) != (char == '\u3000'):
            raise ValueError(f'Unexpected blank symbol at slot {index}')
        glyphs.append((ord(char), frame))
    if (previous != 0x2B493D or len(glyphs) != 682 or
            sha256(b''.join(frames)) != 'aacb9dd89d63e22ae131c1e6218bdefb39bc08968139fba63c463ae2a979f69a'):
        raise ValueError('Shared-symbol checksum or mapping mismatch')
    return glyphs


def make_bdf(style, glyphs, include_symbols=False):
    scope = 'Hanzi + shared GB2312 symbols; fullwidth Latin, not ASCII' if include_symbols else 'Hanzi only'
    lines = ['STARTFONT 2.1', f'COMMENT Stone MS-2401H numeric style {style}; native 32x32 {scope}.',
             'COMMENT Unicode mapping via GB2312; no scaling or substituted glyphs.',
             'COMMENT Synthetic baseline ascent/descent 32/0; not recovered historic metrics.',
             f'FONT -stone-ms2401h_style{style}-medium-r-normal--32-320-72-72-c-320-iso10646-1',
             'SIZE 32 72 72', 'FONTBOUNDINGBOX 32 32 0 0', 'STARTPROPERTIES 6',
             'FONT_ASCENT 32', 'FONT_DESCENT 0', 'RESOLUTION_X 72', 'RESOLUTION_Y 72', 'CHARSET_REGISTRY "ISO10646"',
             'CHARSET_ENCODING "1"', 'ENDPROPERTIES', f'CHARS {len(glyphs)}']
    for codepoint, frame in glyphs:
        lines.extend([f'STARTCHAR U{codepoint:04X}', f'ENCODING {codepoint}',
                      'SWIDTH 1000 0', 'DWIDTH 32 0', 'BBX 32 32 0 0', 'BITMAP'])
        lines.extend(frame[j:j + 4].hex().upper() for j in range(0, 128, 4))
        lines.append('ENDCHAR')
    return '\n'.join(lines + ['ENDFONT', '']).encode('ascii')


def export(rom_dir, output, include_symbols=False):
    # Require a new directory. This also rejects existing files and dangling symlinks.
    if output.exists() or output.is_symlink():
        raise ValueError('Output must be a new directory; existing paths are never overwritten')
    sources = load_sources(rom_dir)
    artifacts, reports = {}, []
    symbols = extract_symbols(sources) if include_symbols else []
    for style in range(1, 5):
        glyphs = extract(sources, style) + symbols
        suffix = '-gb-symbols' if include_symbols else ''
        name = f'stone-ms2401h-style-{style}-32x32{suffix}.bdf'
        artifacts[name] = make_bdf(style, glyphs, include_symbols)
        reports.append({'style': style, 'file': name, 'glyphs': len(glyphs),
                        'sha256': sha256(artifacts[name]), 'all_slot_row_major_sha256': FRAME_HASHES[style]})
    report = {'sources': {name: {'size': size, 'sha256': digest} for name, (size, digest) in SOURCES.items()},
              'included_gb_symbols': len(symbols), 'ordinary_ascii': 0,
              'native_frame': [32, 32], 'synthetic_ascent_descent': [32, 0],
              'excluded_gb_slots': ['D7FA', 'D7FB', 'D7FC', 'D7FD', 'D7FE'], 'styles': reports}
    artifacts['export-report.json'] = (json.dumps(report, indent=2) + '\n').encode('utf-8')
    # Validation finishes before any directory or output is created. mkdir and xb
    # reject conflicts, including a concurrent invocation; no --force escape hatch.
    output.mkdir(parents=True, exist_ok=False)
    for name, data in artifacts.items():
        with (output / name).open('xb') as handle:
            handle.write(data)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom-dir', required=True, type=Path, help='directory containing four verified ROM files')
    parser.add_argument('--output', required=True, type=Path, help='new local output directory (must not exist)')
    parser.add_argument('--include-symbols', action='store_true', help='include 682 original GB2312 symbols and fullwidth Latin; not ordinary ASCII')
    args = parser.parse_args(argv)
    try:
        report = export(args.rom_dir, args.output, args.include_symbols)
    except (OSError, ValueError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    print(f'Exported {len(report["styles"])} BDF files, 6763 Hanzi + {report["included_gb_symbols"]} symbols each, to {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
