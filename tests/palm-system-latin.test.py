"""Palm-only supplement boundaries; synthetic NFNT plus optional real-source checks."""
from pathlib import Path
import hashlib,json,re,struct,sys,tempfile
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import palm_system_latin_to_bdf as p
import cjkos_to_bdf as c

def blocks(text):return re.findall(r'STARTCHAR [^\n]+\n.*?ENDCHAR\n',text,re.S)
def parsed(block):
 lines=block.splitlines();cp=int(next(s for s in lines if s.startswith('ENCODING ')).split()[1]);w,h,x,y=map(int,next(s for s in lines if s.startswith('BBX ')).split()[1:]);at=lines.index('BITMAP')+1
 pixels=tuple(tuple(int(bit) for bit in f'{int(row,16):0{len(row)*4}b}'[:w]) for row in lines[at:at+h])
 adv=int(next(s for s in lines if s.startswith('DWIDTH ')).split()[1]);return cp,pixels,adv,(w,h,x,y)

# Fabricated pixels exercise parsing without embedding any source glyphs.
count=95;width=3;height=11;rowwords=18;rb=rowwords*2;image=bytearray(rb*height)
for i in range(1,count+1):
 for y in range(height):
  x=i*width+(y%3);image[y*rb+x//8]|=0x80>>(x%8)
loc=26+len(image);ow=loc+2*(count+2)
head=struct.pack('>13H',0x9000,32,126,width,0,0,width,height,(ow-16)//2,9,2,0,rowwords)
source=head+image+struct.pack('>'+'H'*(count+2),*(i*width for i in range(count+2)))+b'\0\x03'*(count+2)
glyphs,metrics=p.parse_nfnt(source);assert set(glyphs)==set(range(32,127))
for malformed in [source[:-1],source+b'\0',b'bad']:
 try:p.parse_nfnt(malformed)
 except (ValueError,struct.error):pass
 else:raise AssertionError('Malformed NFNT accepted')
orig,report=c.render_bdf([{'source_code':0xA440,'codepoint':19968,'canonical':True,'pixels':tuple((1,)*12 for _ in range(12))}],{'size':12,'codec':'big5','source_sha256':'synthetic'})
combined=p.compose_bdf(orig,glyphs);assert blocks(combined)[:1]==blocks(orig)
assert 'FONTBOUNDINGBOX 12 12 0 0\n' in combined and 'FONT_ASCENT 12\nFONT_DESCENT 0\n' in combined
assert 'CHARS 96\n' in combined
for block in blocks(combined)[1:]:
 cp,pixels,adv,bbx=parsed(block);assert pixels==glyphs[cp]['pixels'] and adv==glyphs[cp]['advance'] and bbx[-1]==0
alone=p.standalone_bdf(glyphs,{'source_metrics':metrics})
assert 'FONT_ASCENT 9\nFONT_DESCENT 2\n' in alone
assert all(parsed(b)[3][-1]==-2 for b in blocks(alone))
with tempfile.TemporaryDirectory() as tmp:
 bad=Path(tmp)/'bad.rom';bad.write_bytes(b'invalid')
 try:p.load_system_latin(bad)
 except ValueError:pass
 else:raise AssertionError('Unknown ROM accepted')

# Public metadata and preview: only this row changes, original Chinese stays identical.
u=json.loads((R/'data/update-palm-latin-20261106.json').read_text());rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id']!='mstar_tv_simp_18'];a=u['after'];b=u['before']
assert next(r for r in rows if r['id']==a['id'])==a
other=[r for r in rows if r['id']!=a['id']]
assert hashlib.sha256(json.dumps(other,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==u['otherRowsSha256']
for key in ['id','name','family','text','width','height','cellWidth','cellHeight','inkWidth','inkHeight','scripts','priority','sourceIndex','nativeEvidence','hanMissing']:
 assert a[key]==b[key],key
assert a['asciiOrigin']=='native' and a['asciiMissing']==[] and a['asciiText']=='0123456789 AaBb GgMm !?:+-.'
assert a['asciiPairing']['glyphs']==95 and a['asciiPairing']['kind']=='compatible-system-composition'
assert a['asciiPairing']['originalRuntimeLayoutVerified'] is False
assert '组合排版' in a['sampleLabel'] and '非原机' in a['sampleLabel']
raw=(R/a['specimen']).read_bytes();assert hashlib.sha256(raw).hexdigest()==a['specimenSha256']
im=Image.open(R/a['specimen']).convert('RGBA');assert im.size==(156,28)
m=u['originalHanMask'];crop=im.crop((0,0,*m['topSize']))
mask=bytes(int(alpha>0 and red+green+blue<384) for red,green,blue,alpha in crop.getdata())
assert hashlib.sha256(mask).hexdigest()==m['topMaskSha256']
assert any(alpha for *_,alpha in im.crop((0,16,156,28)).getdata())

# Full local validation is available when separately supplied inputs are present.
rom=R/'local-research/palm-latin/sources/Palm-m515-4.1-en.rom';pdb=rom.parent/'FB512XMF.PDB'
if rom.exists() and pdb.exists():
 latin,info=p.load_system_latin(rom);han,hinfo=c.load_font(pdb);original,hreport=c.render_bdf(han,hinfo);merged=p.compose_bdf(original,latin)
 old=blocks(original);new=blocks(merged)
 assert len(old)==13973 and len(new)==14068 and old==new[:13973]
 assert hreport['encoded_glyphs']==13706
 for block in new[13973:]:
  cp,pixels,adv,bbx=parsed(block);assert pixels==latin[cp]['pixels'] and adv==latin[cp]['advance'] and bbx==(latin[cp]['width'],11,0,0)
 # Match every displayed ASCII pixel to the independently parsed fixed PNG.
 x=0
 for ch in a['asciiText']:
  g=latin[ord(ch)]
  for y,row in enumerate(g['pixels']):
   for xx,v in enumerate(row):assert int(im.getpixel((x+xx,17+y))[3]>0)==v
  x+=g['advance']
 with tempfile.TemporaryDirectory() as tmp:
  out=Path(tmp)/'export';report=p.export(rom,pdb,out);assert report['combined_slots']==14068
  assert (out/'cjkos-ximing-original.bdf').read_text()==original
  try:p.export(rom,pdb,out)
  except ValueError:pass
  else:raise AssertionError('Existing export was overwritten')
 print('Palm source validation: 95 ROM ASCII and all 13973 original CJK blocks preserved; BDF and fixed PNG agree.')
else:print('Palm real-source validation skipped: local research inputs not provided.')
print('Palm Latin: only retained XiMing supplemented; original Han pixels/identity/metrics unchanged; composition clearly labeled.')
