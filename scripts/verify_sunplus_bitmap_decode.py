#!/usr/bin/env python3
"""Independently audit the three simplified Sunplus SPHE8202L bitmap exports.

Reads the original ar archive as data, never executes an object or firmware, and
examines only the three CP936 bitmap members and CP936 mapping metadata.
Independent ar, ELF, GB2312,
pixel, BDF and PNG readers do not reuse the exporter's parsing or decoding.
Full glyphs, diagnostic PNGs and BDFs remain in memory. The optional JSON output
contains only aggregate counts, hashes, statuses and container boundaries.
All three CP936 sources remain technical audit subjects. Only 16x16 and 20x24
are new public entries: 12x12 duplicates the existing HZK12 repertoire, as
confirmed by a separate complete-source comparison, and stays a technical
comparison only. --specimen-dir checks the two public specimens, not 12x12.
"""

import argparse
import binascii
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import zlib


SOURCE_BYTES = 13305912
SOURCE_SHA256 = 'bbf28d191a165c8540f34c66ea6839fa395bcdfd2825e6342f1a4eff7210a5df'
PHRASE = '视野无限广，窗外有蓝天。'
EXTRA = '片版牌局'
SLOTS = 7614
PUBLIC_VARIANTS = ('16x16', '20x24')
HZK12_SOURCE_SHA256 = 'd83b7f1603e87dd68bebc3a6a159c57909779684188cba790146f59424c28a02'
FONTINFO_MEMBER = 'FontInfo_FONT_CP_936.o'
FONTINFO_SHA256 = 'bdbe34c290c34a73dcc6fb063172218dac10847cae84189674177a26d7383477'
FONTINFO_SYMBOLS = {
    'UtoG': (0, 44506, '8ada71afbea4af69cfebed861481b1839faf3c4f434e9cb4a785e4119f561ad4'),
    'UtoG_table_offset': (44508, 264, '8fc1061e9b8b034e827d6dcf506fffb2fe6ac5ab1d54f9ef94a56df5f69f243f'),
    'FontInfo_FONT_CP_936_HighByte': (44772, 4, 'bac9e78065464fb11011529d8f37fbc3e750a4999d9a232a9e74fcfd86a11df8'),
    'FontInfo_FONT_CP_936_LowByte': (44776, 2, '00629a368cf722a648b5438ef81bf21f22b56c15a5a55a4e1d2956a54a6c5bb8'),
}
VARIANTS = {
    '12x12': {
        'width': 12, 'height': 12,
        'object_sha256': 'cae41b8c3cc568a92dd40b16e21e1de0d06af7f2a1839bd37845b059f6b9b151',
        'payload_sha256': 'e6135cbfde217794148394c379699f9795dc9d9cae6d14e43be57442a8a7e61a',
        'object_bytes': 139649, 'ar_header_offset': 945526,
        'ar_data_offset': 945586, 'rodata_offset': 1868,
        'rodata_bytes': 137056, 'symbol_bytes': 137054,
        'blank_mapped_count': 1,
    },
    '16x16': {
        'width': 16, 'height': 16,
        'object_sha256': 'ccde5faca1424eeb8b6c32d6d33142910146fa8952e134c22beaffa0df84eae2',
        'payload_sha256': '1f0ad632938ced219964358f11aa78fed84da5578eca4383182289ec724f32a8',
        'object_bytes': 246245, 'ar_header_offset': 2435386,
        'ar_data_offset': 2435446, 'rodata_offset': 1868,
        'rodata_bytes': 243652, 'symbol_bytes': 243650,
        'blank_mapped_count': 2,
    },
    '20x24': {
        'width': 20, 'height': 24,
        'object_sha256': '26c367d39cf2d0eb39d926337b453ac87400f37b3c58d001efdd518d8da3db2e',
        'payload_sha256': '3092173e88303e04a9c29c9f3deb4212557beeba8de63f0ee603f5b4e25103e4',
        'object_bytes': 459437, 'ar_header_offset': 5110138,
        'ar_data_offset': 5110198, 'rodata_offset': 1868,
        'rodata_bytes': 456844, 'symbol_bytes': 456842,
        'blank_mapped_count': 3,
    },
}
for _name, _info in VARIANTS.items():
    _info['member'] = f'FontBmp_FONT_CP_936_FONT_SIZE_{_name}_FONT_NOT_COMPRESSED.o'


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bounded(data, offset, size, label):
    check(0 <= offset <= len(data) and 0 <= size <= len(data) - offset,
          label + ' exceeds containing object')
    return data[offset:offset + size]


