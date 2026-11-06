#!/usr/bin/env python3
"""Offline Samsung R20ZCVI1 bitmap reader. Python standard library only.

No embedded glyphs, downloads, source execution, rasterizers or fallback fonts.
Default outputs: one fixed specimen PNG and an aggregate report. Optional BDF is
for local use only, subject to rights in the source. Never publish the firmware,
full BDF or full glyph data. Input and output paths must not contain symlinks.
"""
import argparse
import binascii
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys
import zlib

AXF_SIZE = 1976056
OGM_SIZE = 1178788
AXF_SHA256 = '4c8d54f97d2c05f34b8cf9995fad1a4ba75fbb942c8dd8b49602fb70e931d521'
OGM_SHA256 = 'a7f2e4bd228b31937eb0ad47170592a1ec21b35801ae2086c00e9be686dab629'
HAN_INDEX = 0xad7e
HAN_BITMAP = 0x127ba
HAN_RECORDS = 15646
LATIN_BASE = 0x17eec0
PERIOD_OFFSET = 0x8cbda
PHRASE = '视野无限广，窗外有蓝天。'
ASCII = '0123456789 AaBb GgMm !?:+-.'
PNG_NAME = 'samsung_r208_16.png'
REPORT_NAME = 'samsung-r208-report.json'
BDF_NAME = 'samsung-r208-local-only.bdf'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _path_parts(path):
    # Do not resolve: resolution would silently follow symlinks.
    value = os.fspath(path)
    require(isinstance(value, str) and value and '\x00' not in value, 'Invalid path')
    require('..' not in value.split('/'), 'Parent traversal is not accepted')
    p = Path(os.path.abspath(value))
    require(p.name not in ('', '.', '..'), 'Root is not a file/output destination')
    return p


