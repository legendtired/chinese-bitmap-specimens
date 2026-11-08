#!/usr/bin/env python3
"""Offline RichWin fixed ten-Han preview. No bitmap data or arbitrary text export."""

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
# Source identities and original RSE metadata, not glyph data.
SOURCES = {
    'GB16ST.RSF': {'bytes': 216664, 'sha256': 'e210c3c3edc359bf9bfd7ffc664946f794962ae85f433e7841225c9b3339933e',
                   'encoding': 1, 'range': (0xb0a1, 0xf7fe), 'slots': 6768},
    'CBST16E1.RSF': {'bytes': 75352, 'sha256': '562a48053bcfe87d53fa8f9e5a9a37c7fb18c95502bebe697ceb2aec993cde5d',
                    'encoding': 21, 'range': (0x81a1, 0x9aa2), 'slots': 2352},
    'CBST16E2.RSF': {'bytes': 377272, 'sha256': 'f9ff7bd921947fb44600d241a67662b4ccfae70fd2bc0a5f97b36140fe39c46a',
                    'encoding': 21, 'range': (0x8130, 0xfe61), 'slots': 11787},
}
# Only the approved phrase's original file, slot, byte offset and target code.
# E2 belongs to the original family but contributes zero glyphs to this phrase.
FIXED = (
    ('視', 'CBST16E1.RSF', 797, 25592, 0x89ce),
    ('野', 'GB16ST.RSF', 3211, 102840, 0xd2b0),
    ('無', 'CBST16E1.RSF', 908, 29144, 0x8adf),
    ('限', 'GB16ST.RSF', 2975, 95288, 0xcfde),
    ('廣', 'CBST16E1.RSF', 269, 8696, 0x83f2),
    ('窗', 'GB16ST.RSF', 391, 12600, 0xb4b0),
    ('外', 'GB16ST.RSF', 2791, 89400, 0xcde2),
    ('有', 'GB16ST.RSF', 3337, 106872, 0xd3d0),
    ('藍', 'CBST16E1.RSF', 472, 15192, 0x86a3),
    ('天', 'GB16ST.RSF', 2707, 86712, 0xccec),
)
PNG_SHA256 = {
    1: 'a5566e5e840fbb4e9946f87cef2641cdf842616dad07329744886eb757aad61a',
    4: '0954bf116d377000d09fad53980a3af25ee5c477902c4827ff839b3d42736b42',
}


def _parent_fd(path):
    """Walk each directory by descriptor, never following a symlink."""
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


def validate_layout(name, data):
    """Validate original header/ranges; does not assign meanings to unknown fields."""
    spec = SOURCES[name]
    if len(data) != spec['bytes'] or len(data) != 88 + spec['slots'] * 32:
        raise ValueError('RSE size/count mismatch')
    if data[:6] != b'RSE\x1a\x01\x00':
        raise ValueError('Not the approved RSE container')
    u16 = lambda offset: struct.unpack_from('<H', data, offset)[0]
    limits = (int.from_bytes(data[0x18:0x1a], 'big'), int.from_bytes(data[0x1c:0x1e], 'big'))
    if (u16(0x10), u16(0x12), u16(0x14), u16(0x16)) != (spec['encoding'], 128, 16, 16):
        raise ValueError('RSE encoding, class or dimensions differ')
    if limits != spec['range'] or data[0x20:0x25] != b'\xcb\xce\xcc\xe5\0':
        raise ValueError('Original range or Song family differs')
    if u16(0x48) != 72 or u16(0x50) != 32 or u16(0x52) != spec['slots']:
        raise ValueError('RSE header length, stride or count differs')


def checked_source(name, path):
    """Read an exact-size, SHA-locked, single-link ordinary local file."""
    spec = SOURCES[name]
    parent, filename = _parent_fd(path)
    try:
        fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != spec['bytes']:
            raise ValueError('Source must be an exact-size single-link regular file')
        data = stream.read(spec['bytes'] + 1)
    if len(data) != spec['bytes'] or hashlib.sha256(data).hexdigest() != spec['sha256']:
        raise ValueError('Source size or SHA256 mismatch')
    validate_layout(name, data)
    return data


def fixed_image(sources):
    """Read only ten fixed original cells; never accept arbitrary source mappings."""
    if set(sources) != set(SOURCES):
        raise ValueError('All three original RSF sources are required')
    for name, data in sources.items():
        if len(data) != SOURCES[name]['bytes'] or hashlib.sha256(data).hexdigest() != SOURCES[name]['sha256']:
            raise ValueError('Source size or SHA256 mismatch')
        validate_layout(name, data)
    image = Image.new('RGBA', (160, 16), (255, 255, 255, 0))
    for index, (char, name, slot, offset, code) in enumerate(FIXED):
        spec = SOURCES[name]
        if char != TEXT[index] or offset != 88 + slot * 32 or not 0 <= slot < spec['slots']:
            raise ValueError('Fixed source slot outside approved layout')
        if not spec['range'][0] <= code <= spec['range'][1]:
            raise ValueError('Fixed code outside original range')
        raw = sources[name][offset:offset + 32]
        if len(raw) != 32:
            raise ValueError('Fixed glyph outside source')
        for y in range(16):
            row = int.from_bytes(raw[y * 2:y * 2 + 2], 'big')
            for x in range(16):
                if row & (1 << (15 - x)):
                    image.putpixel((16 * index + x, y), (0, 0, 0, 255))
    return image


def render(gb_source, e1_source, e2_source, output, scale=1):
    if type(scale) is not int or scale not in (1, 4):
        raise ValueError('Only approved integer 1x and 4x previews')
    if Path(output).suffix.lower() != '.png':
        raise ValueError('Output must be a new .png file')
    paths = dict(zip(SOURCES, (gb_source, e1_source, e2_source)))
    image = fixed_image({name: checked_source(name, path) for name, path in paths.items()})
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
    parser.add_argument('--gb-source', required=True)
    parser.add_argument('--e1-source', required=True)
    parser.add_argument('--e2-source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--scale', type=int, choices=(1, 4), default=1)
    args = parser.parse_args()
    render(args.gb_source, args.e1_source, args.e2_source, args.output, args.scale)