def cstring(data, offset, label):
    check(0 <= offset < len(data), label + ' string offset')
    end = data.find(b'\0', offset)
    check(end >= 0, label + ' missing string terminator')
    return data[offset:end].decode('ascii')


def independent_ar(data):
    """Parse ar; retain three bitmaps and their CP936 mapping metadata only."""
    check(data[:8] == b'!<arch>\n', 'Not an ar archive')
    wanted = {value['member'] for value in VARIANTS.values()}
    wanted.add(FONTINFO_MEMBER)
    names = None
    cursor = 8
    found = {}
    seen = set()
    count = 0
    while cursor < len(data):
        header = bounded(data, cursor, 60, 'ar member header')
        check(header[58:60] == b'`\n', 'ar member header terminator')
        name_field = header[:16].decode('ascii').rstrip(' ')
        size_field = header[48:58].decode('ascii').strip()
        check(size_field.isdigit(), 'ar member size is not decimal')
        size = int(size_field)
        start = cursor + 60
        check(start + size <= len(data), 'ar member exceeds archive')
        if name_field == '//':
            check(names is None, 'Repeated ar long-name table')
            names = data[start:start + size]
            name = '//'
        elif name_field == '/':
            name = '/'
        elif name_field.startswith('/'):
            check(names is not None and name_field[1:].isdigit(),
                  'Invalid ar long-name reference')
            offset = int(name_field[1:])
            check(0 <= offset < len(names), 'ar long-name offset')
            check(offset == 0 or names[offset - 1:offset] == b'\n',
                  'ar reference is not at a name boundary')
            end = names.find(b'/\n', offset)
            check(end >= 0, 'ar long-name terminator')
            name = names[offset:end].decode('ascii')
        else:
            check(not name_field.startswith('#1/'), 'Unsupported BSD ar name')
            name = name_field.removesuffix('/')
        check(name not in seen, 'Duplicate ar member name')
        seen.add(name)
        if name in wanted:
            found[name] = (data[start:start + size], {
                'ar_header_offset': cursor, 'ar_data_offset': start,
                'object_bytes': size,
            })
        # Non-CP936 objects are skipped without ELF or bitmap interpretation.
        next_cursor = start + size
        if size % 2:
            check(bounded(data, next_cursor, 1, 'ar padding') == b'\n',
                  'ar odd-size member padding')
            next_cursor += 1
        check(next_cursor > cursor, 'ar cursor did not advance')
        cursor = next_cursor
        count += 1
    check(cursor == len(data), 'ar trailing extent')
    check(set(found) == wanted, 'Missing permitted CP936 member')
    return found, count