def open_directory(path):
    """Open each directory component relative to a pinned directory descriptor."""
    require(hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY'),
            'Safe path handling requires POSIX O_NOFOLLOW and O_DIRECTORY')
    p = Path(os.path.abspath(os.fspath(path)))
    require('..' not in os.fspath(path).split('/'), 'Parent traversal is not accepted')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in p.parts[1:]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_source(path, size, digest):
    p = _path_parts(path)
    parent = open_directory(p.parent)
    try:
        fd = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode), 'Source must be a regular file')
            require(info.st_size == size, 'Unrecognized source length')
            data = bytearray()
            while len(data) <= size:
                chunk = os.read(fd, min(65536, size + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
            require(len(data) == size and sha(data) == digest, 'Unrecognized source SHA256')
            return bytes(data)
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def decode_rows(raw, width, height=16):
    require(width in (8, 16) and height == 16, 'Only verified 8/16 by 16 cells are supported')
    require(len(raw) == width * 2, 'Incorrect bitmap extent')
    rows = [sum(((raw[(y//8)*width+x] >> (y%8)) & 1) << (width-1-x)
                for x in range(width)) for y in range(height)]
    return dict(width=width, height=height, rows=rows)


def gb2312_han():
    result = set()
    for hi in range(0xb0, 0xf8):
        for lo in range(0xa1, 0xff):
            try:
                result.add(ord(bytes((hi, lo)).decode('gb2312')))
            except UnicodeDecodeError:
                pass
    require(len(result) == 6763, 'Unexpected standard GB2312 codec')
    return result


def decode(axf, ogm):
    # Gate again for callers that bypass read_source().
    require(len(axf) == AXF_SIZE and sha(axf) == AXF_SHA256, 'Unrecognized AXF length/SHA256')
    require(len(ogm) == OGM_SIZE and sha(ogm) == OGM_SHA256, 'Unrecognized OGM length/SHA256')
    require(axf[0x4e6c:0x4e77] == b'Sep 06 2002', 'Unexpected firmware date')
    codes = struct.unpack_from('<15646H', ogm, HAN_INDEX)
    require(list(codes) == sorted(set(codes)), 'Unsorted/duplicate Unicode table')
    require(codes[-1] == 0x9fa6 and all(0x4e00 <= c <= 0x9fa6 for c in codes),
            'Unexpected Han table range')
    glyphs = {c: decode_rows(ogm[HAN_BITMAP+i*32:HAN_BITMAP+(i+1)*32], 16)
              for i, c in enumerate(codes)}
    require(not any(glyphs.pop(0x9fa6)['rows']), 'Expected blank fallback sentinel')
    require(len(glyphs) == 15645 and all(any(g['rows']) for g in glyphs.values()),
            'Unexpected supported Han count or blank Han')
    require(gb2312_han() <= glyphs.keys(), 'Missing GB2312 Han')
    require((axf[0x158610+4], axf[0x158604+4], axf[0x15861c+4]) == (8, 16, 16),
            'Unexpected Western index 4 dimensions')
    require(struct.unpack_from('<I', axf, 0x1868c0+4*4)[0] == LATIN_BASE,
            'Unexpected Western index 4 pointer')
    for cp in range(32, 127):
        glyphs[cp] = decode_rows(axf[LATIN_BASE+cp*16:LATIN_BASE+(cp+1)*16], 8)
    require(not any(glyphs[32]['rows']) and all(any(glyphs[c]['rows']) for c in range(33, 127)),
            'Unexpected printable ASCII coverage')
    # Only U+3002 and U+FF0C are included among non-ASCII symbols. This is NOT a
    # complete symbol-table emulator. The separate renderer audit pins the paths.
    punctuation = struct.unpack_from('<16H', ogm, 0x8cb7a)
    require(punctuation.index(0x3002) == 2, 'Unexpected U+3002 lookup index')
    glyphs[0x3002] = decode_rows(ogm[PERIOD_OFFSET:PERIOD_OFFSET+32], 16)
    glyphs[0xff0c] = dict(glyphs[ord(',')], rows=list(glyphs[ord(',')]['rows']))
    require(len(glyphs) == 15742, 'Unexpected export count')
    return glyphs


def specimen_pixels(glyphs):
    # Match the reviewed research specimen: 4px outer margins, 4px line gap,
    # no inserted inter-character gap; preserve the actual 8px comma cell.
    lines = [PHRASE, ASCII]
    widths = [sum(glyphs[ord(c)]['width'] for c in text) for text in lines]
    width, height = max(widths)+8, 44
    pixels = bytearray([255]) * (width*height)
    for line, text in enumerate(lines):
        x, y0 = 4, 4+20*line
        for char in text:
            g = glyphs[ord(char)]
            for y, row in enumerate(g['rows']):
                for xx in range(g['width']):
                    if row & (1 << (g['width']-1-xx)):
                        pixels[(y0+y)*width+x+xx] = 0
            x += g['width']
    return width, height, bytes(pixels)


def png_bytes(width, height, pixels):
    require(width > 0 and height > 0 and len(pixels) == width*height, 'Invalid PNG pixels')
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', binascii.crc32(kind+data)&0xffffffff)
    raw = b''.join(b'\0'+pixels[y*width:(y+1)*width] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0))+
            chunk(b'IDAT', zlib.compress(raw, 9))+chunk(b'IEND', b''))


def bdf_bytes(glyphs):
    # Explicit export convention, NOT a claim about handset baseline/placement.
    lines = ['STARTFONT 2.1',
             'COMMENT Local-only export; not an openly licensed font.',
             'COMMENT Top-aligned stored cells; bottom=0 ascent=16 descent=0.',
             'COMMENT Original handset baseline and complete shaping are unverified.',
             'COMMENT U+FF0C aliases the native 8px Latin comma, not a 16px cell.',
             'FONT -research-SamsungR208-medium-r-normal--16-160-75-75-c-160-iso10646-1',
             'SIZE 16 75 75', 'FONTBOUNDINGBOX 16 16 0 0', 'STARTPROPERTIES 4',
             'FONT_ASCENT 16', 'FONT_DESCENT 0', 'CHARSET_REGISTRY "ISO10646"',
             'CHARSET_ENCODING "1"', 'ENDPROPERTIES', f'CHARS {len(glyphs)}']
    for cp, g in sorted(glyphs.items()):
        w, h = g['width'], g['height']
        require(w in (8, 16) and h == 16 and len(g['rows']) == h, 'Unexpected BDF cell')
        require(all(0 <= row < (1 << w) for row in g['rows']), 'BDF row outside cell')
        # SWIDTH = width * 72000 / (point-size * dpi): 960 or 480.
        lines += [f'STARTCHAR U{cp:04X}', f'ENCODING {cp}', f'SWIDTH {w*60} 0',
                  f'DWIDTH {w} 0', f'BBX {w} 16 0 0', 'BITMAP']
        lines.extend(f'{row:0{w//4}X}' for row in g['rows'])
        lines.append('ENDCHAR')
    return ('\n'.join(lines+['ENDFONT'])+'\n').encode('ascii')


def make_report(axf, ogm, glyphs, png):
    width, height = struct.unpack_from('>II', png, 16)
    phrase_width = sum(glyphs[ord(c)]['width'] for c in PHRASE)
    ascii_width = sum(glyphs[ord(c)]['width'] for c in ASCII)
    return dict(model='Samsung SGH-R208', firmware='R20ZCVI1', embeddedBuildDate='2002-09-06',
                axfSha256=sha(axf), ogmSha256=sha(ogm), sourceHanRecords=15646,
                supportedNonblankHan=15645, blankFallback='U+9FA6 excluded', gb2312Han=6763,
                gb2312All7445Characters='Not verified; no full GB2312 symbol coverage claim',
                printableAscii=95, westernFontIndex=4, hanCell=[16,16], asciiCell=[8,16],
                exportedSymbols=['U+3002 stored 16x16', 'U+FF0C renderer alias to 8x16 ASCII comma'],
                exportedGlyphs=len(glyphs), runtimeBaseline=None,
                runtimeAdvance='Latin path returns width 8; complete handset layout unverified',
                specimen=dict(file=PNG_NAME, sha256=sha(png), width=width, height=height,
                              phrase=PHRASE, ascii=ASCII, phraseWidth=phrase_width, asciiWidth=ascii_width,
                              outerMargin=4, lineGap=4, insertedCharacterGap=0),
                bdfConvention='75dpi, SIZE16, SWIDTH960/480; stored cell top-alignment, bottom0/ascent16/descent0, not recovered device baseline',
                rights='Proprietary source; limited fixed specimen and source-only method. No firmware/full font distribution.',
                limits='Static reconstruction, not a phone screenshot. Index4 is evidenced in this path, not necessarily every UI context.')


def write_new_directory(output, payloads):
    """Refuse existing outputs and symlinks; validate everything before writing.

    Requires an existing parent. Creates a new exclusive destination, pins it by
    descriptor, and rolls it back on a write failure. Never overwrites anything.
    """
    p = _path_parts(output)
    require(payloads and all(isinstance(k, str) and Path(k).name == k and k not in ('.','..')
                            and '/' not in k and '\x00' not in k and isinstance(v, bytes)
                            for k,v in payloads.items()), 'Invalid output payload')
    parent = open_directory(p.parent)
    fd = None
    created = False
    names = []
    inode = None
    try:
        os.mkdir(p.name, mode=0o700, dir_fd=parent)  # Atomic fail if anything exists.
        created = True
        inode = os.stat(p.name, dir_fd=parent, follow_symlinks=False)
        fd = os.open(p.name, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=parent)
        info = os.fstat(fd)
        require((info.st_dev, info.st_ino) == (inode.st_dev, inode.st_ino), 'Output directory changed')
        for name, data in payloads.items():
            f = os.open(name, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600, dir_fd=fd)
            names.append(name)
            try:
                view = memoryview(data)
                while view:
                    count = os.write(f, view)
                    require(count > 0, 'Short output write')
                    view = view[count:]
                os.fsync(f)
            finally:
                os.close(f)
        os.fsync(fd)
    except BaseException:
        if fd is not None:
            for name in names:
                os.unlink(name, dir_fd=fd)
        if created:
            now = os.stat(p.name, dir_fd=parent, follow_symlinks=False)
            if inode is not None and (now.st_dev, now.st_ino) == (inode.st_dev, inode.st_ino):
                os.rmdir(p.name, dir_fd=parent)
        raise
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('axf', help='Exact local R20ZCVI1.axf')
    parser.add_argument('ogm', help='Exact local R20ZCVI1.ogm')
    parser.add_argument('--output', required=True, help='New absent directory under an existing non-symlink parent')
    parser.add_argument('--export-bdf', action='store_true', help='Additionally write local-only complete BDF')
    args = parser.parse_args(argv)
    try:
        axf = read_source(args.axf, AXF_SIZE, AXF_SHA256)
        ogm = read_source(args.ogm, OGM_SIZE, OGM_SHA256)
        glyphs = decode(axf, ogm)
        png = png_bytes(*specimen_pixels(glyphs))
        report = make_report(axf, ogm, glyphs, png)
        payloads = {PNG_NAME: png, REPORT_NAME: (json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode()}
        if args.export_bdf:
            payloads[BDF_NAME] = bdf_bytes(glyphs)
        write_new_directory(args.output, payloads)
    except (OSError, ValueError, struct.error) as exc:
        parser.exit(2, f'error: {exc}\n')
    print(f'Wrote {len(payloads)} files to a new directory; no source files changed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
