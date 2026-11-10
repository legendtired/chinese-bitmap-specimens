"""Optional independent BDF sample decoding, not an arbitrary-text export endpoint."""
from pathlib import Path
import hashlib,json,os
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
TEXT='视野无限广，窗外有蓝天。'
EXPECTED={
 'simsun_v303_12':'5ca5e889c1fe151e8e25b8d243635714e490b86afd95c76f63449d1a5cc0f2a9',
 'simsun_v303_14':'c488ac98509336d6ecd76b42c55e2b2796ce8463b65454c87247c63bf81dd828',
 'simsun_v503_12':'57f9fa9514e83387df9bb61952d6865d5d45eb0d17a3b523044138a689e2c906',
 'simsun_v503_14':'dc6184ab692d32a4f6b9de44bf6469068f52cf245ae1bcea958960eec4fc68c1'}
for version in ('303','503'):
 directory=os.environ.get('SIMSUN_V'+version+'_BDF_DIR')
 if not directory:
  print(f'SimSun {version}: private source verification SKIPPED; supply SIMSUN_V{version}_BDF_DIR')
  continue
 for size in (12,14):
  ident=f'simsun_v{version}_{size}'
  # Old 5.03 input alias may be retained in a private diagnostic archive.
  source=Path(directory)/(ident+'.bdf')
  if not source.exists() and version=='503':source=Path(directory)/f'simsun_native_{size}.bdf'
  raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED[ident]
  alltext=raw.decode('ascii');ascent=int(next(line.split()[1] for line in alltext.splitlines() if line.startswith('FONT_ASCENT ')))
  glyphs={}
  for block in alltext.split('STARTCHAR ')[1:]:
   lines=block.splitlines();code=int(next(s.split()[1] for s in lines if s.startswith('ENCODING ')))
   if code not in map(ord,TEXT):continue
   bbx=tuple(map(int,next(s for s in lines if s.startswith('BBX ')).split()[1:]));advance=int(next(s for s in lines if s.startswith('DWIDTH ')).split()[1])
   start=lines.index('BITMAP')+1;bitmap=lines[start:lines.index('ENDCHAR')]
   glyphs[code]=(bbx,advance,bitmap)
  assert set(map(ord,TEXT))==set(glyphs)
  canvas=Image.new('RGBA',(size*len(TEXT),size),(0,0,0,0));cursor=0
  for ch in TEXT:
   (w,h,x,y),advance,hexrows=glyphs[ord(ch)]
   assert advance==size and len(hexrows)==h
   # Pillow raw decoder is independent of the production bit-shift renderer.
   plane=Image.frombytes('1',(w,h),b''.join(bytes.fromhex(s) for s in hexrows),'raw','1',(w+7)//8,1)
   pixels=plane.load()
   for yy in range(h):
    for xx in range(w):
     if pixels[xx,yy]:canvas.putpixel((cursor+x+xx,ascent-y-h+yy),(28,31,33,255))
   cursor+=advance
  with Image.open(ROOT/f'assets/specimens/{ident}.png') as public:
   assert canvas.mode==public.mode and canvas.size==public.size and canvas.tobytes()==public.tobytes(),ident
  assert source.read_bytes()==raw
  print(ident+': independent exact source sample pixels, BBX, bearing, baseline and advance PASS')