def independent_elf(obj, symbol_name, bitmap=True):
    """Locate the declared STT_OBJECT via ELF32 section and symbol tables."""
    check(len(obj) >= 52 and obj[:7] == b'\x7fELF\x01\x01\x01',
          'Expected little-endian ELF32 version 1')
    header = struct.unpack_from('<HHIIIIIHHHHHH', obj, 16)
    (etype, machine, version, entry, phoff, shoff, flags, ehsize,
     phentsize, phnum, shentsize, shnum, shstrndx) = header
    check((etype, machine, version, ehsize) == (1, 8, 1, 52),
          'Expected MIPS ELF32 relocatable object')
    check(entry == 0 and phnum == 0 and phoff == 0, 'Unexpected executable headers')
    check(shentsize == 40 and shnum > 0 and 0 < shstrndx < shnum,
          'ELF section table geometry')
    bounded(obj, shoff, shnum * shentsize, 'ELF section table')
    sections = [struct.unpack_from('<10I', obj, shoff + index * shentsize)
                for index in range(shnum)]
    for section in sections:
        if section[1] != 8:  # SHT_NOBITS has no file payload.
            bounded(obj, section[4], section[5], 'ELF section')
        alignment = section[8]
        check(alignment == 0 or alignment & (alignment - 1) == 0,
              'ELF non-power-of-two alignment')
        check(alignment <= 1 or section[4] % alignment == 0,
              'ELF section file alignment')
    name_section = sections[shstrndx]
    check(name_section[1] == 3, 'ELF section names are not SHT_STRTAB')
    section_names = bounded(obj, name_section[4], name_section[5], 'ELF section names')
    labels = [cstring(section_names, section[0], 'ELF section name') for section in sections]
    check(len(set(labels)) == len(labels), 'Duplicate ELF section name')
    matches = []
    for index, section in enumerate(sections):
        if section[1] != 2:
            continue
        check(section[9] == 16 and section[5] % 16 == 0,
              'ELF symbol table geometry')
        check(0 < section[6] < shnum, 'ELF symbol string-table reference')
        strings_section = sections[section[6]]
        check(strings_section[1] == 3, 'ELF symbol names are not SHT_STRTAB')
        strings = bounded(obj, strings_section[4], strings_section[5], 'ELF symbol names')
        for offset in range(section[4], section[4] + section[5], 16):
            name, value, size, info, other, section_index = struct.unpack_from('<IIIBBH', obj, offset)
            label = cstring(strings, name, 'ELF symbol name')
            if label == symbol_name:
                expected_info = 0x11 if bitmap else 0x01
                check(info == expected_info and other == 0,
                      'Unexpected font symbol binding/type/visibility')
                check(0 < section_index < shnum, 'ELF symbol section reference')
                matches.append((value, size, section_index, offset, index))
    check(len(matches) == 1, 'Expected exactly one font object symbol')
    value, size, index, symbol_offset, symtab_index = matches[0]
    section = sections[index]
    check(labels[index] == '.rodata' and section[1] == 1 and section[2] == 2,
          'Font symbol is not in read-only PROGBITS')
    check(section[3] == 0 and (not bitmap or value == 0),
          'Unexpected font symbol offset/address')
    check(0 < size <= section[5] - value, 'ELF symbol exceeds its section')
    payload = bounded(obj, section[4] + value, size, 'ELF font symbol')
    alignment_bytes = section[5] - value - size
    if bitmap:
        check(alignment_bytes == 2, 'Expected exactly two section-alignment bytes')
        check(not any(obj[section[4] + value + size:section[4] + section[5]]),
              'Nonzero section-alignment bytes')
    report = {
        'elf_section_table_offset': shoff, 'elf_section_count': shnum,
        'rodata_section_index': index, 'rodata_offset': section[4],
        'rodata_bytes': section[5], 'symbol_table_section_index': symtab_index,
        'symbol_entry_offset': symbol_offset, 'symbol_value': value,
        'symbol_bytes': size, 'payload_object_offset': section[4] + value,
    }
    if bitmap:
        report.update(excluded_alignment_bytes=alignment_bytes, alignment_bytes_zero=True)
    return payload, report


def independent_mapping():
    result = {}
    slot = 0
    invalid = 0
    for leads in (range(0xA1, 0xAA), range(0xB0, 0xF8)):
        for lead in leads:
            for trail in range(0xA1, 0xFF):
                try:
                    text = bytes((lead, trail)).decode('gb2312', errors='strict')
                except UnicodeDecodeError:
                    invalid += 1
                else:
                    check(len(text) == 1 and ord(text) not in result,
                          'Nonunique GB2312 mapping')
                    result[ord(text)] = slot
                slot += 1
    check(slot == SLOTS and len(result) == 7445 and invalid == 169,
          'Independent GB2312 slot counts')
    check(sum(0x4E00 <= cp <= 0x9FFF for cp in result) == 6763,
          'Independent GB2312 Han count')
    check(not set(range(128)) & result.keys(), 'Unexpected single-byte ASCII mapping')
    return result


