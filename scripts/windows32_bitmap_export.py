#!/usr/bin/env python3
"""Fixed-source Windows 3.2 SIMSUN13/20 bitmap decoder. Python standard library only.

No font data is embedded or downloaded. Obtain the original source lawfully.
Defaults to fixed research specimens and metadata. --export-bdf additionally
writes a complete local BDF: do not publish it without the relevant rights.
BDF layout uses an explicit top-aligned cell convention, not inferred Windows
baseline metrics. No outlines, rasterizer, fallback, or character substitution.
"""
import argparse
import binascii
import hashlib
import json
from pathlib import Path
import struct
import zlib

DISK_SHA256 = '3f769322784d0c7e64530075ba0b9f444025590931f22b2d16d134b74e741f17'
SPECS = {
 13: dict(size=204830, sha256='740a69421666667e734e356f536b8684d55cefe1e6a5e9d16fe80c438161b2dd', compressed_sha256='f0051cbef4065420ce25201fa909368fa2e7da037a5121dff8c5bd25b3dd8dd0', ascii_width=7, ascii_stride=13, han_stride=26, han_offset=1952, slots=7803),
 20: dict(size=473528, sha256='f245986e77adbb467dcbef6428e1a7abb01ccaf40ea61cc4a680c5dcdc445b9e', compressed_sha256='443c45d0eb8d9059dcca90d70a68040f897bf134c06bdf35120ff77f24938215', ascii_width=10, ascii_stride=40, han_stride=60, han_offset=5408, slots=7802),
}
PHRASE = '视野无限广，窗外有蓝天。'
EXTRA = '片版牌局'
ASCII = '0123456789 AaBb GgMm !?:+-.'

def sha(b): return hashlib.sha256(b).hexdigest()
def u16(b, p): return struct.unpack_from('<H', b, p)[0]
def u32(b, p): return struct.unpack_from('<I', b, p)[0]
def require(ok, why):
    if not ok: raise ValueError(why)

