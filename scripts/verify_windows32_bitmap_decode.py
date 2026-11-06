#!/usr/bin/env python3
"""Optional independent audit against a private pinned DISK6 image.
Requires Pillow only for raw 1-bit decoding, never a font renderer.
No source font or glyph data is embedded. Produces only aggregate audit JSON.
"""
import argparse,json
from pathlib import Path
from PIL import Image
import windows32_bitmap_export as m

def audit(source,n):
    b=m.read_source(source,n);gs=m.decode(b,n);s=m.SPECS[n]
    # Independent offset arithmetic and Pillow's C raw-decoder path.
    for cp,g in gs.items():
        if cp<128:
            off=288+cp*(13 if n==13 else 40);width=7 if n==13 else 10;rb=1 if n==13 else 2
        else:
            a,z=chr(cp).encode('gb2312');index=(a-161)*94+z-161
            if a>=174:index-=376
            off=(1952 if n==13 else 5408)+index*(26 if n==13 else 60);width=n;rb=2 if n==13 else 3
        im=Image.frombytes('1',(rb*8,n),b[off:off+n*rb],'raw','1;I')
        rows=[]
        for y in range(n):
            row=0
            for x in range(width):row=row*2+int(bool(im.getpixel((x,y))))
            rows.append(row)
        if rows!=g['rows']:raise ValueError(f'Pillow differs at U+{cp:04X}')
    count=bytecount=0
    for offset,stride,slots in [(288,s['ascii_stride'],128),(s['han_offset'],s['han_stride'],s['slots'])]:
        rb=stride//n
        for i in range(slots):
            raw=b[offset+i*stride:offset+(i+1)*stride]
            im=Image.frombytes('1',(rb*8,n),raw,'raw','1;I');out=bytearray()
            for y in range(n):
                for xx in range(rb):
                    value=0
                    for bit in range(8):value=value*2+int(not im.getpixel((xx*8+bit,y)))
                    out.append(value)
            if bytes(out)!=raw:raise ValueError(f'Physical slot {i} does not round-trip')
            count+=1;bytecount+=len(raw)
    return dict(size=n,source_sha256=m.sha(b),unicode_glyphs_compared=len(gs),physical_slots_roundtripped=count,physical_bitmap_bytes_roundtripped=bytecount,passed=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source');ap.add_argument('--output',type=Path);args=ap.parse_args()
    results=[audit(args.source,n) for n in [13,20]];encoded=(json.dumps(results,indent=2)+'\n').encode()
    if args.output:m.write_outputs(args.output.parent,{args.output.name:encoded})
    print(encoded.decode(),end='')
if __name__=='__main__':main()
