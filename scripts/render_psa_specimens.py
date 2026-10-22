#!/usr/bin/env python3
"""Render fixed specimens from a separately supplied, verified private Flash input.
No firmware or glyph arrays are distributed with this script. No network access.
"""
from pathlib import Path
import argparse, hashlib, json, struct
from PIL import Image
EXPECTED='9690e1dafb21e1c7a2af839ce53ef301f05f4b7336ab1eeeb355edb1ef055201'
TABLES={0:(0x9c84,0x17c9c,0x1eca8,0x3acd8,14),2:(0x1f2ce0,0x200cf8,0x207d04,0x223d34,17)}
TEXT='视野无限广，窗外有蓝天。';ASCII='0123456789 AaBb GgMm !?:+-.'
def render(data,group,text):
 cm,wm,om,bm,h=TABLES[group];n=(wm-cm)//2
 codes=struct.unpack_from('<'+'H'*n,data,cm);widths=data[wm:wm+n];offsets=struct.unpack_from('<'+'I'*n,data,om);lookup={cp:i for i,cp in enumerate(codes)}
 assert len(lookup)==n==28684
 missing=[c for c in text if ord(c) not in lookup]
 if missing:raise ValueError(f'Source missing characters: {missing!r}; no fallback is used')
 width=sum(widths[lookup[ord(c)]] for c in text);out=Image.new('RGBA',(width,h),(0,0,0,0));x=0
 for char in text:
  i=lookup[ord(char)];w=widths[i];stride=(w+7)//8;p=bm+offsets[i]
  if i+1<n:assert offsets[i+1]-offsets[i]==h*stride
  assert p+h*stride<=len(data)
  for y in range(h):
   bits=int.from_bytes(data[p+y*stride:p+(y+1)*stride],'little')
   for column in range(w):
    if (bits>>column)&1:out.putpixel((x+column,y),(0,0,0,255))
  x+=w
 return out

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--firmware',required=True,type=Path);p.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[1]/'local-research/psa-c-screen/generated');a=p.parse_args()
 data=a.firmware.read_bytes()
 if len(data)!=4194304 or hashlib.sha256(data).hexdigest()!=EXPECTED:raise ValueError('Unexpected input; this script only supports the verified private Flash specimen')
 a.output_dir.mkdir(parents=True,exist_ok=True);result=[]
 for group,design in [(0,12),(2,14)]:
  han,latin=render(data,group,TEXT),render(data,group,ASCII);gap=5;out=Image.new('RGBA',(max(han.width,latin.width),han.height+gap+latin.height),(0,0,0,0));out.paste(han,(0,0));out.paste(latin,(0,han.height+gap));id=f'psa_c_screen_{design}';f=a.output_dir/f'{id}.png';out.save(f)
  result.append({'id':id,'group':group,'designHeight':design,'storageWidth':14 if group==0 else 16,'storageHeight':TABLES[group][-1],'specimenWidth':out.width,'specimenHeight':out.height,'specimenSha256':hashlib.sha256(f.read_bytes()).hexdigest(),'text':TEXT,'asciiText':ASCII,'missing':[]})
 (a.output_dir/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('Rendered two fixed PNGs from original row-major LSB-first bits; storage padding preserved.')
if __name__=='__main__':main()
