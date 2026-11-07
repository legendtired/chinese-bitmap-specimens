#!/usr/bin/env python3
"""Rebuild only the approved three-line Xelibri font-4 specimen.

Reads one SHA-locked local SW511 CLA. No network, firmware execution,
arbitrary text, other font layers, glyph-array output, or font/subset export.
The source is a third-party preserved firmware, not manufacturer authentication.
Requires Python 3.9+, Pillow and POSIX no-follow file-descriptor support.
"""
import argparse
import hashlib
import io
import os
from pathlib import Path
import stat
import struct

from PIL import Image

SOURCE_BYTES = 3145732
SOURCE_SHA256 = '3d8047d15f91249e6ec8f2d5f97338b7f8368445e04c32d16476134a48c3afa0'
SPECIMEN_SHA256 = '047cf9b058da58738e47025836496fa71b2c6e660d54729ef43aec0749673b51'
LINES = ('视野无限广，窗外有蓝天。', '視野無限廣，窗外有藍天。')
ASCII = 'AaBbCc 0123456789'
FONT = 4


def _parent_fd(path):
    """Open each parent without following symlinks, including ancestors."""
    if not all(hasattr(os, name) for name in ('O_NOFOLLOW', 'O_DIRECTORY')):
        raise RuntimeError('Safe no-follow file access requires POSIX support')
    absolute = Path(os.path.abspath(os.fspath(path)))
    fd = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd, absolute.name
    except BaseException:
        os.close(fd)
        raise


def checked_source(path):
    """Reject links/nonregular files and verify size and SHA before parsing."""
    parent, name = _parent_fd(path)
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != SOURCE_BYTES:
            raise ValueError('Source is not the exact regular SW511 file')
        data = stream.read(SOURCE_BYTES + 1)
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source size or SHA256 mismatch')
    return data


def _source_cp(cp):
    # Native 0x26280–0x26290 aliases fullwidth ASCII to same-layer ASCII.
    return cp - 0xfee0 if 0xff01 <= cp <= 0xff5e else cp


