#!/usr/bin/env python3
"""Redraw only the fixed HP-UX specimens from exact, user-supplied PCFs.
Requires Pillow and system iconv EUC-TW. No network, font installation or BDF export.
"""
import argparse,hashlib,io,json,struct,subprocess
from pathlib import Path
from PIL import Image,PcfFontFile
ROOT=Path(__file__).resolve().parents[1]
CHINESE='視野無限廣，窗外有藍天。'
ASCII='0123456789 AaBb GgMm !?:+-.'

def parse(blob):
    if blob[:4]!=b'\x01fcp':raise ValueError('Expected decompressed PCF')
    fp=io.BytesIO(blob);fp.seek(4);count=struct.unpack('<I',fp.read(4))[0]
    obj=object.__new__(PcfFontFile.PcfFontFile);obj.fp=fp;obj.toc={}
    for _ in range(count):
        tag,fmt,size,offset=struct.unpack('<IIII',fp.read(16));obj.toc[tag]=(fmt,size,offset)
    props=obj._load_properties();metrics=obj._load_metrics();bitmaps=obj._load_bitmaps(metrics)
    fp,fmt,i16,i32=obj._getformat(PcfFontFile.PCF_BDF_ENCODINGS)
    fc,lc,fr,lr,default=[i16(fp.read(2))for _ in range(5)];enc={}
    for row in range(fr,lr+1):
        for col in range(fc,lc+1):
            ix=i16(fp.read(2))
            if ix!=65535:enc[row*256+col]=ix
    return props,metrics,bitmaps,enc

def sample_codes():
    result={}
    for char in set(CHINESE):
        b=subprocess.run(['iconv','-f','UTF-8','-t','EUC-TW'],input=char.encode(),capture_output=True,check=True).stdout
        if len(b)==2:plane=1;row,col=b
        elif len(b)==4 and b[0]==0x8e:plane=b[1]-0xa0;row,col=b[2:]
        else:raise ValueError('Unexpected CNS mapping')
        if plane not in [1,2]:raise ValueError('Sample outside supported CNS planes')
        result[char]=(f'n{plane}',(row-128)*256+col-128)
    result.update({c:('na',ord(c))for c in set(ASCII)})
    return result

def render(source,size):
    manifest=json.loads((ROOT/'data/hpux-sung-sources.json').read_text());fonts={}
    for suffix in ['n1','n2','na']:
        name=f'sung{size}{suffix}.pcf';b=(source/name).read_bytes()
        expected=next(r['pcfSha256']for r in manifest if Path(r['path']).name==name)
        if hashlib.sha256(b).hexdigest()!=expected:raise ValueError('Unexpected PCF hash: '+name)
        fonts[suffix]=parse(b)
    glyphs={}
    for char,(suffix,code)in sample_codes().items():
        props,metrics,bitmaps,enc=fonts[suffix];ix=enc[code];glyphs[char]=(metrics[ix],bitmaps[ix])
    lines=[CHINESE,ASCII];width=max(sum(glyphs[c][0][4]for c in s)for s in lines)+8
    out=Image.new('RGBA',(width,size*2+12),(255,255,255,0))
    for li,line in enumerate(lines):
        x=4
        for c in line:
            met,img=glyphs[c]
            # Exact audited fonts have zero left bearing and identical ascent/descent.
            if met[2]!=0 or met[1]!=size:raise ValueError('Unexpected source metrics')
            out.paste(Image.new('RGBA',img.size,(28,31,33,255)),(x,4+li*(size+4)),img);x+=met[4]
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    if a.output.exists():p.error('Output must not already exist')
    rendered=[(n,render(a.source,n))for n in [24,34,42]]
    a.output.mkdir(parents=True)
    for n,img in rendered:img.save(a.output/f'hpux_sung_{n}.png')
if __name__=='__main__':main()
