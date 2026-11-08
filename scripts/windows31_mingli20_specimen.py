#!/usr/bin/env python3
"""Only SHA-locked fixed windows31_mingli20 PNGs. No network, arbitrary text or font export."""
import argparse, hashlib, io, os, stat
from pathlib import Path
from PIL import Image
SOURCE_BYTES = 832088
SOURCE_SHA256 = '5b0d5a506b03b9f6ab981ff220c1e14aafda7966960cc4234ba3bb6f76003b09'
TEXT = '視野無限廣，窗外有藍天。'
WIDTH, HEIGHT = 20, 20
PNG_SHA256 = {1: '692fd91faef8fed21c152ed85fb35e29af98ff210a4d4734459addbf479803a5', 4: '9d3d57d4f363802ed994503524cc564f027d1db420076895bcbf37da29fdb8e9'}

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
        if not stat.S_ISREG(info.st_mode) or info.st_size != SOURCE_BYTES or info.st_nlink != 1:
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
        code = lead * 256 + trail
        if 0xa140 <= code <= 0xa3e0:
            slot = (lead - 0xa1) * 157 + t
        elif 0xa440 <= code <= 0xc67e:
            slot = 684 + (lead - 0xa4) * 157 + t
        elif 0xc940 <= code <= 0xf9d5:
            slot = 6085 + (lead - 0xc9) * 157 + t
        else:
            raise ValueError('Fixed glyph outside mapped ranges')
        offset = 5408 + slot * 60
        raw = data[offset:offset + 60]
        if len(raw) != 60:
            raise ValueError('Fixed glyph outside source')
        cells.append(raw)
    image = Image.new('1', (WIDTH*len(TEXT), HEIGHT), 1)
    for i, raw in enumerate(cells):
        for y in range(HEIGHT):
            row = int.from_bytes(raw[y*3:(y+1)*3], 'big')
            for x in range(WIDTH):
                if not row & (1 << (23-x)):
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