def check_fontinfo(obj, ar_boundaries, mapping):
    """Audit source Unicode aliases without using them to relabel bitmap slots.

    The range table is addressed in bytes: Unicode*2 - subtract. Reading this
    data is not execution or emulation of the MIPS functions. It documents why
    runtime substitutions must not replace a physical-code GB2312 inventory.
    """
    check(len(obj) == 52428 and sha(obj) == FONTINFO_SHA256,
          'FontInfo object size/hash')
    symbols = {}
    symbol_reports = {}
    for name, (value, size, digest) in FONTINFO_SYMBOLS.items():
        payload, bounds = independent_elf(obj, name, bitmap=False)
        check(bounds['rodata_offset'] == 6240 and bounds['rodata_bytes'] == 44844,
              'FontInfo rodata boundary')
        check((bounds['symbol_value'], bounds['symbol_bytes']) == (value, size),
              'FontInfo symbol boundary ' + name)
        check(sha(payload) == digest, 'FontInfo symbol hash ' + name)
        symbols[name] = payload
        symbol_reports[name] = {'sha256': digest, 'boundaries': bounds}
    check(symbols['FontInfo_FONT_CP_936_HighByte'] == bytes((0xA1, 0xA9, 0xB0, 0xF7)),
          'FontInfo physical lead-byte ranges')
    check(symbols['FontInfo_FONT_CP_936_LowByte'] == bytes((0xA1, 0xFE)),
          'FontInfo physical trail-byte range')
    raw_ranges = symbols['UtoG_table_offset']
    table = symbols['UtoG']
    ranges = [struct.unpack_from('<III', raw_ranges, offset)
              for offset in range(0, len(raw_ranges), 12)]
    check(len(ranges) == 22, 'FontInfo Unicode range count')
    end = 0
    previous_unicode_end = 0
    for start, length, subtract in ranges:
        check(start % 2 == length % 2 == subtract % 2 == 0,
              'FontInfo Unicode range alignment')
        check(start >= previous_unicode_end and length > 0 and start + length <= 0x20000,
              'FontInfo Unicode range order/extent')
        check(start - subtract == end, 'FontInfo ranges do not cover table contiguously')
        end += length
        check(end <= len(table), 'FontInfo range exceeds UtoG symbol')
        previous_unicode_end = start + length
    check(end == len(table), 'FontInfo range coverage does not match UtoG symbol')

    def table_code(cp):
        address = cp * 2
        for start, length, subtract in ranges:
            if start <= address < start + length:
                offset = address - subtract
                return bounded(table, offset, 2, 'FontInfo mapping entry')
        return None

    key_values = {
        0x30FB: b'\xA1\xA4', 0x2022: b'\xA1\xA4', 0x00B7: b'\xA1\xF5',
        0x2015: b'\xA1\xAA', 0x2500: b'\xA1\xAA', 0xFF0D: b'\xA1\xAA',
        0x2014: b'\xA1\xF5',
    }
    for cp, expected in key_values.items():
        check(table_code(cp) == expected, 'FontInfo key mapping U+' + format(cp, '04X'))
    differences = []
    for cp in sorted(mapping):
        standard = chr(cp).encode('gb2312')
        source = table_code(cp)
        check(source is not None, 'GB2312 character outside FontInfo ranges')
        if source != standard:
            differences.append({
                'unicode': f'U+{cp:04X}', 'gb2312_source_code': standard.hex().upper(),
                'fontinfo_source_code': source.hex().upper(),
            })
    han_differences = sum(0x4E00 <= int(item['unicode'][2:], 16) <= 0x9FFF
                          for item in differences)
    check(len(differences) == 24 and han_differences == 11,
          'FontInfo/GB2312 differences changed')
    return {
        'passed': True, 'object_bytes': len(obj), 'object_sha256': sha(obj),
        'ar_boundaries': ar_boundaries, 'symbols': symbol_reports,
        'unicode_range_count': len(ranges), 'unicode_table_entries': len(table) // 2,
        'contiguous_table_range_coverage': True, 'gb2312_mappings_compared': len(mapping),
        'different_source_code_count': len(differences), 'different_han_source_code_count': han_differences,
        'differences': differences,
        'key_mappings': [{'unicode': f'U+{cp:04X}', 'fontinfo_source_code': code.hex().upper()}
                         for cp, code in sorted(key_values.items())],
        'runtime_aliases_applied_to_export': False, 'runtime_functions_executed': False,
        'additional_alias_glyphs_decoded': 0,
    }


