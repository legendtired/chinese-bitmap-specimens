#!/usr/bin/env python3
"""Export a verified local IBM PC DOS 24x24 font to a local-research BDF.

Offline, standard-library only. Source files are data, never executed.
Preserves every source record and native pixel; no scaling or fallback.
"""
import argparse
import hashlib
import os
from pathlib import Path
import stat
import sys

SECTOR = 512
WIDTH = HEIGHT = 24
STRIDE = 3
FRAME_BYTES = 72
DIRECTORY_BASE = 0xA00
ROOT_START, ROOT_END = 0xBC0, 0xBE0
MAPPING_SHA256 = 'f316706b97fa814d122b49bc146fe88daed4a6830d6d40478fdc75b03b488aaa'
SAFE_DIR_FD = (hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY')
               and os.open in os.supports_dir_fd and os.mkdir in os.supports_dir_fd)
SOURCES = {
    '1cf871b9a37966d779402cb30be9150611ddcf8a7b6598a8e8512ff985eb3fca': {
        'name': 'prckt24', 'style': 'Kai', 'size': 345600, 'records': 7503,
        'unmapped': 59, 'header_name': '楷体',
        'indexed_sha256': '3551f8981910a4e32e6f7ef417d27530d2e75b9fc5ec1784708a27f4542926e1'},
    '6b8a3d637a5a92d84259bdd5265c2021f98c43e51e4154a1907151d54b1eb949': {
        'name': 'prcht24', 'style': 'Hei', 'size': 331776, 'records': 7503,
        'unmapped': 59, 'header_name': '黑体',
        'indexed_sha256': '5bcc457067b55d3160f4282795615eca056a4c5891a50b7bbdc8351f12feaabe'},
    '789fe69db7497e570a9e7a63434a3a20a4f75ed7e67fe23d72916a49608a0771': {
        'name': 'prcfs24', 'style': 'Fangsong', 'size': 340992, 'records': 7472,
        'unmapped': 28, 'header_name': '仿宋体',
        'indexed_sha256': 'e9dbbd82977593858a19abdb25906b713a6e47ee26d7cf762e7d91864c9950bd'},
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def reject_symlinks(path):
    """Reject all symlink components, including dangling final links."""
    for component in (Path(path).absolute(), *Path(path).absolute().parents):
        if component.is_symlink():
            raise ValueError(f'Symbolic links are not accepted: {component}')


def load_font(path):
    """Read a regular file without writes; accept only the three known hashes."""
    path = Path(path)
    reject_symlinks(path)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError as error:
        raise ValueError('Missing FNT file') from error
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('FNT input must be a regular file')
        if info.st_size not in {source['size'] for source in SOURCES.values()}:
            raise ValueError('Unsupported FNT size; expected a verified 24-dot IBM source')
        data = handle.read(max(source['size'] for source in SOURCES.values()) + 1)
    digest = sha256(data)
    source = SOURCES.get(digest)
    if source is None or len(data) != source['size']:
        raise ValueError('SHA-256 mismatch; unsupported or modified FNT file')
    return data, source


def u16(data, offset):
    if not 0 <= offset <= len(data) - 2:
        raise ValueError('Truncated 16-bit field')
    return int.from_bytes(data[offset:offset + 2], 'little')


def prefix_rules(table):
    """Expand the font's lookahead table into a validated prefix code."""
    if len(table) != 264 or table[0] != 0:
        raise ValueError('Invalid Huffman table size or escape entry')
    rules = {}
    for look in range(1, 264):
        value = table[look]
        length, symbol = value >> 4, value & 15
        if look < 256:
            if not 1 <= length <= 8:
                raise ValueError('Invalid Huffman code length')
            key = (length, look >> (8 - length))
        else:
            if not 1 <= length <= 3:
                raise ValueError('Invalid extended Huffman code length')
            key = (8 + length, (look - 256) >> (3 - length))
        if key in rules and rules[key] != symbol:
            raise ValueError('Conflicting Huffman table entries')
        rules[key] = symbol
    if len(rules) != 16 or sorted(rules.values()) != list(range(16)):
        raise ValueError('Huffman table must encode exactly 16 distinct nibbles')
    for length, code in rules:
        if any((short, code >> (length - short)) in rules for short in range(1, length)):
            raise ValueError('Huffman codes are not prefix-free')
    if sum(1 << (11 - length) for length, _ in rules) != 1 << 11:
        raise ValueError('Incomplete Huffman code')
    return rules


def decode_payload(payload, rules, predictor):
    """Decode 144 residual nibbles and apply two-row nibble prediction."""
    if not payload or len(payload) > 216 or len(predictor) != 2048:
        raise ValueError('Invalid payload or predictor size')
    raw, bitpos = bytearray(FRAME_BYTES), 0
    for nibble_index in range(FRAME_BYTES * 2):
        code = 0
        for length in range(1, 12):
            if bitpos >= len(payload) * 8:
                raise ValueError('Truncated glyph payload')
            code = (code << 1) | ((payload[bitpos // 8] >> (7 - bitpos % 8)) & 1)
            bitpos += 1
            if (length, code) in rules:
                rank = rules[length, code]
                break
        else:
            raise ValueError('Invalid glyph Huffman prefix')
        index, shift = nibble_index // 2, 4 if nibble_index % 2 == 0 else 0
        prev1 = (raw[index - STRIDE] >> shift) & 15 if index >= STRIDE else 0
        prev2 = (raw[index - 2 * STRIDE] >> shift) & 15 if index >= 2 * STRIDE else 0
        lookup = (prev2 << 8) | (prev1 << 4) | rank
        pair = predictor[lookup // 2]
        value = pair & 15 if lookup % 2 else pair >> 4
        raw[index] |= value << shift
    if len(payload) * 8 - bitpos >= 8:
        raise ValueError('Unused complete bytes in glyph payload')
    return bytes(raw)


def decode_font(data):
    """Low-level bounded parser, also usable with invented test fixtures.

    Public export always calls load_font first. No unchecked/force CLI exists.
    """
    if len(data) < 0x1C00 or len(data) % SECTOR:
        raise ValueError('Invalid FNT size or truncated sector')
    if data[:16] != b'System DBCS 24  ':
        raise ValueError('Unexpected System DBCS 24 header')
    if (u16(data, 16), u16(data, 18), u16(data, 20), u16(data, 22),
            u16(data, 24), u16(data, 28)) != (1381, 24, 24, 1, 72, 1):
        raise ValueError('Unsupported codepage, dimensions, bit depth, or compression')
    rules = prefix_rules(data[0xC0:0x1C8])
    predictor = data[0x200:0xA00]
    for offset in range(0, 2048, 8):
        values = [nibble for value in predictor[offset:offset + 8]
                  for nibble in (value >> 4, value & 15)]
        if sorted(values) != list(range(16)):
            raise ValueError('Predictor context is not a 16-nibble permutation')
    directory_sectors = u16(data, DIRECTORY_BASE + 2)
    start = DIRECTORY_BASE + directory_sectors * SECTOR
    if directory_sectors != 8 or not ROOT_END <= start < len(data):
        raise ValueError('Unsupported directory bounds')
    records, offsets = {}, {}
    last_id = -1
    for sector in range(start, len(data), SECTOR):
        cursor, end = sector, sector + SECTOR
        while cursor + 3 <= end:
            record_id = u16(data, cursor)
            if record_id == 0xFFFF:
                break
            size = data[cursor + 2]
            if not 1 <= size <= 216 or cursor + 3 + size > end:
                raise ValueError('Glyph payload length crosses sector boundary or is invalid')
            if record_id in records:
                raise ValueError('Duplicate IBM record ID')
            if record_id <= last_id:
                raise ValueError('IBM record IDs are not strictly increasing')
            records[record_id] = decode_payload(data[cursor + 3:cursor + 3 + size], rules, predictor)
            offsets[record_id] = cursor
            last_id = record_id
            cursor += 3 + size
        if sector not in offsets.values():
            raise ValueError('Empty data sector or missing first record')
    indexed_sectors = set()
    for cursor in range(DIRECTORY_BASE, start, 4):
        record_id, relative_sector = u16(data, cursor), u16(data, cursor + 2)
        target = DIRECTORY_BASE + relative_sector * SECTOR
        if ROOT_START <= cursor < ROOT_END:
            expected_page = (cursor - ROOT_START) // 4
            if relative_sector != expected_page or not DIRECTORY_BASE <= target < start:
                raise ValueError('Invalid root directory pointer')
            if u16(data, target) != record_id:
                raise ValueError('Root directory does not match leaf page head')
            continue
        if record_id == 0xFFFF:
            continue
        if not start <= target < len(data) or offsets.get(record_id) != target:
            raise ValueError('Leaf directory does not point to first glyph in data sector')
        if target in indexed_sectors:
            raise ValueError('Duplicate leaf directory sector')
        indexed_sectors.add(target)
    if indexed_sectors != set(range(start, len(data), SECTOR)):
        raise ValueError('Leaf directory does not cover every data sector exactly once')
    return records


def gb2312_mapping():
    """Only standard GB2312; IBM codepage 1381 extensions remain unencoded."""
    mapping = {}
    han_ids = set()
    for high in range(0xA1, 0xF8):
        for low in range(0xA1, 0xFF):
            try:
                char = bytes((high, low)).decode('gb2312', errors='strict')
            except UnicodeDecodeError:
                continue
            record_id = 256 + (high - 0x8C) * 94 + low - 0xA1
            if len(char) != 1 or record_id in mapping:
                raise ValueError('Unexpected GB2312 mapping')
            mapping[record_id] = ord(char)
            if high >= 0xB0:
                han_ids.add(record_id)
    serialized = ''.join(f'{idx:04X}:{cp:04X}\n' for idx, cp in sorted(mapping.items()))
    if (len(mapping) != 7445 or len(set(mapping.values())) != 7445 or len(han_ids) != 6763
            or sha256(serialized.encode('ascii')) != MAPPING_SHA256):
        raise ValueError('Unexpected GB2312 mapping checksum or counts')
    return mapping, han_ids


def validate_records(data, records, source, mapping, han_ids):
    if data[0x1E:0x26] != b'01/24/92':
        raise ValueError('Unexpected font header date')
    if data[0x2A:0x42].split(b'\0', 1)[0] != source['header_name'].encode('gb2312'):
        raise ValueError('Unexpected font style name')
    if len(records) != source['records']:
        raise ValueError('Unexpected total record count')
    missing = {mapping[idx] for idx in mapping.keys() - records.keys()}
    if missing != {0x3000} or len(records.keys() & mapping.keys()) != 7444:
        raise ValueError('Unexpected GB2312 coverage; U+3000 must remain absent')
    if not han_ids <= records.keys() or any(not any(records[idx]) for idx in han_ids):
        raise ValueError('Missing or blank GB2312 Hanzi')
    if len(records.keys() - mapping.keys()) != source['unmapped']:
        raise ValueError('Unexpected unmapped IBM record count')
    indexed = b''.join(idx.to_bytes(2, 'little') + records[idx] for idx in sorted(records))
    if sha256(indexed) != source['indexed_sha256']:
        raise ValueError('Decoded native bitmap checksum mismatch')


def make_bdf(records, source_name, mapping=None):
    if source_name not in {source['name'] for source in SOURCES.values()}:
        raise ValueError('Unsupported font name')
    if mapping is None:
        mapping, _ = gb2312_mapping()
    seen = set()
    for record_id, frame in records.items():
        if not isinstance(record_id, int) or not 0 <= record_id < 65535 or len(frame) != FRAME_BYTES:
            raise ValueError('Invalid IBM record ID or 24x24 frame size')
        codepoint = mapping.get(record_id)
        if codepoint is not None:
            if (not isinstance(codepoint, int) or not 0 <= codepoint <= 0x10FFFF
                    or 0xD800 <= codepoint <= 0xDFFF or codepoint in seen):
                raise ValueError('Invalid or duplicate Unicode mapping')
            seen.add(codepoint)
    lines = ['STARTFONT 2.1',
             'COMMENT Native IBM PC DOS 2000 Simplified Chinese 24x24 source pixels.',
             'COMMENT Source header date 01/24/92; not a proven first-release date.',
             'COMMENT Only standard GB2312 is mapped; unknown IBM IDs use ENCODING -1.',
             'COMMENT U+3000 has no source record and is not synthesized.',
             'COMMENT Synthetic baseline ascent/descent 24/0; not recovered historic metrics.',
             'COMMENT No redistribution licence for the source font has been established.',
             f'FONT -ibm-{source_name}-medium-r-normal--24-240-72-72-c-240-iso10646-1',
             'SIZE 24 72 72', 'FONTBOUNDINGBOX 24 24 0 0', 'STARTPROPERTIES 8',
             'FONT_ASCENT 24', 'FONT_DESCENT 0', 'PIXEL_SIZE 24', 'POINT_SIZE 240',
             'RESOLUTION_X 72', 'RESOLUTION_Y 72',
             'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"', 'ENDPROPERTIES',
             f'CHARS {len(records)}']
    for record_id, frame in sorted(records.items()):
        codepoint = mapping.get(record_id)
        name = f'uni{codepoint:04X}' if codepoint is not None else f'IBM{record_id:04X}'
        lines.extend([f'STARTCHAR {name}', f'ENCODING {codepoint if codepoint is not None else -1}',
                      'SWIDTH 1000 0', 'DWIDTH 24 0', 'BBX 24 24 0 0', 'BITMAP'])
        lines.extend(frame[offset:offset + STRIDE].hex().upper()
                     for offset in range(0, FRAME_BYTES, STRIDE))
        lines.append('ENDCHAR')
    return ('\n'.join(lines + ['ENDFONT', ''])).encode('ascii')


def output_path(output):
    output = Path(output).absolute()
    reject_symlinks(output)
    root = Path.cwd() / 'local-research'
    reject_symlinks(root)
    resolved, root = output.resolve(), root.resolve()
    if root not in resolved.parents:
        raise ValueError('Output must be inside local-research under the current working directory')
    if output.suffix.lower() != '.bdf':
        raise ValueError('Output must have a .bdf extension')
    if output.exists() or output.is_symlink():
        raise ValueError('Output must not exist; existing files are never overwritten')
    return resolved


def write_bdf(output, bdf):
    """Keep every creation under cwd using directory-relative no-follow opens."""
    if not SAFE_DIR_FD:
        raise ValueError('Safe output requires POSIX O_NOFOLLOW and dir_fd support')
    output = output_path(output)
    parts = output.relative_to(Path.cwd().resolve()).parts
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open('.', flags)
    created = False
    try:
        for part in parts[:-1]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=parent)
            except FileExistsError:
                pass
            child = os.open(part, flags, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        created = True
        with os.fdopen(fd, 'wb') as handle:
            handle.write(bdf)
    except Exception:
        if created:
            os.unlink(parts[-1], dir_fd=parent)
        raise
    finally:
        os.close(parent)


def export(font_path, output):
    output = output_path(output)
    if Path(font_path).resolve() == output:
        raise ValueError('Output cannot overwrite the input font')
    data, source = load_font(font_path)
    records = decode_font(data)
    mapping, han_ids = gb2312_mapping()
    validate_records(data, records, source, mapping, han_ids)
    bdf = make_bdf(records, source['name'], mapping)
    # Complete all parsing, coverage and bitmap checks before creating anything.
    write_bdf(output, bdf)
    return {'font': source['name'], 'records': len(records), 'mapped_gb2312': 7444,
            'hanzi': len(han_ids), 'unmapped': source['unmapped'],
            'native_dimensions': [24, 24], 'synthetic_ascent_descent': [24, 0],
            'source_sha256': sha256(data), 'bdf_sha256': sha256(bdf),
            'indexed_bitmap_sha256': source['indexed_sha256']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', required=True, type=Path,
                        help='local verified prckt24.FNT, prcht24.FNT or prcfs24.FNT')
    parser.add_argument('--output', required=True, type=Path,
                        help='new .bdf inside ./local-research (never overwrites)')
    args = parser.parse_args(argv)
    try:
        report = export(args.font, args.output)
    except (OSError, ValueError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    print(f'Exported {report["records"]} native 24x24 records: 7444 standard GB2312 mappings, '
          f'6763 Hanzi, {report["unmapped"]} unencoded IBM records. U+3000 remains absent.')
    print(f'BDF SHA-256: {report["bdf_sha256"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