def fat12_file(b, wanted):
    require(sha(b) == DISK_SHA256, 'Unrecognized DISK6.img SHA256; refusing extraction')
    bps, spc, reserved, nf, nr, spf = u16(b, 11), b[13], u16(b, 14), b[16], u16(b, 17), u16(b, 22)
    fat = b[reserved*bps:(reserved+spf)*bps]
    root = (reserved+nf*spf)*bps
    data = root + ((nr*32+bps-1)//bps)*bps
    for p in range(root, root+nr*32, 32):
        e = b[p:p+32]
        if e[0] == 0: break
        if e[0] == 0xe5 or e[11] & 0x18: continue
        name = e[:8].decode('ascii').strip() + '.' + e[8:11].decode('ascii').strip()
        if name != wanted: continue
        size, cluster, out, seen = u32(e, 28), u16(e, 26), bytearray(), set()
        while 2 <= cluster < 0xff8:
            require(cluster not in seen, 'FAT cycle')
            seen.add(cluster)
            start = data+(cluster-2)*spc*bps
            require(start+spc*bps <= len(b), 'FAT extent outside image')
            out.extend(b[start:start+spc*bps])
            x = u16(fat, cluster*3//2)
            cluster = x >> 4 if cluster & 1 else x & 0xfff
        require(len(out) >= size, 'Short FAT chain')
        return bytes(out[:size])
    raise ValueError('Source file not found in pinned disk image: '+wanted)

def szdd(b, expected_size):
    require(len(b) >= 14, 'Truncated SZDD header')
    require(0 < expected_size <= 1024*1024, 'Unreasonable expanded size')
    require(b[:9] == b'SZDD\x88\xf0\x273A', 'Not SZDD mode A')
    require(u32(b, 10) == expected_size, 'Unexpected expanded size')
    ring, pos, i, out = bytearray(b' '*4096), 4080, 14, bytearray()
    while len(out) < expected_size:
        require(i < len(b), 'Truncated SZDD flag')
        flags = b[i]; i += 1
        for bit in range(8):
            if len(out) >= expected_size: break
            if flags & (1 << bit):
                require(i < len(b), 'Truncated SZDD literal')
                v = b[i]; i += 1
                out.append(v); ring[pos] = v; pos = (pos+1) & 4095
            else:
                require(i+2 <= len(b), 'Truncated SZDD reference')
                lo, hi = b[i:i+2]; i += 2
                offset, count = lo | ((hi & 0xf0) << 4), (hi & 15)+3
                for j in range(count):
                    v = ring[(offset+j) & 4095]
                    out.append(v); ring[pos] = v; pos = (pos+1) & 4095
    require(len(out) == expected_size, 'SZDD output overrun')
    return bytes(out)

def read_source(path, n):
    s = SPECS[n]; b = Path(path).read_bytes()
    if sha(b) == DISK_SHA256: b = fat12_file(b, f'SIMSUN{n}.FO_')
    if b.startswith(b'SZDD'):
        require(sha(b) == s['compressed_sha256'], 'Unrecognized compressed-source SHA256')
        b = szdd(b, s['size'])
    require(len(b) == s['size'] and sha(b) == s['sha256'], 'Unrecognized FON size or SHA256; refusing decoding')
    return b

def decode_rows(data, offset, height, stride, width):
    require(height > 0 and stride > 0 and stride % height == 0, 'Invalid row stride')
    rb = stride//height
    require(0 < width <= rb*8, 'Invalid cell width')
    require(offset >= 0 and offset+stride <= len(data), 'Bitmap extent outside data')
    rows=[]
    for y in range(height):
        row=int.from_bytes(data[offset+y*rb:offset+(y+1)*rb], 'big')
        rows.append(((~row)&((1<<(rb*8))-1))>>(rb*8-width))
    return dict(width=width,height=height,rows=rows)

def decode(b, n):
    s = SPECS[n]
    require(sha(b) == s['sha256'], 'Unrecognized FON SHA256')
    require(b[:10] == b'CWIN30    ' and b[140:146] == b'GB2312', 'Unexpected CWIN30/GB2312 markers')
    require([u16(b, x) for x in [0x9e, 0xa0, 0xa2]] == [n]*3, 'Unexpected size fields')
    require(u16(b, 0xae) == s['ascii_width'], 'Unexpected ASCII width')
    require((u32(b, 0x110), u32(b, 0x114), u16(b, 0x11c), u16(b, 0x11e)) == (288, s['han_offset'], s['ascii_stride'], s['han_stride']), 'Unexpected offsets/strides')
    def glyph(offset, stride, width):return decode_rows(b,offset,n,stride,width)
    gs = {c:glyph(288+c*s['ascii_stride'], s['ascii_stride'], s['ascii_width']) for c in range(32,127)}
    for lead in list(range(0xa1,0xaa))+list(range(0xae,0xf8)):
        for trail in range(0xa1,0xff):
            try: c = bytes([lead,trail]).decode('gb2312')
            except UnicodeDecodeError: continue
            index = (lead-0xa1-(4 if lead >= 0xae else 0))*94+trail-0xa1
            gs[ord(c)] = glyph(s['han_offset']+index*s['han_stride'], s['han_stride'], n)
    required = set()
    for a in range(0xa1,0xf8):
        for c in range(0xa1,0xff):
            try: required.add(ord(bytes([a,c]).decode('gb2312')))
            except UnicodeDecodeError: pass
    require(len(required) == 7445 and required <= gs.keys(), 'Incomplete GB2312 mapping')
    han = [g for c,g in gs.items() if 0x4e00 <= c <= 0x9fff]
    require(len(han) == 6763 and all(any(g['rows']) for g in han), 'Missing or blank standard Han')
    return gs

def png_data(gs, text, scale=1):
    require(all(ord(c) in gs for c in text), 'Requested specimen has an unmapped character')
    h = max(gs[ord(c)]['height'] for c in text)
    w = sum(gs[ord(c)]['width']+1 for c in text)-1
    pixels = [[255]*w for _ in range(h)]; x = 0
    for c in text:
        g = gs[ord(c)]
        for y,row in enumerate(g['rows']):
            for j in range(g['width']):
                if row & (1 << (g['width']-1-j)): pixels[y][x+j] = 0
        x += g['width']+1
    raw = bytearray()
    for row in pixels:
        rr = b''.join(bytes([v])*scale for v in row)
        raw.extend((b'\0'+rr)*scale)
    def chunk(tag, data): return struct.pack('>I',len(data))+tag+data+struct.pack('>I',binascii.crc32(tag+data)&0xffffffff)
    data = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w*scale,h*scale,8,0,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw),9))+chunk(b'IEND',b'')
    return data