def fixed_glyphs(data):
    """Parse original maps and decompress only this specimen's characters."""
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source size or SHA256 mismatch')
    u16 = lambda p: struct.unpack_from('>H', data, p)[0]
    u32 = lambda p: struct.unpack_from('>I', data, p)[0]
    u24 = lambda p: int.from_bytes(data[p:p+3], 'big')
    descriptor, bitmap_base = struct.unpack_from('>II', data, 0x17c7f0 + FONT*12)
    height = data[0x17c7f8 + FONT*12]
    if height != 14:
        raise ValueError('Unexpected native font height')
    tables = [u32(0x26c510+i*4) for i in range(2)]
    if tables != [0x17ca15, 0x17ca2b]:
        raise ValueError('Unexpected native entropy table pointers')
    wanted = {_source_cp(ord(c)) for line in (*LINES, ASCII) for c in line}
    found = {}

    def lookup(at, cp):
        p, first, last, end, width, kind, metric, _ = struct.unpack_from('>IHHHBBBB', data, at)
        if not p:
            return None
        offset = None
        if kind == 1:
            n = cp-first
            if 0 <= n <= (end-3)//2:
                delta = u16(p+1+2*(n & 255)) if n else 0
                if n == 0 or delta:
                    offset = u24(p)+delta
        elif kind == 0:
            for index in range(0, last+1, 3):
                if data[p+index] != cp >> 8:
                    continue
                q = u16(p+index+1)
                stop = u16(p+index+4) if index < last else end
                low = cp & 255
                while q < stop:
                    count = (data[p+q] & 7)+1
                    low0 = data[p+q+3]
                    last_delta = data[p+q+count+2] >> 5
                    if low < low0:
                        break
                    if low <= low0+last_delta:
                        value = ((data[p+q] >> 3) << 16) | u16(p+q+1)
                        if low == low0:
                            offset = value
                        else:
                            for k in range(1, count):
                                part = data[p+q+3+k]
                                value += part & 31
                                if part >> 5 == low-low0:
                                    offset = value
                                    break
                        break  # Native first containing block semantics.
                    q += count+3
                break
        else:
            raise ValueError('Unexpected native mapping type')
        if offset is None:
            return None
        address = bitmap_base+offset
        if width == 255:
            width = data[address]
            address += 1
        if not 0 < width < 128 or not bitmap_base <= address < 0x17331e:
            raise ValueError('Invalid native glyph bounds')
        return address, width, metric

    def decompress(address, width):
        # Logical storage is MSB-first column-major, with columns padded to
        # whole bytes. Preserve every native 14-high rectangle without crop.
        stride = (height+7) & ~7
        packed = bytearray(width*(stride//8))
        remaining = [-1 if data[t+1] else 1 << 30 for t in tables]
        repeat, flip = [0, 0], [0, 0]
        context = previous = bit = 0
        for i in range(width*stride):
            c = context | previous
            for j, shift in ((i-stride+2, 3), (i-2*stride+2, 9), (i-3*stride, 14)):
                if j >= 0:
                    c |= ((packed[j//8] >> (7-j%8)) & 1) << shift
            if i % stride < height:
                predicted = (data[0x17ca35+c//4] >> ((c%4)*2)) & 3
                stream, previous = predicted >> 1, predicted & 1
                remaining[stream] -= 1
                if remaining[stream] < 0:
                    position, shift = address+bit//8, bit%8
                    window = ((data[position] << 8 | data[position+1]) >> (8-shift)) & 255
                    t = tables[stream]
                    for k in range(data[t+2]):
                        bound = data[t+3+2*k]
                        if bound and window <= bound:
                            break
                    else:
                        raise ValueError('Invalid native entropy code')
                    length = k+1
                    bit += length
                    symbol_index = data[t+4+2*k]-((bound-window) >> (8-length))
                    symbol = data[t+3+2*data[t+2]+symbol_index]
                    base = data[t]
                    if symbol < base:
                        remaining[stream], repeat[stream], flip[stream] = symbol+1, 0, 1
                    elif data[t+1] > 1 and symbol == base and repeat[stream]:
                        remaining[stream], flip[stream] = 1 << 30, 0
                    else:
                        remaining[stream] = (symbol+1-base)*base
                        repeat[stream], flip[stream] = int(symbol == base), 0
                    remaining[stream] -= 1
                if remaining[stream] == 0:
                    previous ^= flip[stream]
                packed[i//8] |= previous << (7-i%8)
            else:
                previous = 0
            context = (c << 1) & 0x3df6
        pixels = bytes(255-255*((packed[(x*stride+y)//8] >> (7-y%8)) & 1)
                       for y in range(height) for x in range(width))
        return Image.frombytes('L', (width, height), pixels)

    for cp in wanted:
        for script in range(14):
            first, last = struct.unpack_from('>HH', data, 0x17c868+script*8)
            if first <= cp <= last:
                if data[0x17c86c+script*8] != 0:
                    raise ValueError('Unsupported native stream flag')
                item = lookup(descriptor+script*16, cp)
                if item is None:
                    raise ValueError('Fixed specimen character missing from source')
                address, width, metric = item
                if 0x4e00 <= cp <= 0x9fff and (width, metric) != (14, 14):
                    raise ValueError('Unexpected native Han metrics')
                found[cp] = decompress(address, width)
                break
        else:
            raise ValueError('Fixed specimen character outside native ranges')
    if set(found) != wanted:
        raise ValueError('Incomplete fixed specimen')
    return found


def render(source, output):
    """Write one new fixed PNG; never overwrite any existing path or source."""
    if Path(output).suffix.lower() != '.png':
        raise ValueError('Output must be a new .png file')
    glyphs = fixed_glyphs(checked_source(source))
    texts = (*LINES, ASCII)
    widths = [sum(glyphs[_source_cp(ord(c))].width+1 for c in text)-1 for text in texts]
    image = Image.new('L', (max(widths), 50), 255)
    for line, text in enumerate(texts):
        x = 0
        for c in text:
            glyph = glyphs[_source_cp(ord(c))]
            image.paste(glyph, (x, line*18))
            x += glyph.width+1  # Ordinary native advance; not a new bitmap column.
    if image.size != (168, 50):
        raise ValueError('Unexpected fixed specimen size')
    encoded = io.BytesIO()
    image.save(encoded, format='PNG')
    png = encoded.getvalue()
    # The approved image is fixed byte-for-byte, not silently substituted by
    # another encoder result. A different Pillow encoder must be reviewed.
    if hashlib.sha256(png).hexdigest() != SPECIMEN_SHA256:
        raise ValueError('PNG bytes differ from the approved specimen')
    parent, name = _parent_fd(output)
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(png)
    finally:
        os.close(parent)
    return image


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Exact local SW511 CLA file')
    parser.add_argument('--output', required=True, help='New .png path; existing parents only; no symlinks')
    args = parser.parse_args()
    render(args.source, args.output)
