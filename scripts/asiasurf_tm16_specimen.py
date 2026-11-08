#!/usr/bin/env python3
"""Offline AsiaSurf TM16 fixed ten-Han preview, without embedded glyph data."""

import argparse
import hashlib
import io
import os
from pathlib import Path
import stat
import struct

from PIL import Image

TEXT = '視野無限廣窗外有藍天'
WIDTH, HEIGHT = 16, 16
SOURCE_NAME = 'DLM_TM.WKF'
SOURCE_BYTES = 790002
SOURCE_SHA256 = '669c1e9acf8d20eb1598355387ebdb1234af9e5900095f9904e858cdc23c6e55'
DBCS_OFFSET = 342866
DBCS_SLOTS = 13973
# Only this phrase's original Big5 codes, slots and offsets, never glyph pixels.
FIXED = (
    ('視', 0xb5f8, 3290, 448146),
    ('野', 0xb3a5, 2893, 435442),
    ('無', 0xb54c, 3152, 443730),
    ('限', 0xadad, 1959, 405554),
    ('廣', 0xbc73, 4290, 480146),
    ('窗', 0xb5a1, 3203, 445362),
    ('外', 0xa57e, 690, 364946),
    ('有', 0xa6b3, 866, 370578),
    ('藍', 0xc2c5, 5280, 511826),
    ('天', 0xa4d1, 582, 361490),
)
PNG_SHA256 = {
    1: '2effe5e9f6f64d1ace4e34f70ba740ad0da5cf4be5f7acc9e77314007d03a321',
    4: '7341fe4087afc67fcdf3d4e99e588834b1121a0125b79aceff04379c3e9de57f',
}


def _parent_fd(path):
    """Walk each existing directory by descriptor; never follow symbolic links."""
    if not all(hasattr(os, name) for name in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')):
        raise RuntimeError('Safe file access requires POSIX no-follow support')
    value = os.fspath(path)
    if not isinstance(value, str) or not value or '\0' in value or '..' in value.split('/'):
        raise ValueError('Use a file path without parent traversal')
    absolute = Path(os.path.abspath(value))
    if not absolute.name:
        raise ValueError('A file name is required')
    fd = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd, absolute.name
    except BaseException:
        os.close(fd)
        raise


def validate_layout(data):
    """Check original WKF metadata; the 12px header is identity, not an output."""
    if len(data) != SOURCE_BYTES or data[256:264] != bytes.fromhex('c4f9eee1c6efeef4'):
        raise ValueError('WKF size or DynaFont signature mismatch')
    u16 = lambda offset: struct.unpack_from('<H', data, offset)[0]
    u32 = lambda offset: struct.unpack_from('<I', data, offset)[0]
    if u32(270) != 137 or u16(274) != 1 or u32(294) != 12:
        raise ValueError('WKF record base, Big5 encoding or bitmap table differs')
    if (u16(298), u16(300), u32(302), u32(306)) != (256, 2, 12, 338454):
        raise ValueError('WKF layer table differs')
    for start, size, dbcs_relative, next_boundary in ((310, 12, 3090, 338752),
                                                     (338752, 16, 4114, SOURCE_BYTES)):
        actual = struct.unpack_from('<HHBBHHII', data, start)
        if actual != (size, size, 0, 255, 0xa140, 0xf9fe, 18, dbcs_relative):
            raise ValueError('Original layer dimensions, ranges or offsets differ')
        single_stride = ((size // 2 + 7) // 8) * size
        dbcs_stride = ((size + 7) // 8) * size
        if start + 18 + 256 * single_stride != start + dbcs_relative:
            raise ValueError('Physical single-byte storage boundary differs')
        if start + dbcs_relative + DBCS_SLOTS * dbcs_stride != next_boundary:
            raise ValueError('DBCS layer boundary differs')
    if 338752 + 4114 != DBCS_OFFSET or DBCS_OFFSET + DBCS_SLOTS * 32 != len(data):
        raise ValueError('TM16 source boundary differs')


def checked_source(path):
    """Require an exact-size, SHA-locked, single-link ordinary local file."""
    parent, filename = _parent_fd(path)
    try:
        fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != SOURCE_BYTES:
            raise ValueError('Source must be an exact-size single-link regular file')
        data = stream.read(SOURCE_BYTES + 1)
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source size or SHA256 mismatch')
    validate_layout(data)
    return data


def fixed_image(data):
    """Read the approved ten source cells only. No arbitrary text or map input."""
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source size or SHA256 mismatch')
    validate_layout(data)
    if len(FIXED) != 10 or ''.join(item[0] for item in FIXED) != TEXT:
        raise ValueError('Fixed phrase changed')
    image = Image.new('RGBA', (160, 16), (0, 0, 0, 0))
    for index, (char, code, slot, offset) in enumerate(FIXED):
        lead, trail = code >> 8, code & 255
        if not (0xa1 <= lead <= 0xf9 and (0x40 <= trail <= 0x7e or 0xa1 <= trail <= 0xfe)):
            raise ValueError('Invalid original Big5 code')
        original_slot = (lead - 0xa1) * 157 + trail - 0x40 - (34 if trail > 0x7e else 0)
        if slot != original_slot or not 0 <= slot < DBCS_SLOTS or offset != DBCS_OFFSET + slot * 32:
            raise ValueError('Fixed code, slot or offset differs from original lookup')
        raw = data[offset:offset + 32]
        if len(raw) != 32:
            raise ValueError('Fixed glyph outside source')
        for y in range(16):
            row = int.from_bytes(raw[y * 2:y * 2 + 2], 'big')
            for x in range(16):
                if not row & (1 << (15 - x)):
                    image.putpixel((16 * index + x, y), (0, 0, 0, 255))
    return image


def render(source, output, scale=1):
    if type(scale) is not int or scale not in (1, 4):
        raise ValueError('Only approved integer 1x and 4x previews')
    if Path(output).suffix.lower() != '.png':
        raise ValueError('Output must be a new .png file')
    image = fixed_image(checked_source(source))
    if scale == 4:
        image = image.resize((640, 64), Image.Resampling.NEAREST)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    png = buffer.getvalue()
    if hashlib.sha256(png).hexdigest() != PNG_SHA256[scale]:
        raise ValueError('PNG encoder differs from approved bytes')
    parent, name = _parent_fd(output)
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(png)
    finally:
        os.close(parent)
    return image


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--scale', type=int, choices=(1, 4), default=1)
    args = parser.parse_args()
    render(args.source, args.output, args.scale)