def source_bit(frame, width, x, y):
    # The source is a continuous width*height bitstream, with no row padding.
    position = y * width + x
    byte_offset, bit_offset = divmod(position, 8)
    return (frame[byte_offset] >> (7 - bit_offset)) & 1


def direct_rows(frame, width, height):
    check(len(frame) * 8 == width * height, 'Source frame bit extent')
    rows = []
    for y in range(height):
        row = 0
        for x in range(width):
            row = row * 2 + source_bit(frame, width, x, y)
        rows.append(row)
    return tuple(rows)


def check_bdf(text, frames, width, height):
    lines = text.splitlines()
    check(lines[0] == 'STARTFONT 2.1' and lines[-1] == 'ENDFONT', 'BDF envelope')
    check(f'FONTBOUNDINGBOX {width} {height} 0 0' in lines, 'BDF font bounding box')
    check(f'SIZE {height} 75 75' in lines, 'BDF point size/resolution')
    check(f'CHARS {len(frames)}' in lines, 'BDF declared glyph count')
    seen = set()
    cursor = 0
    pad = (-width) % 8
    row_bytes = (width + 7) // 8
    expected_swidth = round(width * 72000 / (height * 75))
    while cursor < len(lines):
        if not lines[cursor].startswith('STARTCHAR '):
            cursor += 1
            continue
        end = lines.index('ENDCHAR', cursor + 1)
        block = lines[cursor + 1:end]
        encodings = [line for line in block if line.startswith('ENCODING ')]
        check(len(encodings) == 1, 'BDF encoding count')
        cp = int(encodings[0].split()[1])
        check(cp in frames and cp not in seen, 'BDF repertoire or duplicate encoding')
        check(f'DWIDTH {width} 0' in block and f'BBX {width} {height} 0 0' in block,
              'BDF glyph bounding box or advance')
        check(f'SWIDTH {expected_swidth} 0' in block,
              'BDF SWIDTH inconsistent with SIZE and DWIDTH')
        check(block.count('BITMAP') == 1, 'BDF bitmap marker')
        bitmap = block[block.index('BITMAP') + 1:]
        check(len(bitmap) == height, 'BDF row count')
        for y, row in enumerate(bitmap):
            check(len(row) == row_bytes * 2, 'BDF byte-aligned row width')
            bits = bytes.fromhex(row)
            check(len(bits) == row_bytes, 'BDF malformed hex row')
            if pad:
                check(bits[-1] & ((1 << pad) - 1) == 0, 'BDF nonzero low padding bits')
            for x in range(width):
                actual = (bits[x // 8] >> (7 - x % 8)) & 1
                check(actual == source_bit(frames[cp], width, x, y),
                      f'BDF source pixel mismatch U+{cp:04X} at {x},{y}')
        seen.add(cp)
        cursor = end + 1
    check(seen == set(frames), 'BDF missing glyphs')
    return {
        'passed': True, 'glyph_count': len(seen), 'pixel_checks': len(seen) * width * height,
        'row_bytes': row_bytes, 'right_padding_bits': pad,
        'source_pixel_roundtrip': True, 'left_aligned_rows': True,
        'swidth_consistent_with_size_and_dwidth': True, 'swidth': expected_swidth,
        'sha256': sha(text.encode('ascii')),
    }


def png_pixels(blob):
    check(blob[:8] == b'\x89PNG\r\n\x1a\n', 'PNG signature')
    cursor = 8
    header = None
    compressed = bytearray()
    ended = False
    idat_ended = False
    idat_seen = False
    chunk_count = 0
    while cursor < len(blob):
        check(not ended, 'PNG trailing bytes after IEND')
        length, tag = struct.unpack('>I4s', bounded(blob, cursor, 8, 'PNG chunk header'))
        body = bounded(blob, cursor + 8, length, 'PNG chunk body')
        crc, = struct.unpack('>I', bounded(blob, cursor + 8 + length, 4, 'PNG CRC field'))
        check(crc == binascii.crc32(tag + body) & 0xFFFFFFFF, 'PNG CRC mismatch')
        if tag == b'IHDR':
            check(header is None and cursor == 8 and length == 13, 'PNG IHDR placement/size')
            header = struct.unpack('>IIBBBBB', body)
        elif tag == b'IDAT':
            check(header is not None and not idat_ended, 'PNG IDAT placement')
            compressed.extend(body)
            idat_seen = True
        elif tag == b'IEND':
            check(header is not None and idat_seen and length == 0, 'PNG IEND placement/size')
            ended = True
        else:
            check(tag[0] & 32, 'Unexpected critical PNG chunk')
        if idat_seen and tag != b'IDAT':
            idat_ended = True
        cursor += 12 + length
        chunk_count += 1
    check(ended and header is not None, 'PNG missing header/end')
    width, height, depth, ctype, compression, filtering, interlace = header
    check(width > 0 and height > 0 and (depth, ctype, compression, filtering, interlace)
          == (8, 6, 0, 0, 0), 'Expected noninterlaced 8-bit RGBA PNG')
    inflater = zlib.decompressobj()
    raw = inflater.decompress(compressed) + inflater.flush()
    check(inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail,
          'PNG zlib stream boundary')
    stride = width * 4
    check(len(raw) == (stride + 1) * height, 'PNG decompressed extent')
    rows = []
    previous = bytes(stride)
    for y in range(height):
        offset = y * (stride + 1)
        filter_kind = raw[offset]
        check(filter_kind in range(5), 'PNG filter kind')
        row = bytearray(raw[offset + 1:offset + stride + 1])
        for x in range(stride):
            left = row[x - 4] if x >= 4 else 0
            above = previous[x]
            upper_left = previous[x - 4] if x >= 4 else 0
            if filter_kind == 0:
                predictor = 0
            elif filter_kind == 1:
                predictor = left
            elif filter_kind == 2:
                predictor = above
            elif filter_kind == 3:
                predictor = (left + above) // 2
            else:
                p = left + above - upper_left
                distances = (abs(p - left), abs(p - above), abs(p - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
            row[x] = (row[x] + predictor) & 255
        rows.append(bytes(row))
        previous = row
    return width, height, rows, chunk_count


def check_png(blob, frames, width, height, texts, gap=1, line_gap=4):
    canvas_width, canvas_height, rows, chunk_count = png_pixels(blob)
    line_widths = [len(text) * width + (len(text) - 1) * gap for text in texts]
    check((canvas_width, canvas_height) ==
          (max(line_widths), len(texts) * height + (len(texts) - 1) * line_gap),
          'PNG native dimensions/gaps')
    on_pixels = 0
    transparent_pixels = 0
    for y, row in enumerate(rows):
        line_index, sy = divmod(y, height + line_gap)
        for x in range(canvas_width):
            expected = b'\xff\xff\xff\x00'
            if sy < height and x < line_widths[line_index]:
                expected = b'\xff\xff\xff\xff'
                char_index, sx = divmod(x, width + gap)
                if sx < width:
                    frame = frames[ord(texts[line_index][char_index])]
                    if source_bit(frame, width, sx, sy):
                        expected = b'\0\0\0\xff'
                        on_pixels += 1
            else:
                transparent_pixels += 1
            check(row[x * 4:x * 4 + 4] == expected,
                  f'PNG source pixel/alpha/gap mismatch at {x},{y}')
    return {
        'passed': True, 'width': canvas_width, 'height': canvas_height,
        'pixel_checks': canvas_width * canvas_height, 'on_pixels': on_pixels,
        'transparent_pixels': transparent_pixels, 'chunk_crc_checks': chunk_count,
        'gap': gap, 'line_gap': line_gap, 'line_count': len(texts),
        'sha256': sha(blob),
    }


def load_exporter(path):
    check(path.is_file(), 'Exporter is not available')
    specification = importlib.util.spec_from_file_location('sunplus_export_under_test', path)
    module = importlib.util.module_from_spec(specification)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        specification.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def audit(source, exporter, specimen_dir=None):
    archive = source.read_bytes()
    check(len(archive) == SOURCE_BYTES and sha(archive) == SOURCE_SHA256,
          'Wrong source archive size/hash')
    objects, ar_count = independent_ar(archive)
    mapping = independent_mapping()
    fontinfo_report = check_fontinfo(*objects[FONTINFO_MEMBER], mapping)
    source_payloads = {}
    boundaries = {}
    for name, info in VARIANTS.items():
        obj, ar_boundary = objects[info['member']]
        check(sha(obj) == info['object_sha256'], name + ' original object hash')
        payload, elf_boundary = independent_elf(obj, info['member'][:-2])
        check(sha(payload) == info['payload_sha256'], name + ' original payload hash')
        combined = ar_boundary | elf_boundary
        for key in ('ar_header_offset', 'ar_data_offset', 'object_bytes', 'rodata_offset',
                    'rodata_bytes', 'symbol_bytes'):
            check(combined[key] == info[key], name + ' pinned boundary ' + key)
        check(payload[:2] == bytes((info['width'], info['height'])), name + ' size header')
        check(len(payload) == 2 + SLOTS * info['width'] * info['height'] // 8,
              name + ' exact physical slot extent')
        source_payloads[name] = payload
        boundaries[name] = combined
    module = load_exporter(exporter)
    check(set(module.VARIANTS) == set(VARIANTS), 'Exporter must offer exactly three CP936 variants')
    check(module.PHRASE == PHRASE and module.EXTRA == EXTRA, 'Exporter sample contract')
    check(module.read_source(source) == archive, 'Exporter source reader')
    exported_members = module.parse_ar(archive)
    check(module.mapping() == mapping, 'Exporter GB2312 mapping differs from enumeration')
    if specimen_dir is not None:
        check(not (specimen_dir / 'sunplus_sphe8202l_12x12.png').exists(),
              '12x12 duplicates HZK12 and must not remain a public specimen')
    variants = {}
    disk_specimens = {}
    for name, info in VARIANTS.items():
        width, height = info['width'], info['height']
        for key in ('width', 'height', 'member', 'object_sha256', 'payload_sha256'):
            check(module.VARIANTS[name][key] == info[key], name + ' exporter constant ' + key)
        obj = objects[info['member']][0]
        check(exported_members[info['member']] == obj, name + ' exporter ar member extraction')
        payload = source_payloads[name]
        check(module.elf_payload(obj, info['member'][:-2]) == payload,
              name + ' exporter ELF symbol extent')
        frame_bytes = width * height // 8
        expected_rows = []
        frames = []
        for slot in range(SLOTS):
            offset = 2 + slot * frame_bytes
            frame = payload[offset:offset + frame_bytes]
            reference = direct_rows(frame, width, height)
            check(tuple(module.decode_rows(frame, width, height)) == reference,
                  f'{name} physical slot {slot} bitstream mismatch')
            expected_rows.append(reference)
            frames.append(frame)
        decoded = module.decode(archive, name)
        check(set(decoded) == set(mapping), name + ' decoded repertoire')
        mapped_frames = {}
        blank_mapped = 0
        blank_han = 0
        for cp, slot in mapping.items():
            check(tuple(decoded[cp]) == expected_rows[slot], name + ' mapped source pixels')
            mapped_frames[cp] = frames[slot]
            if not any(frames[slot]):
                blank_mapped += 1
                blank_han += int(0x4E00 <= cp <= 0x9FFF)
        check(blank_han == 0, name + ' blank mapped Han character')
        check(blank_mapped == info['blank_mapped_count'], name + ' blank mapped count')
        check(all(ord(char) in mapped_frames for char in PHRASE + EXTRA),
              name + ' missing fixed sample character')
        bdf_report = check_bdf(module.bdf(decoded, width, height), mapped_frames, width, height)
        samples = {}
        phrase_label = 'published_phrase' if name in PUBLIC_VARIANTS else 'technical_comparison_phrase'
        sample_contracts = {
            phrase_label: ([PHRASE], 1, 4),
            'diagnostic': ([EXTRA], 0, 4),
            'two_line_diagnostic': ([PHRASE, EXTRA], 1, 4),
            'custom_gaps': ([PHRASE, EXTRA], 3, 2),
        }
        for label, (texts, gap, line_gap) in sample_contracts.items():
            blob = module.png_data(decoded, width, height, texts, gap=gap, line_gap=line_gap)
            samples[label] = check_png(blob, mapped_frames, width, height, texts, gap, line_gap)
            if name in PUBLIC_VARIANTS and label == phrase_label and specimen_dir is not None:
                filename = f'sunplus_sphe8202l_{name}.png'
                disk_path = specimen_dir / filename
                check(disk_path.is_file(), 'Missing existing specimen ' + filename)
                disk_blob = disk_path.read_bytes()
                check_png(disk_blob, mapped_frames, width, height, texts, gap, line_gap)
                check(disk_blob == blob, 'Existing specimen differs from current exporter ' + filename)
                disk_specimens[filename] = {'passed': True, 'sha256': sha(disk_blob)}
        variants[name] = {
            'passed': True, 'width': width, 'height': height,
            'new_catalog_entry': name in PUBLIC_VARIANTS,
            'public_specimen_required': name in PUBLIC_VARIANTS,
            'technical_comparison_only': name not in PUBLIC_VARIANTS,
            'object_sha256': sha(obj), 'payload_sha256': sha(payload),
            'boundaries': boundaries[name], 'header_bytes': 2,
            'frame_bytes': frame_bytes, 'physical_slots': SLOTS,
            'all_source_pixel_checks': SLOTS * width * height,
            'mapped_characters': len(mapping), 'mapped_han': 6763,
            'unmapped_slots': SLOTS - len(mapping), 'blank_mapped_count': blank_mapped,
            'blank_han_count': blank_han, 'ascii_mapped_count': 0,
            'sample_missing_count': 0, 'bdf': bdf_report, 'png_samples': samples,
        }
        if name == '12x12':
            variants[name]['duplicate_reference'] = {
                'name': 'HZK12', 'source_sha256': HZK12_SOURCE_SHA256,
                'matching_mapped_characters': 7445, 'matching_han_characters': 6763,
                'matching_cell_width': 12, 'matching_cell_height': 12,
                'status': 'confirmed-by-separate-full-repertoire-comparison',
                'comparison_rerun_by_this_verifier': False,
            }
    return {
        'passed': True, 'source_bytes': len(archive), 'source_sha256': sha(archive),
        'exporter_sha256': sha(exporter.read_bytes()),
        'verifier_sha256': sha(Path(__file__).read_bytes()),
        'ar_container_members': ar_count, 'bitmap_members_examined': len(variants),
        'mapping_metadata_members_examined': 1, 'source_mapping_metadata': fontinfo_report,
        'all_source_slot_checks': SLOTS * len(variants),
        'all_source_pixel_checks': sum(info['all_source_pixel_checks'] for info in variants.values()),
        'mapping_sha256': sha(''.join(f'{cp:04X}:{slot}\n' for cp, slot in sorted(mapping.items())).encode('ascii')),
        'source_lead_byte_ranges': [[0xA1, 0xA9], [0xB0, 0xF7]],
        'source_trail_byte_range': [0xA1, 0xFE],
        'variants': variants, 'existing_specimens': disk_specimens,
        'new_catalog_entry_count': len(PUBLIC_VARIANTS),
        'public_specimen_variants': list(PUBLIC_VARIANTS),
        'public_specimen_count': len(PUBLIC_VARIANTS),
        'technical_comparison_only_count': len(VARIANTS) - len(PUBLIC_VARIANTS),
        'existing_specimens_checked': specimen_dir is not None,
        'independent_ar_elf_readers': True, 'independent_bit_addressing': True,
        'independent_gb2312_enumeration': True, 'in_memory_bdf_roundtrip': True,
        'png_crc_dimensions_pixels_gaps_checked': True,
        'library_or_firmware_executed': False, 'traditional_bitmap_members_examined': 0,
        'full_glyph_data_written': False, 'diagnostic_images_written': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--exporter', type=Path,
                        default=Path(__file__).with_name('sunplus_bitmap_export.py'))
    parser.add_argument('--specimen-dir', type=Path,
                        help='Verify only the public 16x16/20x24 PNGs; reject a stale duplicate 12x12 PNG')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.report is not None:
        check(not args.report.exists(), 'Refusing to overwrite an existing audit report')
    report = audit(args.source, args.exporter, args.specimen_dir)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.report is not None:
        with args.report.open('x', encoding='utf-8') as handle:
            handle.write(rendered)
    print(rendered, end='')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, KeyError, IndexError, struct.error, zlib.error) as error:
        print('Audit failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
