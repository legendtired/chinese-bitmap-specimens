#!/usr/bin/env python3
"""Offline, SHA-locked DEADF fixed phrase only. No arbitrary text or font export."""

import argparse
import hashlib
import io
import os
from pathlib import Path
import stat

from PIL import Image

SOURCE_BYTES = 452832
SOURCE_SHA256 = '438ac6da4f212fbdf2098e0828786177ffdd25ec1d93225d9113298be7e43967'
TEXT = '視野無限廣，窗外有藍天。'
WIDTH, HEIGHT = 16, 16
PNG_SHA256 = {
    1: '023a138be5fe1df233fd8dccafb4e35b41ee0180287255b467d353f5062d3293',
    4: '35f04e67d53acec55146b72018860103bbf568673eec331e488e01334209232a',
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


def checked_source(path):
    """Read only a single-link regular file of the exact approved identity."""
    parent, name = _parent_fd(path)
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != SOURCE_BYTES:
            raise ValueError('Source must be the exact single-link regular source file')
        data = stream.read(SOURCE_BYTES + 1)
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source size or SHA256 mismatch')
    return data


def fixed_image(data):
    """Decode only the twelve approved cells, preserving all 16 rows and columns."""
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source size or SHA256 mismatch')
    image = Image.new('RGBA', (WIDTH * len(TEXT), HEIGHT), (0, 0, 0, 0))
    for index, char in enumerate(TEXT):
        lead, trail = char.encode('big5')
        # Original DF.ORI arithmetic retains the physical 7F and A0 slots.
        slot = (lead - 0xa1) * 159 + trail - 0x40 - (32 if trail >= 0xa0 else 0)
        raw = data[slot * 32:(slot + 1) * 32]
        if len(raw) != 32:
            raise ValueError('Fixed glyph outside source')
        for y in range(HEIGHT):
            row = int.from_bytes(raw[y * 2:y * 2 + 2], 'big')
            for x in range(WIDTH):
                if row & (1 << (15 - x)):
                    image.putpixel((index * WIDTH + x, y), (0, 0, 0, 255))
    return image


def render(source, output, scale=1):
    if type(scale) is not int or scale not in (1, 4):
        raise ValueError('Only approved integer 1x and 4x previews')
    if Path(output).suffix.lower() != '.png':
        raise ValueError('Output must be a new .png file')
    image = fixed_image(checked_source(source))
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
    parser.add_argument('--output', required=True)
    parser.add_argument('--scale', type=int, choices=(1, 4), default=1)
    args = parser.parse_args()
    render(args.source, args.output, args.scale)
