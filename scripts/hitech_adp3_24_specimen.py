#!/usr/bin/env python3
"""Only SHA-locked fixed hitech_adp3_24 PNGs. No network, arbitrary text or font export."""
import argparse, hashlib, io, os, stat
from pathlib import Path
from PIL import Image
SOURCE_BYTES = 976680
SOURCE_SHA256 = '1f46c0240a1a840f944baed0627c734351672c0dd388528313c9421d6a957121'
TEXT = '視野無限廣，窗外有藍天。'
WIDTH, HEIGHT = 24, 24
PNG_SHA256 = {1: '2d361e448715a86d80b8a9bcbdb73b2ea3ee6ceb38ef3cc895bb02ad2d7e5265', 4: 'd2d39acfbc1c5b636d3087fa8b24313c71f7179a9c2db57a2d1694d5b476de1c'}

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
            raise ValueError('Source is not the exact regular source file')
        data = stream.read(SOURCE_BYTES + 1)
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source size or SHA256 mismatch')
    return data


def fixed_image(data):
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source size or SHA256 mismatch')
    cells = []
    for char in TEXT:
        lead, trail = char.encode('big5')
        t = trail - (0x40 if trail < 0x7f else 0x62)
        slot = 157*(lead-0xa1)+t if lead < 0xc9 else 157*(lead-0xa3)+t-94
        raw = data[slot*72:(slot+1)*72]
        if len(raw) != 72:
            raise ValueError('Fixed glyph outside source')
        cells.append(raw)
    image = Image.new('1', (WIDTH*len(TEXT), HEIGHT), 1)
    for i, raw in enumerate(cells):
        for y in range(HEIGHT):
            row = int.from_bytes(raw[y*(WIDTH//8):(y+1)*(WIDTH//8)], 'big')
            for x in range(WIDTH):
                if row & (1 << (WIDTH-1-x)):
                    image.putpixel((i*WIDTH+x,y), 0)
    return image


def render(source, output, scale=1):
    if scale not in (1,4) or isinstance(scale,bool):
        raise ValueError('Only approved 1x and 4x previews')
    if Path(output).suffix.lower() != '.png':
        raise ValueError('Output must be a new .png file')
    image = fixed_image(checked_source(source))
    if scale == 4:
        image = image.resize((image.width*4,image.height*4),Image.Resampling.NEAREST)
    buffer = io.BytesIO()
    image.save(buffer,format='PNG')
    png = buffer.getvalue()
    if hashlib.sha256(png).hexdigest() != PNG_SHA256[scale]:
        raise ValueError('PNG encoder differs from approved bytes')
    parent, name = _parent_fd(output)
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,0o600,dir_fd=parent)
        with os.fdopen(fd,'wb') as stream:
            stream.write(png)
    finally:
        os.close(parent)
    return image

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--scale',type=int,choices=[1,4],default=1)
    args = parser.parse_args()
    render(args.source,args.output,args.scale)
