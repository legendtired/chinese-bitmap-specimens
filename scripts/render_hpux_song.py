#!/usr/bin/env python3
"""Redraw only the approved Chinese Song40 sample from an exact local PCF."""
import argparse, hashlib, json
from pathlib import Path
from PIL import Image
from render_hpux_sung import parse
ROOT = Path(__file__).resolve().parents[1]
CHINESE = '视野无限广，窗外有蓝天。'

def render(source):
    data = source.read_bytes()
    manifest = json.loads((ROOT/'data/hpux-song-sources.json').read_text())
    if hashlib.sha256(data).hexdigest() != manifest['pcfSha256']:
        raise ValueError('Unexpected PCF hash')
    props, metrics, bitmaps, enc = parse(data)
    if props[b'CHARSET_REGISTRY'] != b'GB2312.1980':
        raise ValueError('Unexpected encoding')
    out = Image.new('RGBA', (488, 48), (255, 255, 255, 0))
    for i, char in enumerate(CHINESE):
        code = int.from_bytes(char.encode('gb2312'), 'big')
        index = enc[code]
        if tuple(metrics[index]) != (40, 40, 0, 40, 40, 34, 6, 0):
            raise ValueError('Unexpected source metrics')
        bitmap = bitmaps[index]
        if not bitmap.getbbox(): raise ValueError('Blank sample glyph')
        out.paste(Image.new('RGBA', bitmap.size, (28, 31, 33, 255)), (4+i*40, 4), bitmap)
    return out

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Output must not already exist')
    image = render(args.source)
    args.output.mkdir(parents=True)
    image.save(args.output/'hpux_song_40.png')
if __name__ == '__main__': main()
