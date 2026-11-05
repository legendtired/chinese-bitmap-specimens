#!/usr/bin/env python3
"""Export the audited FlipperCN 20240803 firmware's native U8g2 font to BDF.

Python 3.9+ standard library only. Supply your own lawfully obtained TGZ.
No downloading, device access, firmware execution, or glyph data is included.
Only the exact audited archive is accepted. Existing outputs are not overwritten.
Export does not establish permission to redistribute the source or font.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

ARCHIVE_SIZE = 10027673
ARCHIVE_SHA256 = 'e31b30ee7cbcc10ceae67d3533ae3a999d1ad3420ed0e38c93dd8b18b644b6a4'
DFU_MEMBER = 'f7-update-mntm-release-186bc960/firmware.dfu'
DFU_SIZE = 853165
DFU_SHA256 = '07ad42d9119ca653650a83c2e02dfecc369fd5742880a19012bcba52df3c7129'
FONT_OFFSET = 0xCB1C4  # Offset in the full DFU file, not the flash address.
FONT_SIZE = 11801
FONT_SHA256 = '15a85edd16380fef4991a1b3efd4fc85c51bc6bea8547cf51fdde2c9a9a4791d'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def signed_byte(value):
    return value - 256 if value >= 128 else value


def word(data, offset):
    if offset < 0 or offset + 2 > len(data):
        raise ValueError('Truncated U8g2 word.')
    return int.from_bytes(data[offset:offset + 2], 'big')


class Bits:
    """U8g2 fields are LSB-first; signed fields use an excess-2^(n-1) bias."""
    def __init__(self, data):
        self.data = data
        self.position = 0

    def unsigned(self, count):
        if not 0 <= count <= 8 or self.position + count > len(self.data) * 8:
            raise ValueError('Truncated or unsupported U8g2 bit field.')
        value = 0
        for bit in range(count):
            position = self.position + bit
            value |= ((self.data[position // 8] >> (position % 8)) & 1) << bit
        self.position += count
        return value

    def signed(self, count):
        if count < 1:
            raise ValueError('A signed U8g2 field must have at least one bit.')
        return self.unsigned(count) - (1 << (count - 1))


def decode_glyph(codepoint, raw, header):
    bits = Bits(raw)
    width, height = bits.unsigned(header[4]), bits.unsigned(header[5])
    x, y, advance = (bits.signed(header[index]) for index in (6, 7, 8))
    pixels = []
    target = width * height
    if (width == 0) != (height == 0):
        raise ValueError('Inconsistent empty glyph dimensions.')
    while len(pixels) < target:
        zero, one = bits.unsigned(header[2]), bits.unsigned(header[3])
        if zero + one == 0:
            raise ValueError('U8g2 RLE pair makes no progress.')
        while True:
            if len(pixels) + zero + one > target:
                raise ValueError('U8g2 RLE exceeds glyph bounds.')
            pixels.extend([0] * zero + [1] * one)
            repeat = bits.unsigned(1)
            if not repeat:
                break
    if len(raw) * 8 - bits.position >= 8:
        raise ValueError('Unused complete bytes at end of glyph.')
    rows = [sum(pixels[row * width + col] << (width - 1 - col)
                for col in range(width)) for row in range(height)]
    return {'unicode': codepoint, 'bbx': [width, height, x, y],
            'advance': advance, 'rows': rows}


def decode_font(data):
    """Read native BMP codepoints and metrics; no guessed encoding or fallback."""
    if len(data) < 27:
        raise ValueError('Truncated U8g2 font.')
    header = data[:23]
    if header[1] > 3 or any(not 1 <= width <= 8 for width in header[2:9]):
        raise ValueError('Unsupported U8g2 header.')
    glyphs, offsets = [], {}
    position = 23
    previous = -1
    while True:
        if position + 2 > len(data):
            raise ValueError('Missing U8g2 8-bit section terminator.')
        codepoint, size = data[position:position + 2]
        if size == 0:
            if codepoint != 0:
                raise ValueError('Invalid U8g2 8-bit section terminator.')
            break
        if size < 3 or position + size > len(data) or codepoint <= previous:
            raise ValueError('Invalid U8g2 8-bit glyph record.')
        offsets[codepoint] = position
        glyphs.append(decode_glyph(codepoint, data[position + 2:position + size], header))
        previous = codepoint
        position += size
    table = position + 2
    if table != 23 + word(header, 21):
        raise ValueError('Unicode lookup table does not match the header.')
    table_size = word(data, table)
    if table_size < 4 or table_size % 4 or table + table_size > len(data):
        raise ValueError('Invalid Unicode lookup table length.')
    position = table + table_size
    previous = 255
    while True:
        codepoint = word(data, position)
        if codepoint == 0:
            if position + 2 != len(data):
                raise ValueError('Unexpected data after the Unicode terminator.')
            break
        if position + 3 > len(data):
            raise ValueError('Truncated Unicode glyph record.')
        size = data[position + 2]
        if (size < 4 or position + size > len(data) or codepoint <= previous
                or 0xD800 <= codepoint <= 0xDFFF):
            raise ValueError('Invalid Unicode glyph record.')
        offsets[codepoint] = position
        glyphs.append(decode_glyph(codepoint, data[position + 3:position + size], header))
        previous = codepoint
        position += size
    if header[0] != len(glyphs) % 256:
        raise ValueError('Glyph count does not match the U8g2 byte-sized count.')
    for character, field in [('A', 17), ('a', 19)]:
        if ord(character) in offsets and 23 + word(header, field) != offsets[ord(character)]:
            raise ValueError('ASCII lookup offset does not match its glyph.')
    # Confirm each Unicode block's cumulative jump and coverage boundary.
    block_start, last_limit = table, 255
    unicode_offsets = {offsets[g['unicode']]: g['unicode'] for g in glyphs if g['unicode'] > 255}
    for entry in range(table, table + table_size, 4):
        block_start += word(data, entry)
        limit = word(data, entry + 2)
        if block_start not in unicode_offsets or not last_limit < unicode_offsets[block_start] <= limit:
            raise ValueError('Unicode index does not match the glyph sequence.')
        next_start = (block_start + word(data, entry + 4)
                      if entry + 4 < table + table_size else position)
        block_codes = [cp for offset, cp in unicode_offsets.items()
                       if block_start <= offset < next_start]
        if not block_codes or max(block_codes) > limit:
            raise ValueError('Unicode index excludes a glyph in its block.')
        last_limit = limit
    if last_limit != 0xFFFF:
        raise ValueError('Unicode index lacks its final sentinel.')
    bbox = [header[9], header[10], signed_byte(header[11]), signed_byte(header[12])]
    for glyph in glyphs:
        width, height, x, y = glyph['bbx']
        if width and (x < bbox[2] or y < bbox[3] or x + width > bbox[2] + bbox[0]
                      or y + height > bbox[3] + bbox[1]):
            raise ValueError('Glyph exceeds the original global bounding box.')
    return {'bbox': bbox, 'glyphs': glyphs}


def recover(archive):
    if len(archive) != ARCHIVE_SIZE or sha256(archive) != ARCHIVE_SHA256:
        raise ValueError('Unknown input archive; only the audited 20240803 TGZ is supported. '
                         'Refusing to guess offsets. SHA256: ' + sha256(archive))
    # Read only the named member in memory. Never extract paths or execute a file.
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as bundle:
        matching = [member for member in bundle.getmembers() if member.name == DFU_MEMBER]
        if len(matching) != 1 or not matching[0].isfile() or matching[0].size != DFU_SIZE:
            raise ValueError('Expected firmware.dfu member is missing or invalid.')
        stream = bundle.extractfile(matching[0])
        if stream is None:
            raise ValueError('Cannot read firmware.dfu member.')
        dfu = stream.read()
    if sha256(dfu) != DFU_SHA256:
        raise ValueError('DFU SHA256 mismatch.')
    if dfu[:6] != b'DfuSe\x01':
        raise ValueError('Unexpected DFU container.')
    font_data = dfu[FONT_OFFSET:FONT_OFFSET + FONT_SIZE]
    if sha256(font_data) != FONT_SHA256:
        raise ValueError('Embedded font SHA256 mismatch.')
    font = decode_font(font_data)
    glyphs = font['glyphs']
    if len(glyphs) != 604 or sum(0x4E00 <= g['unicode'] <= 0x9FFF for g in glyphs) != 503:
        raise ValueError('Unexpected coverage in the audited font.')
    return font


def bdf_text(font):
    width, height, x, y = font['bbox']
    glyphs = font['glyphs']
    lines = ['STARTFONT 2.1',
             'COMMENT Native U8g2 pixels and Unicode codepoints; no rasterization or fallback.',
             'COMMENT Source archive SHA256 ' + ARCHIVE_SHA256,
             'COMMENT Embedded font SHA256 ' + FONT_SHA256,
             'COMMENT Export does not grant redistribution rights.',
             'COMMENT SIZE uses the 11-pixel global bounds as an export convention.',
             'FONT -Recovered-FlipperCN20240803-Medium-R-Normal--11-110-72-72-P-0-ISO10646-1',
             'SIZE 11 72 72', f'FONTBOUNDINGBOX {width} {height} {x} {y}',
             'STARTPROPERTIES 4', f'FONT_ASCENT {height + y}', f'FONT_DESCENT {-y}',
             'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"', 'ENDPROPERTIES',
             f'CHARS {len(glyphs)}']
    for glyph in glyphs:
        width, height, x, y = glyph['bbx']
        advance = glyph['advance']
        lines += [f"STARTCHAR uni{glyph['unicode']:04X}", f"ENCODING {glyph['unicode']}",
                  f'SWIDTH {round(advance * 1000 / 11)} 0', f'DWIDTH {advance} 0',
                  f'BBX {width} {height} {x} {y}', 'BITMAP']
        row_bytes = (width + 7) // 8
        padding = row_bytes * 8 - width
        lines += [f'{row << padding:0{row_bytes * 2}X}' for row in glyph['rows']]
        lines.append('ENDCHAR')
    return '\n'.join(lines + ['ENDFONT', ''])


def summary(font, output=None):
    glyphs = font['glyphs']
    han = [g for g in glyphs if 0x4E00 <= g['unicode'] <= 0x9FFF]
    result = {'sourceArchiveSha256': ARCHIVE_SHA256, 'dfuMember': DFU_MEMBER,
              'dfuSha256': DFU_SHA256, 'fontOffsetInDfu': FONT_OFFSET,
              'fontLength': FONT_SIZE, 'fontSha256': FONT_SHA256,
              'globalBoundingBox': font['bbox'], 'glyphs': len(glyphs), 'han': len(han),
              'asciiPrintable': sum(32 <= g['unicode'] <= 126 for g in glyphs),
              'unicodeMapping': 'native U8g2 BMP codepoints',
              'blankCodepoints': [f"U+{g['unicode']:04X}" for g in glyphs if not any(g['rows'])],
              'hanAdvanceExceptions': [
                  {'codepoint': f"U+{g['unicode']:04X}", 'advance': g['advance'], 'bbx': g['bbx']}
                  for g in han if g['advance'] != 10],
              'warning': 'UI subset only; not a complete Chinese font. No redistribution rights inferred.'}
    if output is not None:
        result['outputSha256'] = sha256(output.encode('ascii'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Separately obtained mntm_cn-20240803Test.tgz')
    parser.add_argument('output', type=Path, nargs='?', help='New .bdf output; never overwritten')
    parser.add_argument('--inspect', action='store_true', help='Inspect without writing a font')
    parser.add_argument('--report', type=Path, help='Optional new JSON summary; contains no bitmap rows')
    args = parser.parse_args()
    if args.inspect and (args.output or args.report):
        parser.error('--inspect does not take an output or --report.')
    if not args.inspect and not args.output:
        parser.error('Choose an output .bdf or --inspect.')
    paths = [path for path in (args.output, args.report) if path]
    if args.output and args.output.suffix.lower() != '.bdf':
        parser.error('Output must use the .bdf extension.')
    if len({path.resolve() for path in [args.source] + paths}) != len(paths) + 1:
        parser.error('Source, BDF and report paths must differ.')
    for path in paths:
        if path.exists():
            parser.error('Output already exists; choose a new filename: ' + str(path))
        if not path.parent.is_dir():
            parser.error('Output folder does not exist: ' + str(path.parent))
    try:
        if args.source.stat().st_size != ARCHIVE_SIZE:
            raise ValueError('Input size does not match the audited 20240803 TGZ.')
        font = recover(args.source.read_bytes())
        if args.inspect:
            print(json.dumps(summary(font), ensure_ascii=False, indent=2))
            return
        output = bdf_text(font)
        with args.output.open('x', encoding='ascii', newline='\n') as stream:
            stream.write(output)
        if args.report:
            with args.report.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(summary(font, output), stream, ensure_ascii=False, indent=2)
                stream.write('\n')
    except (OSError, ValueError, tarfile.TarError) as error:
        sys.exit(str(error))
    print(f'Wrote 604 Unicode glyphs (503 Han) to {args.output}.')
    print('Native bearings and advances retained. Local export does not grant redistribution rights.')


if __name__ == '__main__':
    main()
