#!/usr/bin/env python3
"""Offline decoder for the verified Psion 618C Unicode.gdr; contains no glyph data."""
import argparse, hashlib, struct
from pathlib import Path
GDR_SHA='cc99d6580212a5bbbc1ccfa786248aee9637a3ac6a6a88584c7fcf50ed784d15'
def decode(data, size):
    if hashlib.sha256(data).hexdigest()!=GDR_SHA:
        raise ValueError('Not the verified Unicode.gdr')
    pos=0x86
    count=struct.unpack_from('<I',data,pos)[0]; pos+=4
    chars={}; chosen=[]
    for _ in range(count):
        head=struct.unpack_from('<I7BII',data,pos); pos+=19
        sections=[struct.unpack_from('<HHII',data,pos+i*12) for i in range(head[-1])];pos+=12*head[-1]
        if head[4]!=size: continue
        chosen.append(head)
        for start,end,offset,bitmap in sections:
            n=struct.unpack_from('<I',data,offset)[0]
            if n!=end-start+1: raise ValueError('Invalid section length')
            length=struct.unpack_from('<I',data,bitmap)[0]
            packed=data[bitmap+4:bitmap+4+length]
            for j in range(n):
                at,asc,height,left,advance,right,_pad=struct.unpack_from('<H5bB',data,offset+4+j*8)
                if at==65535:continue
                width=advance-left-right;bit=at*8
                if min(width,height)<0: raise ValueError('Invalid metrics')
                def take(n):
                    nonlocal bit
                    if bit+n>len(packed)*8:raise ValueError('Truncated bitmap')
                    v=sum(((packed[(bit+k)//8]>>((bit+k)%8))&1)<<k for k in range(n));bit+=n;return v
                rows=[]
                while len(rows)<height:
                    repeat=take(1)==0;nr=take(4)
                    if not 0<nr<=height-len(rows):raise ValueError('Invalid run')
                    if repeat:
                        row=[take(1) for _ in range(width)];rows.extend([row]*nr)
                    else:rows.extend([[take(1) for _ in range(width)] for _ in range(nr)])
                # Empty placeholder slots are not character coverage.
                if not any(any(row) for row in rows):continue
                cp=start+j
                if cp in chars:raise ValueError('Overlapping sections')
                chars[cp]=(asc,height,left,advance,width,rows)
    if not chosen or not chars:raise ValueError('No glyphs')
    return chars

def export(chars,size):
    xmin=min(g[2] for g in chars.values());xmax=max(g[2]+g[4] for g in chars.values())
    ymin=min(g[0]-g[1] for g in chars.values());ymax=max(g[0] for g in chars.values())
    lines=['STARTFONT 2.1',f'FONT -Psion-Unicode-Medium-R-Normal--{size}-{size*10}-75-75-P-0-ISO10646-1',f'SIZE {size} 75 75',f'FONTBOUNDINGBOX {xmax-xmin} {ymax-ymin} {xmin} {ymin}','STARTPROPERTIES 2',f'FONT_ASCENT {ymax}',f'FONT_DESCENT {-ymin}','ENDPROPERTIES',f'CHARS {len(chars)}']
    for cp,(asc,height,left,adv,width,rows) in sorted(chars.items()):
        lines.extend([f'STARTCHAR U{cp:04X}',f'ENCODING {cp}',f'SWIDTH {round(adv*1000/size)} 0',f'DWIDTH {adv} 0',f'BBX {width} {height} {left} {asc-height}','BITMAP'])
        digits=((width+7)//8)*2;pad=((width+7)//8)*8-width
        for row in rows:
            value=0
            for b in row:value=(value<<1)|b
            lines.append(f'{value<<pad:0{digits}X}')
        lines.append('ENDCHAR')
    return '\n'.join(lines+['ENDFONT',''])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--size',type=int,choices=[8,11],required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--rom',action='store_true',help='Read verified Unicode.gdr slice from a 16MiB ROM')
    a=p.parse_args();data=a.input.read_bytes()
    if a.rom:
        if len(data)!=16*1024*1024:raise ValueError('Expected 16MiB ROM')
        data=data[0x7815d0:0x7815d0+0x158130]
    result=export(decode(data,a.size),a.size)
    with a.output.open('x',encoding='ascii') as f:f.write(result)
if __name__=='__main__':main()
