#!/usr/bin/env python3
"""Export verified CJKOS 10/12 px FBLK databases without executing Palm code."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

# Verified historical databases; True marks an included specimen source.
SOURCES = {
    'a8de69c5cf30d53a3433c63c1fea1f02a54f21e380ebfe1d312514a51eabf091': (12, 'big5', True),
    '2f2db52b735589ee627b2c9ccd4d73bca2ae1cded7ccf14c377423c54a112cef': (10, 'gb2312', True),
    'c02b4e383ddd08b146fef4f853d55bd6492ceb546cf687fcdf4491837bbcdc8c': (12, 'gb2312', True),
    '3ca7a7aa0e595638044337a78f16bc0c194e08d1a30ef13d70212f86c7be83a7': (10, 'big5', True),
    'e913c4c3f91cf2852747500f5c516a5f6ef1852df66493e4cc289f2656e15882': (12, 'big5', True),
    'd85dc93831acfdd1df0bf7c14cd7b972adace6bf99dda38239c2e1676c4b57ac': (10, 'gb2312', False),
    'abb0ebd4a278918614febc5f043e44173d5bffb7fbe4c322bcc96d6502ac68f3': (12, 'gb2312', False),
}

def decode_pixels(data, size):
    if len(data) != (13 if size == 10 else 18):
        raise ValueError('Wrong glyph byte count')
    return tuple(tuple(
        (data[(y*12+x)//8] >> (7-(y*12+x)%8)) & 1 if size == 12 else
        ((data[y] >> (7-x)) & 1 if x < 8 else
         (data[10+y//4] >> (7-2*(y%4)-(x-8))) & 1)
        for x in range(size)) for y in range(size))

def source_codes(codec):
    trails = range(0xa1, 0xff) if codec == 'gb2312' else [*range(0x40, 0x7f), *range(0xa1, 0xff)]
    leads = range(0xa1, 0xf8) if codec == 'gb2312' else range(0xa1, 0xfa)
    return [a*256+b for a in leads for b in trails]

def load_font(path):
    data = Path(path).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha not in SOURCES:
        raise ValueError('Unverified source SHA-256; this exporter only accepts the documented binaries')
    size, codec, catalog_match = SOURCES[sha]
    if data[60:68] != b'dFntdCJK' or not struct.unpack_from('>H', data, 32)[0] & 1:
        raise ValueError('Not a CJKOS resource database')
    count = struct.unpack_from('>H', data, 76)[0]
    entries = [struct.unpack_from('>4sHI', data, 78+i*10) for i in range(count)]
    bpg = 13 if size == 10 else 18
    payloads = []
    for i, (typ, rid, start) in enumerate(entries):
        end = entries[i+1][2] if i+1 < count else len(data)
        if typ != b'FBLK' or rid != i or not 78+count*10 <= start < end <= len(data):
            raise ValueError('Invalid FBLK resource table')
        chunk = data[start:end]
        if len(chunk) % bpg or (i+1 < count and len(chunk) != 2048*bpg):
            raise ValueError('Invalid FBLK length')
        payloads.append(chunk)
    payload = b''.join(payloads)
    codes = source_codes(codec)
    if len(payload) != len(codes)*bpg:
        raise ValueError('Unexpected slot count')
    glyphs = []
    for i, code in enumerate(codes):
        raw = code.to_bytes(2, 'big')
        try:
            char = raw.decode(codec, errors='strict')
            cp = ord(char)
            canonical = char.encode(codec, errors='strict') == raw
        except (UnicodeError, TypeError):
            cp, canonical = None, False
        glyphs.append(dict(source_code=code, codepoint=cp, canonical=canonical,
                           pixels=decode_pixels(payload[i*bpg:(i+1)*bpg], size)))
    info = dict(source_sha256=sha, catalog_source_match=catalog_match, size=size,
                codec=codec, slots=len(glyphs), resources=count,
                baseline_policy='Synthetic baseline at cell bottom; source contains no per-glyph metrics')
    return glyphs, info

def render_bdf(glyphs, info, encoding='unicode'):
    s = info['size']
    registry = 'ISO10646' if encoding == 'unicode' else ('GB2312.1980' if info['codec']=='gb2312' else 'BIG5')
    suffix = '1' if encoding == 'unicode' else '0'
    # Source mode uses EUC bytes for GB (A1A1), not the X11 2121 convention.
    if encoding == 'source': registry = 'CJKOSGB' if info['codec']=='gb2312' else 'CJKOSBIG5'
    lines = ['STARTFONT 2.1', 'COMMENT Exported from native CJKOS FBLK pixels; no fallback glyphs',
             'COMMENT Source SHA256 '+info['source_sha256'],
             f'FONT -cjkarchive-CJKOS{info["codec"]}-medium-r-normal--{s}-{s*10}-72-72-c-{s*10}-{registry}-{suffix}', f'SIZE {s} 72 72',
             f'FONTBOUNDINGBOX {s} {s} 0 0', 'STARTPROPERTIES 5',
             f'FONT_ASCENT {s}', 'FONT_DESCENT 0', f'PIXEL_SIZE {s}',
             f'CHARSET_REGISTRY "{registry}"', f'CHARSET_ENCODING "{suffix}"',
             'ENDPROPERTIES', f'CHARS {len(glyphs)}']
    exceptions = []
    assigned = 0
    for g in glyphs:
        cp = g['codepoint']
        enc = g['source_code'] if encoding == 'source' else cp if cp is not None and g['canonical'] else -1
        if enc == -1:
            exceptions.append(dict(source_code=f'{g["source_code"]:04X}',
                                   unicode=None if cp is None else f'U+{cp:04X}',
                                   reason='unmapped' if cp is None else 'noncanonical_duplicate'))
        else: assigned += 1
        lines += [f'STARTCHAR source-{g["source_code"]:04X}', f'ENCODING {enc}',
                  'SWIDTH 1000 0', f'DWIDTH {s} 0', f'BBX {s} {s} 0 0', 'BITMAP']
        for row in g['pixels']:
            value = sum(bit << (15-x) for x,bit in enumerate(row))
            lines.append(f'{value:04X}')
        lines.append('ENDCHAR')
    lines.append('ENDFONT')
    report = dict(info, output_encoding=encoding, encoded_glyphs=assigned,
                  unencoded_glyphs=len(exceptions), exceptions=exceptions,
                  ordinary_ascii_glyphs=0,
                  note='Every physical slot is preserved. Unmapped or duplicate Unicode slots remain ENCODING -1 with their source-XXXX tag.')
    return '\n'.join(lines)+'\n', report

def preflight_outputs(output, report, source):
    """Do not overwrite inputs, prior outputs, symlinks, or aliasing targets."""
    output, report, source = Path(output), Path(report), Path(source)
    targets = (output, report)
    resolved = [p.resolve() for p in targets]
    if resolved[0] == resolved[1]:
        raise ValueError('Output and report must be different targets, including resolved aliases')
    source_resolved = source.resolve()
    for target, real in zip(targets, resolved):
        if real == source_resolved:
            raise ValueError('Output/report must not replace the input')
        if target.exists() or target.is_symlink():
            raise ValueError(f'Refusing existing output/report target: {target}')
        if not target.parent.is_dir():
            raise ValueError(f'Output/report parent directory does not exist: {target.parent}')
    return targets


def write_outputs(output, report, source, bdf, metadata):
    """Exclusively create both files; remove only our own files after failure."""
    import os
    targets = preflight_outputs(output, report, source)
    payloads = (bdf.encode('ascii'), (json.dumps(metadata, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    opened = []
    try:
        # Open both before writing either. 'xb' uses O_EXCL and refuses symlinks.
        for target in targets:
            stream = target.open('xb')
            st = os.fstat(stream.fileno())
            opened.append((target, stream, (st.st_dev, st.st_ino)))
        for (_, stream, _), payload in zip(opened, payloads):
            stream.write(payload)
            stream.flush()
        for _, stream, _ in opened:
            stream.close()
    except BaseException:
        for target, stream, identity in opened:
            try:
                stream.close()
            except OSError:
                pass
            try:
                st = target.lstat()
                if (st.st_dev, st.st_ino) == identity:
                    target.unlink()
            except OSError:
                pass
        raise

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--encoding', choices=['unicode','source'], default='unicode')
    p.add_argument('--report', type=Path)
    a=p.parse_args()
    try:
        target=a.report or a.output.with_suffix(a.output.suffix+'.json')
        preflight_outputs(a.output,target,a.input)
        glyphs,info=load_font(a.input);bdf,report=render_bdf(glyphs,info,a.encoding)
        write_outputs(a.output,target,a.input,bdf,report)
        print(f'{len(glyphs)} slots; {report["encoded_glyphs"]} encoded; {report["unencoded_glyphs"]} unencoded')
    except (OSError, ValueError, struct.error) as e: p.exit(1,f'Error: {e}\n')
if __name__ == '__main__': main()