def bdf(gs, n):
    # A documented export layout convention, not a claim about Windows bearings.
    lines = ['STARTFONT 2.1','COMMENT Source pixels preserved; original rights remain with their owners.','COMMENT Layout convention: left=0, bottom=0, ascent=cell height, descent=0.','FONT -historical-windows32_simsun-medium-r-normal--%d-0-75-75-c-0-iso10646-1'%n,f'SIZE {n} 75 75',f'FONTBOUNDINGBOX {n} {n} 0 0','STARTPROPERTIES 3',f'FONT_ASCENT {n}','FONT_DESCENT 0','DEFAULT_CHAR 32','ENDPROPERTIES',f'CHARS {len(gs)}']
    for cp,g in sorted(gs.items()):
        w = g['width']; rb = (w+7)//8
        lines += [f'STARTCHAR uni{cp:04X}',f'ENCODING {cp}',f'SWIDTH {round(w*72000/(n*75))} 0',f'DWIDTH {w} 0',f'BBX {w} {n} 0 0','BITMAP']
        lines += [f'{row << (rb*8-w):0{rb*2}X}' for row in g['rows']]
        lines += ['ENDCHAR']
    return '\n'.join(lines+['ENDFONT',''])

def catalog_png(gs, n):
    """The two-line website specimen; exact native pixels and transparent gaps."""
    texts = [PHRASE, ASCII]
    widths = [sum(gs[ord(c)]['width']+1 for c in t)-1 for t in texts]
    width, height = max(widths), n*2+4
    pixels = bytearray(bytes([255,255,255,0])*(width*height))
    for line,t in enumerate(texts):
        top = line*(n+4)
        # Original phrase/ASCII strips have opaque white backgrounds.
        for y in range(n):
            for x in range(widths[line]):
                k=((top+y)*width+x)*4; pixels[k:k+4]=b'\xff\xff\xff\xff'
        x=0
        for c in t:
            g=gs[ord(c)]
            for y,row in enumerate(g['rows']):
                for j in range(g['width']):
                    if row & (1 << (g['width']-1-j)):
                        k=((top+y)*width+x+j)*4;pixels[k:k+4]=b'\0\0\0\xff'
            x+=g['width']+1
    raw=b''.join(b'\0'+pixels[y*width*4:(y+1)*width*4] for y in range(height))
    def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',binascii.crc32(tag+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')

def write_outputs(output, files):
    """Reject any existing target before creating/writing any output file."""
    output=Path(output)
    require(not output.exists() or output.is_dir(), 'Output path is not a directory')
    require(all(not ((output/name).exists() or (output/name).is_symlink()) for name in files), 'Output file already exists; refusing all writes')
    output.mkdir(parents=True,exist_ok=True)
    created=[]
    try:
        for name,data in files.items():
            path=output/name
            # Exclusive create also protects against a collision after preflight.
            with path.open('xb') as f:
                created.append(path);f.write(data)
    except Exception:
        for path in created:path.unlink()
        raise

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',help='Pinned third-party archived DISK6.img, SIMSUN13/20.FO_, or SIMSUN13/20.FON')
    ap.add_argument('--size',type=int,choices=sorted(SPECS),required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--export-bdf',action='store_true',help='Also create a complete local BDF; no redistribution license is implied')
    args=ap.parse_args();n=args.size
    data=read_source(args.source,n);gs=decode(data,n);files={}
    for label,t in [('phrase',PHRASE),('extra',EXTRA),('ascii',ASCII)]:
        files[f'simsun{n}-{label}-1x.png']=png_data(gs,t)
    files[f'win32_simsun_{n}.png']=catalog_png(gs,n)
    report={'source_sha256':sha(data),'size':n,'gb2312_doublebyte':7445,'han':6763,'printable_ascii':95,'unicode_glyphs':len(gs),'ascii_origin':'Original 128-slot halfwidth block; U+0020..U+007E exported, no borrowed glyphs','outline_rendered':False,'layout_note':'BDF uses documented top-aligned fixed-cell convention; original Windows baseline not inferred','specimen_sha256':sha(files[f'win32_simsun_{n}.png'])}
    files[f'simsun{n}-report.json']=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if args.export_bdf:files[f'simsun{n}.bdf']=bdf(gs,n).encode('ascii')
    write_outputs(args.output,files)
    print(json.dumps(report,ensure_ascii=False))
if __name__ == '__main__':main()
