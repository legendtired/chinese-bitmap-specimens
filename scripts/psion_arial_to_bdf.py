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


ROM_SHA = '9c9fc74f237d7b741ab57b8eafa6cb400c5c72d80a9abb3c2b11b309b06b6210'
EON_SHA = '2477ea0d6bae65eba347eb8a9ef9785bf01b58279c903b10da12d1cbc673a5de'
def arial(data, size):
    if hashlib.sha256(data).hexdigest()!=EON_SHA: raise ValueError('Not verified Eon.gdr')
    p=struct.unpack_from('<I',data,32)[0];count=struct.unpack_from('<I',data,p)[0];p+=4
    uid={8:0x100001f2,11:0x100001f3}[size];chars={}
    for _ in range(count):
        h=struct.unpack_from('<I7BII',data,p);p+=19
        sections=[struct.unpack_from('<HHII',data,p+i*12) for i in range(h[-1])];p+=12*h[-1]
        if h[0]!=uid:continue
        for start,end,offset,bitmap in sections:
            n=struct.unpack_from('<I',data,offset)[0];assert n==end-start+1
            length=struct.unpack_from('<I',data,bitmap)[0];packed=data[bitmap+4:bitmap+4+length]
            for j in range(n):
                cp=start+j
                if not 32<=cp<=126:continue
                at,asc,height,left,adv,right,pad=struct.unpack_from('<H5bB',data,offset+4+j*8)
                if at==65535:continue
                width=adv-left-right;bit=at*8
                def take(n):
                    nonlocal bit
                    assert bit+n<=len(packed)*8
                    v=sum(((packed[(bit+k)//8]>>((bit+k)%8))&1)<<k for k in range(n));bit+=n;return v
                rows=[]
                while len(rows)<height:
                    repeat=take(1)==0;nr=take(4);assert 0<nr<=height-len(rows)
                    if repeat:rows.extend([[take(1) for k in range(width)]]*nr)
                    else:rows.extend([[take(1) for k in range(width)] for y in range(nr)])
                chars[cp]=(asc,height,left,adv,width,rows)
    assert set(chars)==set(range(32,127))
    return chars

def combined(rom,size):
    if hashlib.sha256(rom).hexdigest()!=ROM_SHA: raise ValueError('Not verified ROM')
    han=decode(rom[0x7815d0:0x7815d0+0x158130],size)
    latin=arial(rom[0x2c1480:0x2c1480+0x23085],size)
    assert not (han.keys() & latin.keys())
    return han|latin

def main():
    p=argparse.ArgumentParser(description='Psion Unicode Chinese + user-selected same-ROM Arial ASCII. Not a claim of unique original pairing.')
    p.add_argument('rom',type=Path);p.add_argument('--size',type=int,choices=[8,11],required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();chars=combined(a.rom.read_bytes(),a.size)
    text=export(chars,a.size).replace('-Psion-Unicode-', '-Psion-UnicodeArial-')
    text=text.replace('STARTFONT 2.1','STARTFONT 2.1\nCOMMENT Chinese Unicode.gdr plus user-selected same-ROM Eon Arial ASCII; not unique original pairing.')
    with a.output.open('x',encoding='ascii') as f:f.write(text)
if __name__=='__main__':main()
