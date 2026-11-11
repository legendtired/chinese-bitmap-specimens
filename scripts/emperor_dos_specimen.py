#!/usr/bin/env python3
"""Offline, SHA-locked Emperor DOS fixed phrase only. No arbitrary text or font export."""

import argparse
import hashlib
import io
import os
from pathlib import Path
import stat

from PIL import Image

SOURCE_BYTES = 85740
INDEX_BYTES = 30210
INDEX_SHA256 = '867ffc028e1c8c6b6bd5085ad794c01010b4311fb28023766b6743f1067fed0d'
SOURCE_SHA256 = '6b7636fa7d34bf9406f7ba8dc55fe94db1f54d3a62a5c6c6a8084e13bf07cbc5'
TEXT = '視野無限廣，窗外有藍天。'
WIDTH, HEIGHT = 16, 15
PNG_SHA256 = {
    1: 'c81ea562f0db05813adbc1d58550e50b7ae4d57d3c78fe7e9d8fcb343e58f07f',
    4: '97f67f02a0302beb5b221bb3d4b6d3b2e44cddacaf93c63bb94bff66bec5d1ab',
}


def _parent_fd(path):
    """Walk every parent by directory FD; never follow a symlink."""
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
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd, absolute.name
    except BaseException:
        os.close(fd)
        raise


def checked_source(path, expected_bytes=SOURCE_BYTES, expected_sha=SOURCE_SHA256):
    """Read only a single-link regular file of the exact approved identity."""
    parent, name = _parent_fd(path)
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != expected_bytes:
            raise ValueError('Source must be the exact single-link regular source file')
        data = stream.read(expected_bytes + 1)
    if len(data) != expected_bytes or hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError('Source size or SHA256 mismatch')
    return data


def fixed_image(data, index):
    """Decode only the fixed twelve cells; mapping is structural, not EXE-traced."""
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source size or SHA256 mismatch')
    if len(index) != INDEX_BYTES or hashlib.sha256(index).hexdigest() != INDEX_SHA256:
        raise ValueError('Index size or SHA256 mismatch')
    image = Image.new('RGBA', (WIDTH * len(TEXT), HEIGHT), (0, 0, 0, 0))
    for number, char in enumerate(TEXT):
        lead, trail = char.encode('cp950')
        code = lead * 256 + trail
        if 0xa140 <= code <= 0xa3bf:
            base, first = 1025, 0xa1
        elif 0xa440 <= code <= 0xc67e:
            base, first = 2049, 0xa4
        elif 0xc940 <= code <= 0xf9fe:
            base, first = 7450, 0xc9
        else:
            raise ValueError('Fixed character outside recovered ranges')
        rank = (lead - first) * 157 + (trail - 0x40 if trail < 0x7f else trail - 0xa1 + 63)
        entry = base + rank
        slot = int.from_bytes(index[entry * 2:entry * 2 + 2], 'little') - 1
        if not 0 <= slot < SOURCE_BYTES // 30:
            raise ValueError('Fixed glyph absent or outside source')
        raw = data[slot * 30:(slot + 1) * 30]
        for y in range(HEIGHT):
            row = int.from_bytes(raw[y * 2:y * 2 + 2], 'big')
            for x in range(WIDTH):
                if row & (1 << (15 - x)):
                    image.putpixel((number * WIDTH + x, y), (0, 0, 0, 255))
    return image


def render(source, index, output, scale=1):
    if type(scale) is not int or scale not in (1, 4):
        raise ValueError('Only approved integer 1x and 4x previews')
    if Path(output).suffix.lower() != '.png':
        raise ValueError('Output must be a new .png file')
    image = fixed_image(checked_source(source), checked_source(index, INDEX_BYTES, INDEX_SHA256))
    if scale == 4:
        image = image.resize((image.width * 4, image.height * 4), Image.Resampling.NEAREST)
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
    parser.add_argument('--index', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--scale', type=int, choices=(1, 4), default=1)
    args = parser.parse_args()
    render(args.source, args.index, args.output, args.scale)
