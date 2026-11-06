#!/usr/bin/env python3
"""Offline Sunplus SPHE8202L simplified GB2312 bitmap extraction.

Standard library only, no embedded font data, network, or firmware execution.
Supports only the three approved CP936 uncompressed objects, not CP950.
12x12 is a technical source comparison: all 7445 standard GB2312 glyphs match
the existing HZK12 entry. Only 16x16 and 20x24 are new catalog specimens.
Default output is fixed PNG specimens and aggregate metadata. Optional BDFs
are for local use only; this tool grants no font redistribution rights.
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

ARCHIVE_SIZE = 13305912
ARCHIVE_SHA256 = 'bbf28d191a165c8540f34c66ea6839fa395bcdfd2825e6342f1a4eff7210a5df'
SLOTS = 7614
MAPPING_SHA256 = '34e0e683935693242385c15945497ec2624afc4033ad1d86938d16e1465843a9'
PHRASE = '视野无限广，窗外有蓝天。'
EXTRA = '片版牌局'
VARIANTS = {
    '12x12': {'width': 12, 'height': 12, 'object_size': 139649,
             'object_sha256': 'cae41b8c3cc568a92dd40b16e21e1de0d06af7f2a1839bd37845b059f6b9b151',
             'payload_sha256': 'e6135cbfde217794148394c379699f9795dc9d9cae6d14e43be57442a8a7e61a'},
    '16x16': {'width': 16, 'height': 16, 'object_size': 246245,
             'object_sha256': 'ccde5faca1424eeb8b6c32d6d33142910146fa8952e134c22beaffa0df84eae2',
             'payload_sha256': '1f0ad632938ced219964358f11aa78fed84da5578eca4383182289ec724f32a8'},
    '20x24': {'width': 20, 'height': 24, 'object_size': 459437,
             'object_sha256': '26c367d39cf2d0eb39d926337b453ac87400f37b3c58d001efdd518d8da3db2e',
             'payload_sha256': '3092173e88303e04a9c29c9f3deb4212557beeba8de63f0ee603f5b4e25103e4'},
}
for _size, _info in VARIANTS.items():
    _info['symbol'] = f'FontBmp_FONT_CP_936_FONT_SIZE_{_size}_FONT_NOT_COMPRESSED'
    _info['member'] = _info['symbol'] + '.o'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def reject_symlinks(path):
    p = Path(path).absolute()
    for part in (p, *p.parents):
        require(not part.is_symlink(), 'Symbolic links are not accepted')


def validate_source(data):
    require(len(data) == ARCHIVE_SIZE and sha256(data) == ARCHIVE_SHA256,
            'Unsupported libfont.a: complete archive size/SHA-256 mismatch')


def read_source(path):
    path = Path(path)
    reject_symlinks(path)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    with os.fdopen(os.open(path, flags), 'rb') as handle:
        info = os.fstat(handle.fileno())
        require(stat.S_ISREG(info.st_mode), 'Input must be a regular archive file')
        require(info.st_size == ARCHIVE_SIZE, 'Expected complete 13305912-byte libfont.a')
        data = handle.read(ARCHIVE_SIZE + 1)
    validate_source(data)
    return data


def parse_ar(data):
    """Parse GNU/SysV ar, including its long-name table; never extract files."""
    require(data[:8] == b'!<arch>\n', 'Invalid ar signature')
    pos, names, result = 8, None, {}
    while pos < len(data):
        require(pos + 60 <= len(data), 'Truncated ar header')
        header = data[pos:pos + 60]
        require(header[58:60] == b'`\n', 'Invalid ar member header')
        number = header[48:58].strip()
        require(bool(number) and number.isdigit(), 'Invalid ar member size')
        size = int(number)
        start, end = pos + 60, pos + 60 + size
        require(end <= len(data), 'ar member exceeds archive')
        name = header[:16].decode('ascii').rstrip()
        body = data[start:end]
        if name == '//':
            require(names is None, 'Duplicate ar name table')
            names = body
        elif name not in ('/', '/SYM64/'):
            if name.startswith('/'):
                require(name[1:].isdigit() and names is not None, 'Unsupported ar name reference')
                index = int(name[1:])
                require(0 <= index < len(names) and (index == 0 or names[index - 1:index] == b'\n'),
                        'ar name reference is not a table-entry boundary')
                stop = names.find(b'/\n', index)
                require(stop >= 0, 'Unterminated ar long name')
                name = names[index:stop].decode('ascii')
            else:
                require(name.endswith('/'), 'Unsupported ar name format')
                name = name[:-1]
            require(name and Path(name).name == name and '\\' not in name and name not in ('.', '..'),
                    'Invalid ar filename')
            require(name not in result, 'Duplicate ar member')
            result[name] = body
        if size & 1:
            require(end < len(data) and data[end:end + 1] == b'\n', 'Missing ar alignment byte')
        pos = end + (size & 1)
    require(pos == len(data), 'ar trailing data')
    return result


def cstring(data, offset):
    require(0 <= offset < len(data), 'String offset outside table')
    end = data.find(b'\0', offset)
    require(end >= 0, 'Unterminated ELF string')
    return data[offset:end].decode('ascii')


def elf_payload(data, symbol_name):
    """Locate the exact symbol extent, excluding .rodata alignment bytes."""
    require(len(data) >= 52 and data[:7] == b'\x7fELF\x01\x01\x01', 'Expected ELF32 little-endian')
    require(struct.unpack_from('<HHI', data, 16) == (1, 8, 1), 'Expected relocatable MIPS ELF')
    shoff = struct.unpack_from('<I', data, 32)[0]
    ehsize, phsize, phnum, shsize, shnum, shstr = struct.unpack_from('<6H', data, 40)
    require(ehsize == 52 and phnum == 0 and shsize == 40 and shnum > 0 and shstr < shnum,
            'Unsupported ELF header/table layout')
    require(shoff >= 52 and shoff + shsize * shnum <= len(data), 'ELF section table exceeds object')
    sections = [struct.unpack_from('<10I', data, shoff + i * 40) for i in range(shnum)]
    for section in sections:
        if section[1] != 8:  # SHT_NOBITS has no file payload.
            require(section[4] + section[5] <= len(data), 'ELF section exceeds object')
    st = sections[shstr]
    require(st[1] == 3, 'Missing ELF section-name string table')
    section_names = data[st[4]:st[4] + st[5]]
    names = [cstring(section_names, s[0]) for s in sections]
    require(names.count('.rodata') == 1, 'Expected one .rodata section')
    target_index = names.index('.rodata')
    target = sections[target_index]
    require(target[1] == 1, '.rodata is not PROGBITS')
    found = []
    for table in sections:
        if table[1] != 2:
            continue
        require(table[9] == 16 and table[5] % 16 == 0 and table[6] < shnum, 'Invalid ELF symbol table')
        strings = sections[table[6]]
        require(strings[1] == 3, 'Invalid ELF symbol string table')
        string_data = data[strings[4]:strings[4] + strings[5]]
        for pos in range(table[4], table[4] + table[5], 16):
            n, value, size, info, other, index = struct.unpack_from('<IIIBBH', data, pos)
            if cstring(string_data, n) != symbol_name:
                continue
            require(index == target_index and info == 0x11, 'Expected global OBJECT in .rodata')
            require(value == 0 and 0 < size <= target[5], 'Unexpected font symbol extent')
            require(0 <= target[5] - size <= 3, 'Unexpected data after font symbol')
            begin = target[4] + value
            require(data[begin + size:target[4] + target[5]] == bytes(target[5] - size),
                    'Nonzero bytes after font symbol')
            found.append(data[begin:begin + size])
    require(len(found) == 1, 'Expected exactly one matching font symbol')
    return found[0]


def slot_index(lead, trail):
    if not 0xA1 <= trail <= 0xFE:
        return None
    if 0xA1 <= lead <= 0xA9:
        return (lead - 0xA1) * 94 + trail - 0xA1
    if 0xB0 <= lead <= 0xF7:
        return (lead - 0xB0 + 9) * 94 + trail - 0xA1
    return None


def mapping():
    """Label original GB2312 source slots, not the runtime Unicode converter.

    The source converter includes approximate aliases and 24 redirects within
    GB2312 itself. Replaying those would discard original physical glyphs.
    A1A4/U+30FB and A1AA/U+2015 also agree with the source conversion table.
    No runtime aliases, extra GBK slots, or replacement glyphs are added here.
    """
    result = {}
    for lead in range(0xA1, 0xF8):
        for trail in range(0xA1, 0xFF):
            index = slot_index(lead, trail)
            if index is None:
                continue
            try:
                text = bytes((lead, trail)).decode('gb2312')
            except UnicodeDecodeError:
                continue
            require(len(text) == 1 and ord(text) not in result, 'Ambiguous Unicode mapping')
            result[ord(text)] = index
    require(len(result) == 7445 and sum(0x4E00 <= cp <= 0x9FFF for cp in result) == 6763,
            'Unexpected GB2312 coverage')
    digest = sha256(''.join(f'{cp:04X}:{index}\n' for cp, index in sorted(result.items())).encode('ascii'))
    require(digest == MAPPING_SHA256, 'Codec differs from audited GB2312 mapping')
    return result


def decode_rows(frame, width, height):
    require(width > 0 and height > 0 and width * height % 8 == 0,
            'Invalid packed glyph dimensions')
    require(len(frame) == width * height // 8, 'Invalid packed glyph size')
    packed = int.from_bytes(frame, 'big')
    mask = (1 << width) - 1
    return tuple((packed >> ((height - y - 1) * width)) & mask for y in range(height))


def source_payload(data, variant):
    require(variant in VARIANTS, 'Only approved simplified variants are supported')
    validate_source(data)
    v = VARIANTS[variant]
    member = parse_ar(data).get(v['member'])
    require(member is not None and len(member) == v['object_size'] and sha256(member) == v['object_sha256'],
            'Font object size/hash mismatch')
    payload = elf_payload(member, v['symbol'])
    require(len(payload) == 2 + SLOTS * v['width'] * v['height'] // 8
            and payload[:2] == bytes((v['width'], v['height']))
            and sha256(payload) == v['payload_sha256'], 'Font symbol size/header/hash mismatch')
    return payload


def decode(data, variant):
    payload = source_payload(data, variant)
    v = VARIANTS[variant]
    stride = v['width'] * v['height'] // 8
    glyphs = {cp: decode_rows(payload[2 + i * stride:2 + (i + 1) * stride], v['width'], v['height'])
              for cp, i in mapping().items()}
    require(all(any(rows) for cp, rows in glyphs.items() if 0x4E00 <= cp <= 0x9FFF),
            'Unexpected blank Han glyph')
    return glyphs


def ink_dimensions(glyphs, width):
    counts = {}
    for cp, rows in glyphs.items():
        if not 0x4E00 <= cp <= 0x9FFF:
            continue
        points = [(x, y) for y, row in enumerate(rows) for x in range(width) if row & (1 << (width - 1 - x))]
        xs, ys = zip(*points)
        size = (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        counts[size] = counts.get(size, 0) + 1
    return {'max_width': max(w for w, h in counts), 'max_height': max(h for w, h in counts),
            'counts': {f'{w}x{h}': count for (w, h), count in sorted(counts.items())}}


def png_data(glyphs, width, height, texts, gap=1, line_gap=4):
    require(texts and all(texts) and gap >= 0 and line_gap >= 0, 'Invalid specimen layout')
    widths = [len(t) * (width + gap) - gap for t in texts]
    canvas_w = max(widths)
    canvas_h = len(texts) * height + (len(texts) - 1) * line_gap
    pixels = bytearray(b'\xff\xff\xff\x00' * (canvas_w * canvas_h))
    for line, text in enumerate(texts):
        top = line * (height + line_gap)
        for y in range(height):
            for x in range(widths[line]):
                k = ((top + y) * canvas_w + x) * 4
                pixels[k:k + 4] = b'\xff\xff\xff\xff'
        for n, c in enumerate(text):
            require(ord(c) in glyphs, f'No source glyph for U+{ord(c):04X}')
            rows = glyphs[ord(c)]
            require(len(rows) == height and all(0 <= r < (1 << width) for r in rows), 'Invalid bitmap rows')
            for y, row in enumerate(rows):
                for x in range(width):
                    if row & (1 << (width - x - 1)):
                        k = ((top + y) * canvas_w + n * (width + gap) + x) * 4
                        pixels[k:k + 4] = b'\0\0\0\xff'
    raw = b''.join(b'\0' + pixels[y * canvas_w * 4:(y + 1) * canvas_w * 4] for y in range(canvas_h))
    def chunk(tag, body):
        return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', binascii.crc32(tag + body) & 0xFFFFFFFF)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', canvas_w, canvas_h, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def bdf(glyphs, width, height):
    padding = (-width) % 8
    digits = (width + 7) // 8 * 2
    # At SIZE height and 75dpi, SWIDTH = DWIDTH * 72000 / (height * 75).
    swidth = round(width * 960 / height)
    lines = ['STARTFONT 2.1', 'COMMENT Native source pixels; font rights remain with their owners.',
             'COMMENT STANDARD UNICODE INTERPRETATION of original GB2312 source slots.',
             'COMMENT Not a replica of the source runtime approximate Unicode converter.',
             'COMMENT STORAGE-CELL CONVENTION ONLY: top-aligned, fixed cell advance.',
             'COMMENT Device runtime advance and baseline are unverified; no ASCII added.',
             f'FONT -historical-sunplus_sphe8202l-medium-r-normal--{height}-0-75-75-c-{width * 10}-iso10646-1',
             f'SIZE {height} 75 75', f'FONTBOUNDINGBOX {width} {height} 0 0', 'STARTPROPERTIES 2',
             f'FONT_ASCENT {height}', 'FONT_DESCENT 0', 'ENDPROPERTIES', f'CHARS {len(glyphs)}']
    for cp, rows in sorted(glyphs.items()):
        require(len(rows) == height and all(0 <= r < 1 << width for r in rows), 'Invalid BDF rows')
        lines += [f'STARTCHAR uni{cp:04X}', f'ENCODING {cp}', f'SWIDTH {swidth} 0',
                  f'DWIDTH {width} 0', f'BBX {width} {height} 0 0', 'BITMAP']
        lines += [f'{r << padding:0{digits}X}' for r in rows]
        lines += ['ENDCHAR']
    return '\n'.join(lines + ['ENDFONT', ''])


def write_outputs(output, files):
    output = Path(output)
    reject_symlinks(output)
    require(not output.exists() or output.is_dir(), 'Output is not a directory')
    require(all(Path(n).name == n and '\\' not in n and n not in ('.', '..') for n in files), 'Invalid output name')
    require(all(not ((output / n).exists() or (output / n).is_symlink()) for n in files),
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
    ap.add_argument('source', help='Exact-SHA complete local libfont.a')
    ap.add_argument('--output', type=Path, required=True, help='Use a new local-research/ directory')
    ap.add_argument('--size', choices=tuple(VARIANTS) + ('all',), default='all')
    ap.add_argument('--export-bdf', action='store_true', help='Optional local-only BDF: standard Unicode interpretation of GB2312 source slots, not runtime aliases; requires your own font usage rights')
    args = ap.parse_args()
    data = read_source(args.source)
    files, report = {}, {'archive_sha256': sha256(data), 'variants': {}}
    for name in (VARIANTS if args.size == 'all' else (args.size,)):
        v = VARIANTS[name]
        w, h = v['width'], v['height']
        gs = decode(data, name)
        identity = 'sunplus_sphe8202l_' + name
        files[identity + '.png'] = png_data(gs, w, h, [PHRASE])
        files[identity + '-diagnostic.png'] = png_data(gs, w, h, [EXTRA])
        report['variants'][name] = {
            'catalog_status': 'Existing HZK12 duplicate; technical source comparison only' if name == '12x12' else 'New Sunplus catalog specimen',
            'object_sha256': v['object_sha256'], 'payload_sha256': v['payload_sha256'],
            'stored_slots': SLOTS, 'mapped_characters': len(gs), 'mapped_han': 6763,
            'nonblank_mapped': sum(any(rows) for rows in gs.values()),
            'blank_mapped_unicode': [f'U+{cp:04X}' for cp, rows in sorted(gs.items()) if not any(rows)],
            'cell': [w, h], 'han_ink': ink_dimensions(gs, w), 'printable_ascii': 0,
            'ascii_origin': 'Absent from the selected CP936 object; no font pairing or substitution.',
            'mapping': 'Original GB2312 slots to standard Unicode; not a replica of runtime approximate Unicode conversion. CP936 object name does not imply full GBK.',
            'specimen_sha256': sha256(files[identity + '.png']),
            'layout': 'Full storage cells plus 1px specimen gap; runtime advance/baseline unverified.',
        }
        if args.export_bdf:
            files[identity + '-gb2312-standard-unicode-interpretation.bdf'] = bdf(gs, w, h).encode('ascii')
    files['sunplus-report.json'] = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    write_outputs(args.output, files)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
