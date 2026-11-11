"""One approved Emperor specimen, original pixels, and narrow publication scope."""
import copy,hashlib,importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
from approved_emperor import MANIFEST,IDS,before_emperor_rows,before_emperor_data,before_emperor_bytes,digest,sha
R=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('emperor',R/'scripts/emperor_dos_specimen.py');m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)
FNT=os.environ.get('EMPEROR_FNT');IDX=os.environ.get('EMPEROR_IDX')
def png(scale):return R/'assets/specimens'/('emperor_dos_16x15'+('' if scale==1 else '_4x')+'.png')
class Public(unittest.TestCase):
 def test_scope_and_preservation(self):
  rows=json.loads((R/'data/catalog.json').read_text());old=before_emperor_rows(rows)
  self.assertEqual(IDS,['emperor_dos_16x15']);self.assertEqual(len(rows),257);self.assertEqual(len(old),256)
  self.assertEqual(digest(old),MANIFEST['baseRowsSha256']);self.assertEqual(digest(rows[-1]),MANIFEST['rowSha256'])
  self.assertEqual(rows[-1]['priority'],0);self.assertEqual(sum(r['priority']>0 for r in rows),20)
  for p,h in MANIFEST['baseFilesSha256'].items():self.assertEqual(sha(before_emperor_bytes(p)),h,p)
  for p,h in MANIFEST['newFileHashes'].items():self.assertEqual(sha((R/p).read_bytes()),h,p)
  actual={str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
  self.assertEqual(actual,set(MANIFEST['baseFilesSha256'])|set(MANIFEST['newPaths']))
  for p in actual:
   q=R/p;self.assertFalse(q.is_symlink());self.assertEqual(q.stat().st_nlink,1)
   self.assertNotIn(q.suffix.lower(),{'.fnt','.idx','.bdf','.ttf','.otf','.fon','.zip','.rom','.bin','.7z'})
  bad=copy.deepcopy(rows);bad[-1]['name']+=' changed'
  with self.assertRaises(AssertionError):before_emperor_rows(bad)
  bad=json.loads((R/'data/collection-history.json').read_text());bad['batches'][-1]['ids'].append('wrong')
  with self.assertRaises(AssertionError):before_emperor_data('data/collection-history.json',bad)
 def test_fixed_pixels_and_hashes(self):
  self.assertEqual((m.TEXT,m.WIDTH,m.HEIGHT),('視野無限廣，窗外有藍天。',16,15))
  self.assertEqual((m.SOURCE_BYTES,m.INDEX_BYTES),(85740,30210))
  self.assertEqual(m.PNG_SHA256,{1:'c81ea562f0db05813adbc1d58550e50b7ae4d57d3c78fe7e9d8fcb343e58f07f',4:'97f67f02a0302beb5b221bb3d4b6d3b2e44cddacaf93c63bb94bff66bec5d1ab'})
  one=Image.open(png(1));four=Image.open(png(4));self.assertEqual(one.size,(192,15));self.assertEqual(four.size,(768,60));self.assertEqual(one.mode,'RGBA')
  self.assertEqual(four.tobytes(),one.resize(four.size,Image.Resampling.NEAREST).tobytes())
  self.assertEqual(set(one.getdata()),{(0,0,0,0),(0,0,0,255)})
  for n in (1,4):self.assertEqual(sha(png(n).read_bytes()),m.PNG_SHA256[n])
 def test_invalid_inputs(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);bad=p/'bad';bad.write_bytes(b'wrong');out=p/'out.png'
   with self.assertRaises(ValueError):m.render(bad,bad,out)
   with self.assertRaises(ValueError):m.fixed_image(bytes(m.SOURCE_BYTES),bytes(m.INDEX_BYTES))
   for flags in (['--text','unapproved'],['--scale','2'],['--all-glyphs']):
    result=subprocess.run([sys.executable,str(R/'scripts/emperor_dos_specimen.py'),'--source',str(bad),'--index',str(bad),'--output',str(out),*flags],capture_output=True)
    self.assertNotEqual(result.returncode,0)
   self.assertFalse(out.exists())
@unittest.skipUnless(FNT and IDX,'Original source checks skipped: set EMPEROR_FNT and EMPEROR_IDX')
class Original(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.f=Path(FNT);cls.i=Path(IDX);cls.data=m.checked_source(cls.f);cls.index=m.checked_source(cls.i,m.INDEX_BYTES,m.INDEX_SHA256)
 def test_independent_index_and_pixels(self):
  trails=list(range(0x40,0x7f))+list(range(0xa1,0xff));result=Image.new('RGBA',(192,15),(0,0,0,0))
  mapped={}
  for base,start,end in ((1025,0xa140,0xa3bf),(2049,0xa440,0xc67e),(7450,0xc940,0xf9fe)):
   codes=[h*256+t for h in range(start>>8,(end>>8)+1) for t in trails if start<=h*256+t<=end]
   for offset,code in enumerate(codes):
    value=int.from_bytes(self.index[(base+offset)*2:(base+offset)*2+2],'little')
    if not value:continue
    character=code.to_bytes(2,'big').decode('cp950');self.assertNotIn(character,mapped);mapped[character]=value-1
  self.assertEqual(len(mapped),2857);self.assertEqual(set(range(2858))-set(mapped.values()),{2857})
  han=[c for c in mapped if 0x3400<=ord(c)<=0x9fff];self.assertEqual(len(han),2832)
  self.assertTrue(all(any(self.data[mapped[c]*30:(mapped[c]+1)*30]) for c in han))
  for n,c in enumerate(m.TEXT):
   cell=Image.frombytes('1',(16,15),self.data[mapped[c]*30:(mapped[c]+1)*30]);ink=Image.new('RGBA',(16,15),(0,0,0,0));ink.putalpha(cell.convert('L'));result.paste(ink,(n*16,0))
  self.assertEqual(result.tobytes(),Image.open(png(1)).tobytes());self.assertEqual(result.tobytes(),m.fixed_image(self.data,self.index).tobytes())
 def test_render_and_rejections(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   for n in (1,4):m.render(self.f,self.i,p/f'out{n}.png',n);self.assertEqual((p/f'out{n}.png').read_bytes(),png(n).read_bytes())
   out=p/'new.png';bad=p/'bad';changed=bytearray(self.index);changed[2050]^=1;bad.write_bytes(changed)
   with self.assertRaises(ValueError):m.render(self.f,bad,out)
   changed=bytearray(self.data);changed[22]^=1;bad.write_bytes(changed)
   with self.assertRaises(ValueError):m.render(bad,self.i,out)
   for scale in (True,False,0,2,1.0,4.0,'4'):
    with self.assertRaises(ValueError):m.render(self.f,self.i,out,scale)
   with self.assertRaises(FileExistsError):m.render(self.f,self.i,p/'out1.png')
   link=p/'link';link.symlink_to(self.f);fifo=p/'fifo';os.mkfifo(fifo);folder=p/'folder';folder.mkdir();hard=p/'hard';copy=p/'copy';copy.write_bytes(self.data);os.link(copy,hard)
   parentlink=p/'parent';parentlink.symlink_to(p,target_is_directory=True)
   for source in (link,fifo,folder,hard,parentlink/'copy'):
    with self.assertRaises((ValueError,OSError)):m.render(source,self.i,out)
   target=p/'target.png';target.write_bytes(b'keep');outputlink=p/'output.png';outputlink.symlink_to(target)
   for output in (outputlink,parentlink/'new.png',str(p)+'/../new.png'):
    with self.assertRaises((ValueError,OSError)):m.render(self.f,self.i,output)
   self.assertEqual(target.read_bytes(),b'keep');self.assertFalse(out.exists())
if __name__=='__main__':unittest.main(verbosity=2)
