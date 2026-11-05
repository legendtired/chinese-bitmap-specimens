#!/usr/bin/env python3
"""Offline conversion of the exact PC505 manufacturer-emulator obj to BDF.
No downloads, archive extraction or source-program execution. Not a verified
physical-device dump. Pixels are exact, advance/baseline are export conventions.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import zlib

SOURCE_SHA256 = '5701cf386d1935a84b0f1a4edbfcb365f5bdb2891b320c5b1fca22f47ed93630'
SOURCE_BYTES = 4194304
SOURCE_CRC32 = 0x71038c32
DECODED_SHA256 = 'a34bc774dd62b8924493a73f461edb3672958cf4bc237df6f11108ec2097a8fb'
KEY = b'pvdq88kljjjj::::'  # File transform constant, not a credential.
GB_BASE = 0x6c300
ASCII_BASE = 0x6bb00
RESEARCH_BDFS = {'gb': '77aabdaebb80c03dbf0be6ff10b0bbc4201a2feb30e10247c42db846c076cb5d',
 'ascii': '124a4e52dfeef0721c7ff354f666c0447842a15ad4d2b4cff20dc509d751c6fd',
 'combined': '46105fc1121ad5b1ceed40b83c5addb3668b71e32150796a91352e789a77bd1c'}
CANONICAL = {'gb': 'e6158a219cf12e1af7b964232ec7333c6fe7c58b253d8d1e675bb2f9564a6981', 'ascii': 'ed2c6ffb6e543041ebf8fef4a926464de38da2d2bc43995f7297b314162f5b3b', 'combined': 'be850abaec8f75174110f3ffdaad04e933eba6d675bade798197378249b817e7'}
SAFE_DIR_FD = (hasattr(os,'O_NOFOLLOW') and hasattr(os,'O_DIRECTORY')
 and os.open in os.supports_dir_fd and os.mkdir in os.supports_dir_fd)


def require(ok, message):
    if not ok: raise ValueError(message)


def sha256(data): return hashlib.sha256(data).hexdigest()


def absolute_parts(path):
    require('..' not in Path(path).parts, 'Parent traversal is not accepted')
    return Path(os.path.abspath(path)).parts[1:]


def validate_source(raw):
    require(len(raw) == SOURCE_BYTES, 'Unsupported obj size')
    require(sha256(raw) == SOURCE_SHA256, 'SHA-256 mismatch: modified or unsupported obj')
    require(zlib.crc32(raw) == SOURCE_CRC32, 'Source CRC32 mismatch')


def load_obj(path):
    """Bounded regular-file read; no symlinks in any path component."""
    require(SAFE_DIR_FD, 'Requires POSIX O_NOFOLLOW and dir_fd support')
    parts = absolute_parts(path)
    require(bool(parts), 'Input must be a regular file')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open('/', flags)
    try:
        for part in parts[:-1]:
            child = os.open(part, flags, dir_fd=parent)
            os.close(parent); parent = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as handle:
            info = os.fstat(handle.fileno())
            require(stat.S_ISREG(info.st_mode), 'Input must be regular, not FIFO/device/directory')
            require(info.st_size == SOURCE_BYTES, 'Unsupported obj size')
            raw = handle.read(SOURCE_BYTES + 1)
    finally: os.close(parent)
    validate_source(raw)
    return raw


def decode(raw):
    validate_source(raw)
    data = bytes((KEY[i % 16] - value - 1) & 255 for i, value in enumerate(raw))
    require(sha256(data) == DECODED_SHA256, 'Decoded image hash mismatch')
    return data


def mapping():
    result = []
    for hi in range(0xa1, 0xf8):
        for lo in range(0xa1, 0xff):
            pair = bytes((hi, lo))
            try: char = pair.decode('gb2312', 'strict')
            except UnicodeDecodeError: continue
            require(len(char) == 1 and char.encode('gb2312') == pair, 'Mapping roundtrip')
            require(hi <= 0xa9 or hi >= 0xb0, 'Unexpected GB2312 zone')
            slot = ((hi-0xa1)*94+lo-0xa1 if hi <= 0xa9 else 831+(hi-0xb0)*94+lo-0xa1)
            require(0 <= slot < 7599, 'Slot outside table')
            result.append((ord(char), int.from_bytes(pair, 'big'), slot))
    require(len(result) == 7445 and len({cp for cp, _, _ in result}) == 7445, 'Mapping count/collision')
    require(sum(0x4e00 <= cp <= 0x9fff for cp, _, _ in result) == 6763, 'Han mapping count')
    return result


def recover(data):
    require(len(data) == SOURCE_BYTES, 'Truncated decoded image')
    gb = {}
    for cp, _, slot in mapping():
        start = GB_BASE*8 + slot*210
        rows = []
        for y in range(15):
            row = 0
            for x in range(14):
                bit = start+y*14+x
                row = (row << 1) | ((data[(bit//8)^0x4000] >> (7-bit%8)) & 1)
            rows.append(row)
        gb[cp] = (14, tuple(rows))
    ascii_glyphs = {c: (8, tuple(data[(ASCII_BASE+c*16+y)^0x4000] for y in range(16)))
                    for c in range(32, 127)}
    return gb, ascii_glyphs


def validate_glyphs(gb, ascii_glyphs):
    require(len(gb) == 7445 and set(ascii_glyphs) == set(range(32,127)), 'Wrong glyph maps')
    require(not set(gb) & set(ascii_glyphs), 'Mapping overlap')
    require([cp for cp, (_, rows) in sorted(gb.items()) if not any(rows)] == [0x3000], 'Unexpected blank glyph')
    han = {cp: g for cp,g in gb.items() if 0x4e00 <= cp <= 0x9fff}
    require(len(han) == 6763 and len(set(han.values())) == 6763, 'Han count/duplicate changed')
    require(sum(bool(rows[-1]) for _,rows in han.values()) == 6582, 'Last-row preservation')


def make_bdf(glyphs, label):
    require(bool(glyphs), 'No glyphs')
    mw = max(w for w,rs in glyphs.values()); mh = max(len(rs) for w,rs in glyphs.values())
    out = ['STARTFONT 2.1',
     'COMMENT Recovered from PC505 manufacturer emulator image; not independently verified as a physical device dump.',
     'COMMENT Exact stored pixels. Original display advances/baselines not established; export uses stored bitmap dimensions.',
     'COMMENT BDF SIZE and 72-dpi resolution agree with pixel height; SWIDTH is derived from DWIDTH, not a device metric.',
     'COMMENT Source SHA256 '+SOURCE_SHA256, 'COMMENT No claim of font authorship or redistribution permission.',
     f"FONT -Recovered-PC505-{label}-R-Normal--{mh}-{mh*10}-72-72-{'P' if label == 'GB2312ASCII' else 'C'}-{mw*10}-ISO10646-1",
     f'SIZE {mh} 72 72', f'FONTBOUNDINGBOX {mw} {mh} 0 0', 'STARTPROPERTIES 4',
     f'FONT_ASCENT {mh}', 'FONT_DESCENT 0', 'CHARSET_REGISTRY "ISO10646"',
     'CHARSET_ENCODING "1"', 'ENDPROPERTIES', f'CHARS {len(glyphs)}']
    for cp, (w, rows) in sorted(glyphs.items()):
        require(0 <= cp <= 0x10ffff and not 0xd800 <= cp <= 0xdfff, 'Invalid Unicode')
        require(w in (8,14) and len(rows) in (15,16), 'Unsupported dimensions')
        require(all(0 <= r < 1 << w for r in rows), 'Pixel row exceeds width')
        out += [f'STARTCHAR uni{cp:04X}', f'ENCODING {cp}', f'SWIDTH {round(1000*w/mh)} 0',
                f'DWIDTH {w} 0', f'BBX {w} {len(rows)} 0 0', 'BITMAP']
        out += [f'{r<<((-w)%8):0{((w+7)//8)*2}X}' for r in rows]
        out += ['ENDCHAR']
    return ('\n'.join(out+['ENDFONT'])+'\n').encode('ascii')


def output_path(path):
    require(SAFE_DIR_FD, 'Requires POSIX O_NOFOLLOW and dir_fd support')
    absolute_parts(path)
    absolute = Path(os.path.abspath(path)); root = Path.cwd()/'local-research'
    require(absolute.is_relative_to(root), 'Output must be inside ./local-research')
    require(absolute != root and absolute.suffix.lower() == '.bdf', 'Output must be a new .bdf')
    require(not any(p.is_symlink() for p in [absolute,*absolute.parents]), 'Output symlinks refused')
    require(not absolute.exists(), 'Output exists; never overwrites')
    return absolute


def write_bdf(path, data):
    path = output_path(path); relative = path.relative_to(Path.cwd())
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open('.', flags)
    try:
        for part in relative.parts[:-1]:
            try: os.mkdir(part, 0o700, dir_fd=parent)
            except FileExistsError: pass
            child = os.open(part, flags, dir_fd=parent)
            os.close(parent); parent = child
        fd = os.open(relative.parts[-1], os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as handle: handle.write(data)
    finally: os.close(parent)
    # Leave failed new files for inspection; never unlink a concurrently replaced path.


def export(source, output, subset='combined'):
    require(subset in CANONICAL, 'Unknown subset')
    output = output_path(output)
    raw = load_obj(source); gb, ascii_glyphs = recover(decode(raw))
    validate_glyphs(gb, ascii_glyphs)
    glyphs, label = {'gb': (gb,'GB2312'), 'ascii': (ascii_glyphs,'ASCII'),
                     'combined': (gb | ascii_glyphs,'GB2312ASCII')}[subset]
    bdf = make_bdf(glyphs, label)
    require(sha256(bdf) == CANONICAL[subset], 'Canonical BDF hash mismatch')
    write_bdf(output, bdf)
    return {'sourceBytes': len(raw), 'sourceSha256': sha256(raw), 'sourceCrc32': f'{SOURCE_CRC32:08x}',
      'subset': subset, 'unicodeGlyphs': len(glyphs), 'gb2312Glyphs': 0 if subset=='ascii' else 7445,
      'hanGlyphs': 0 if subset=='ascii' else 6763, 'asciiGlyphs': 0 if subset=='gb' else 95,
      'hanStorageCell': [14,15], 'asciiStorageCell': [8,16],
      'metricsStatus': 'Advance, baseline, SIZE, SWIDTH and global bounds are export conventions; pixels unchanged.',
      'physicalDeviceDumpVerified': False, 'bdfBytes': len(bdf), 'bdfSha256': sha256(bdf)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--obj', required=True, type=Path, help='Pinned complete local obj, not RAR or EXE')
    p.add_argument('--output', required=True, type=Path, help='New .bdf inside ./local-research')
    p.add_argument('--subset', choices=tuple(CANONICAL), default='combined')
    a = p.parse_args(argv)
    try: report = export(a.obj, a.output, a.subset)
    except (ValueError,OSError) as error:
        print(f'Error: {error}', file=sys.stderr); return 1
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0

if __name__ == '__main__': sys.exit(main())
