#!/usr/bin/env python3
"""Verified native Sharp/FM Towns ANK, alone or merged with the existing CJK export."""
import argparse, hashlib, json
from pathlib import Path
import sharp_x68000_to_bdf as sharp
import fmtowns_f20_to_bdf as towns

CONFIG = {'sharp': (sharp, 0x3A800, 8, 16, 1), 'fmtowns': (towns, 0x10, 10, 20, 2)}

def extract_ank(rom, device):
    mod, base, width, height, rowbytes = CONFIG[device]
    if len(rom) != mod.ROM_SIZE or hashlib.sha256(rom).hexdigest() != mod.ROM_SHA256:
        raise ValueError('Unsupported ROM')
    result = {}
    for slot in range(0x20, 0x7f):
        cp = {0x5c: 0xa5, 0x7e: 0x203e}.get(slot, slot)
        start = base + slot * height * rowbytes
        frame = rom[start:start + height * rowbytes]
        if slot == 0x20 and any(frame): raise ValueError('Space must be blank')
        if slot != 0x20 and not any(frame): raise ValueError('Unexpected empty ANK glyph')
        if any(frame[y*rowbytes+rowbytes-1] & ((1 << (rowbytes*8-width))-1) for y in range(height)):
            raise ValueError('Nonzero padding')
        result[cp] = (width, height, frame)
    return result

def make_bdf(glyphs, height, device):
    width = max(g[0] for g in glyphs.values())
    lines = ['STARTFONT 2.1', 'COMMENT Native ROM glyphs. No fallback or resampling.',
      'COMMENT JIS Roman slots 5C and 7E map to U+00A5 and U+203E, not ASCII backslash/tilde.',
      'COMMENT Cell-bottom baseline is an export convention, not verified device layout.',
      f'FONT -archive-{device}-medium-r-normal--{height}-{height*10}-72-72-p-0-iso10646-1',
      f'SIZE {height} 72 72', f'FONTBOUNDINGBOX {width} {height} 0 0', 'STARTPROPERTIES 4',
      f'FONT_ASCENT {height}', 'FONT_DESCENT 0', 'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"',
      'ENDPROPERTIES', f'CHARS {len(glyphs)}']
    for cp,(w,h,frame) in sorted(glyphs.items()):
        rb=(w+7)//8
        if len(frame)!=rb*h: raise ValueError('Invalid frame')
        lines += [f'STARTCHAR U{cp:04X}',f'ENCODING {cp}',f'SWIDTH {round(w*1000/height)} 0',
                  f'DWIDTH {w} 0',f'BBX {w} {h} 0 0','BITMAP']
        lines += [frame[y*rb:(y+1)*rb].hex().upper() for y in range(h)]
        lines += ['ENDCHAR']
    return ('\n'.join(lines+['ENDFONT',''])).encode('ascii')

def export(source, output, device):
    mod,base,w,h,rb=CONFIG[device]; output=Path(output)
    mod.reject_symlinks(output)
    if output.exists():raise ValueError('Output directory must not exist')
    rom=mod.load_rom(source); ank=extract_ank(rom,device)
    cjk={cp:(h,h,frame) for cp,frame in mod.extract(rom)}
    if set(cjk)&set(ank):raise ValueError('Overlapping Unicode mappings')
    artifacts={f'{device}-ank.bdf':make_bdf(ank,h,device),
               f'{device}-combined.bdf':make_bdf(cjk|ank,h,device)}
    report={'source_sha256':mod.ROM_SHA256,'ank_glyphs':len(ank),'ascii_glyphs':93,
            'ascii_missing':['U+005C','U+007E'],'jis_roman_exceptions':{'5C':'U+00A5','7E':'U+203E'},
            'cjk_glyphs':len(cjk),'combined_glyphs':len(cjk)+len(ank),
            'ank_frame':[w,h],'cjk_frame':[h,h],
            'sha256':{k:hashlib.sha256(v).hexdigest() for k,v in artifacts.items()}}
    artifacts['report.json']=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()
    output.mkdir(parents=True,exist_ok=False)
    for name,data in artifacts.items():
        with (output/name).open('xb') as f:f.write(data)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--device',choices=CONFIG,required=True);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(export(a.rom,a.output,a.device),indent=2))
if __name__=='__main__':main()
