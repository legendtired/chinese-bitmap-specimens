#!/usr/bin/env python3
"""Extract original IBM PC DOS PRCHN24 ASCII, without executing legacy code.
Input: original PRCHN24.FNT, or Disk01.img from Chinese PC DOS 2000.
Output: original 12x24 glyphs U+0020..U+007E only. No assumed CP437 mapping.
"""
import argparse, hashlib, struct, re
from pathlib import Path
SHA='202aea3f45004ac89d6ceb1a81c33b2ac252fc1f39baf3fe6b3d34959d86c740'
def extract_disk(b):
    bps,spc,res,nfat,nroot,_,_,spf=struct.unpack_from('<HBHBHHBH',b,11)
    if (bps,spc,nfat)!=(512,1,2): raise ValueError('Unexpected disk layout')
    root=(res+nfat*spf)*bps; ds=root+((nroot*32+bps-1)//bps)*bps
    fat=b[res*bps:(res+spf)*bps]
    for o in range(root,root+nroot*32,32):
        e=b[o:o+32]
        if e[:11]!=b'PRCHN24 FNT': continue
        size=struct.unpack_from('<I',e,28)[0]; c=struct.unpack_from('<H',e,26)[0]
        out=bytearray();seen=set()
        while 2<=c<0xff0 and len(out)<size:
            if c in seen: raise ValueError('FAT cycle')
            seen.add(c);p=ds+(c-2)*bps*spc;out.extend(b[p:p+bps*spc])
            v=int.from_bytes(fat[c*3//2:c*3//2+2],'little');c=(v>>4 if c%2 else v)&4095
        if len(out)<size: raise ValueError('Truncated FAT chain')
        return bytes(out[:size])
    raise ValueError('PRCHN24.FNT missing')
def convert(b):
    if len(b)!=9216 or hashlib.sha256(b).hexdigest()!=SHA:raise ValueError('Unknown PRCHN24 source')
    lines=['STARTFONT 2.1','FONT -IBM-PRCHN24-Medium-R-Normal--24-240-72-72-C-120-ISO10646-1',
      'SIZE 24 72 72','FONTBOUNDINGBOX 12 24 0 0','STARTPROPERTIES 5','FONT_ASCENT 24','FONT_DESCENT 0',
      'PIXEL_SIZE 24','CHARSET_REGISTRY "ISO10646"','CHARSET_ENCODING "1"','ENDPROPERTIES','CHARS 95']
    for c in range(32,127):
        v=int.from_bytes(b[c*36:(c+1)*36],'big')
        rows=[(v>>(12*(23-y)))&4095 for y in range(24)]
        if (not any(rows)) != (c == 32): raise ValueError('Unexpected blank ASCII slot')
        lines += [f'STARTCHAR U{c:04X}',f'ENCODING {c}','SWIDTH 500 0','DWIDTH 12 0','BBX 12 24 0 0','BITMAP']
        lines += [f'{row<<4:04X}' for row in rows]+['ENDCHAR']
    return '\n'.join(lines+['ENDFONT',''])
def combine(cjk, ascii_bdf):
    # Keep original fullwidth glyphs byte-for-byte; add only validated ASCII.
    if not cjk.startswith('STARTFONT 2.1\n') or not cjk.rstrip().endswith('ENDFONT'):
        raise ValueError('Invalid BDF')
    if 'FONTBOUNDINGBOX 24 24 0 0' not in cjk or 'FONT_ASCENT 24' not in cjk or 'FONT_DESCENT 0' not in cjk:
        raise ValueError('Expected existing IBM 24x24 BDF metrics')
    if not any(name in cjk for name in ['prckt24', 'prcht24', 'prcfs24']):
        raise ValueError('Expected one of three collected IBM fonts')
    enc=[int(x) for x in re.findall(r'^ENCODING (-?\d+)$',cjk,re.M)]
    if any(32<=c<=126 for c in enc):raise ValueError('ASCII already present; will not overwrite')
    blocks=re.findall(r'^STARTCHAR .*?^ENDCHAR$',ascii_bdf,re.M|re.S)
    if len(blocks)!=95:raise ValueError('Invalid ASCII BDF')
    cjk=re.sub(r'^CHARS (\d+)$',lambda m:'CHARS '+str(int(m[1])+95),cjk,flags=re.M)
    cjk=re.sub(r'\nENDFONT\s*$', '\n'+'\n'.join(blocks)+'\nENDFONT\n',cjk)
    return cjk

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--cjk-bdf',type=Path);a=p.parse_args()
    if a.output.exists() or a.output.is_symlink(): raise ValueError('Output must not exist')
    b=a.source.read_bytes()
    if len(b)!=9216:b=extract_disk(b)
    result=convert(b)
    if a.cjk_bdf:result=combine(a.cjk_bdf.read_text(encoding='ascii'),result)
    with a.output.open('x',encoding='ascii') as out: out.write(result)
    print(f'{a.output}: 95 ASCII slots, original 12x24 bitmap')
