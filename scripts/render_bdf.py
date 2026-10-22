#!/usr/bin/env python3
"""Render saved BDF bitmap pixels; no outline rasterization or font fallback."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def read_bdf(path):
 raw=path.read_bytes();data=gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw
 text=data.decode('ascii',errors='replace');props={};glyphs={};cur=None;bitmap=False
 for line in text.splitlines():
  fields=line.split();key=fields[0] if fields else ''
  if key=='STARTCHAR':cur={'rows':[]};bitmap=False
  elif key=='ENDCHAR':
   if cur is not None and cur.get('encoding',-1)>=0 and 'bbx'in cur and 'advance'in cur:
    assert len(cur['rows'])==cur['bbx'][1],'Incorrect BITMAP row count';glyphs[cur['encoding']]=cur
   cur=None;bitmap=False
  elif cur is not None:
   if key=='ENCODING':cur['encoding']=int(fields[1])
   elif key=='BBX':cur['bbx']=list(map(int,fields[1:5]))
   elif key=='DWIDTH':cur['advance']=int(fields[1])
   elif key=='BITMAP':bitmap=True
   elif bitmap:cur['rows'].append(line.strip())
  elif key in ['FONTBOUNDINGBOX','FONT_ASCENT','FONT_DESCENT','CHARSET_REGISTRY','CHARSET_ENCODING','FONT','SIZE']:
   props[key]=' '.join(fields[1:]).strip('"')
 if not glyphs:raise ValueError('No usable BDF bitmap glyphs')
 return props,glyphs,hashlib.sha256(raw).hexdigest()
def codepoint(c,encoding):
 if encoding=='unicode':return ord(c)
 try:b=c.encode(encoding)
 except UnicodeEncodeError:return None
 if len(b)==1:return b[0]
 if len(b)==2:return int.from_bytes(b,'big')
 return None
def render(font,text,encoding,output):
 from PIL import Image
 props,glyphs,sha=read_bdf(font);bbox=list(map(int,props.get('FONTBOUNDINGBOX','16 16 0 0').split()));default=max(1,bbox[0]);ascent=int(props.get('FONT_ASCENT',max(1,bbox[1]+bbox[3])));descent=int(props.get('FONT_DESCENT',max(0,-bbox[3])))
 lines=text.split('\n');placements=[];missing=[];lineinfo=[];top=0;minx=0;maxx=1
 for line in lines:
  cursor=0;items=[];absent=[];up=ascent;down=descent
  for c in line:
   g=glyphs.get(codepoint(c,encoding));advance=g['advance'] if g else default
   if g:
    w,h,x,y=g['bbx'];up=max(up,y+h);down=max(down,-y);items.append((cursor,c,g));minx=min(minx,cursor+x);maxx=max(maxx,cursor+x+w)
   else:absent.append(c)
   cursor+=advance
  height=max(1,up+down,bbox[1]);maxx=max(maxx,cursor)
  for x,c,g in items:placements.append((x,top+up,g))
  lineinfo.append({'text':line,'missing':list(dict.fromkeys(absent)),'advanceWidth':cursor,'height':height});missing.extend(absent);top+=height+2
 image=Image.new('RGBA',(maxx-minx,max(1,top-2)),(0,0,0,0));pix=image.load()
 for cursor,baseline,g in placements:
  w,h,bx,by=g['bbx'];x=cursor+bx-minx;y=baseline-by-h
  for yy,row in enumerate(g['rows']):
   bits=int(row or '0',16);bitlen=len(row)*4
   if bitlen<w:raise ValueError('BITMAP row is shorter than BBX width')
   for xx in range(w):
    if bits & (1<<(bitlen-1-xx)):pix[x+xx,y+yy]=(28,31,33,255)
 output.parent.mkdir(parents=True,exist_ok=True);image.save(output)
 report={'format':'bdf-bitmap-preview-v1','sourceName':font.name,'sourceSha256':sha,'encoding':encoding,'text':text,'lines':lineinfo,'missing':list(dict.fromkeys(missing)),'specimenWidth':image.width,'specimenHeight':image.height,'specimenSha256':hashlib.sha256(output.read_bytes()).hexdigest(),'png':output.name,'method':'Direct saved BDF BITMAP pixels; original DWIDTH/BBX; no fallback, antialiasing or outline rasterization.'}
 output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--font',required=True);p.add_argument('--inspect',action='store_true');p.add_argument('--encoding',choices=['unicode','gb2312','big5']);p.add_argument('--text');p.add_argument('--output');a=p.parse_args();font=Path(a.font).resolve()
 if not font.is_file():p.error('Source BDF not found: '+str(font)+'. Install optional research materials under local-research/ or supply an existing BDF path; no font is downloaded automatically.')
 if a.inspect:
  props,glyphs,sha=read_bdf(font);print(json.dumps({'properties':props,'glyphCount':len(glyphs),'sourceSha256':sha},ensure_ascii=False,indent=2))
 else:
  if not a.encoding or a.text is None or not a.output:p.error('Rendering requires --encoding, --text and --output')
  output=Path(a.output).resolve();local=(ROOT/'local-research').resolve()
  if not output.is_relative_to(local):p.error('Experimental output must stay under local-research/')
  props,_,_=read_bdf(font);registry=props.get('CHARSET_REGISTRY','').upper()
  if a.encoding=='unicode' and registry and not any(x in registry for x in ['ISO10646','UNICODE']):p.error('BDF registry is not Unicode; choose a verified supported encoding, do not guess.')
  print(json.dumps(render(font,a.text.replace('\\n','\n'),a.encoding,output),ensure_ascii=False,indent=2))
