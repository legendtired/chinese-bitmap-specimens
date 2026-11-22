"""One H-01 specimen; prior collection stays immutable."""
import copy,json,unittest
from PIL import Image
from approved_h01 import ROOT as R,MANIFEST as M,IDS,sha,digest,before_h01_rows,before_h01_data,before_h01_bytes
class H01(unittest.TestCase):
 def test_scope_and_preservation(self):
  rows=json.loads((R/'data/catalog.json').read_text());old=before_h01_rows(rows)
  self.assertEqual(IDS,['h01_16'])
  self.assertEqual(M['baseCommit'],'6dca68070d8a4a78984e1ec8634df120d7e1e7fc')
  self.assertEqual(len(rows),263);self.assertEqual(len(old),262)
  self.assertEqual(digest(old),M['baseRowsSha256'])
  self.assertEqual({r['id']:digest(r) for r in rows[-1:]},M['rowSha256ById'])
  self.assertEqual([r['priority'] for r in rows[-1:]],[0]);self.assertEqual(sum(r['priority']>0 for r in rows),20)
  self.assertEqual(M['batch'],{'sourceManifest':'release-h01.json','ids':IDS})
  for p,h in M['baseFilesSha256'].items():self.assertEqual(sha(before_h01_bytes(p)),h,p)
  for p,h in M['newFileHashes'].items():self.assertEqual(sha((R/p).read_bytes()),h,p)
  actual={str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
  self.assertEqual(actual,set(M['baseFilesSha256'])|set(M['newPaths']))
  self.assertEqual(set(M['newPaths'])-{'data/release-h01.json'},set(M['newFileHashes']))
  for p in actual:
   f=R/p;self.assertFalse(f.is_symlink());self.assertEqual(f.stat().st_nlink,1)
   self.assertNotIn(f.suffix.lower(),{'.bdf','.rom','.bin','.fnt','.woff','.woff2','.ttf','.otf','.zip','.7z'})
 def test_fixed_specimens(self):
  rows=json.loads((R/'data/catalog.json').read_text())[-1:]
  for row,cell in zip(rows,[(16,16)]):
   self.assertEqual((row['width'],row['height']),cell)
   self.assertEqual((row['cellWidth'],row['cellHeight']),cell)
   self.assertNotEqual(row.get('sampleKind'),'reference')
   self.assertEqual(row['hanMissing'],['，','。'])
   self.assertEqual(row['text'],'视野无限广，窗外有蓝天。')
   self.assertEqual(row['asciiText'],'0123456789 AaBb GgMm !?:+-.')
   self.assertEqual(row['asciiOrigin'],'native')
   self.assertEqual(row['nativeEvidence']['gb2312Level1Han'],3755)
   self.assertEqual(row['nativeEvidence']['verifiedAsciiMappings'],93)
   png=R/row['specimen'];im=Image.open(png)
   self.assertEqual(im.size,(row['specimenWidth'],row['specimenHeight']))
   self.assertEqual(sha(png.read_bytes()),row['specimenSha256'])
   self.assertEqual(im.size,(216,34))
   self.assertIsNone(im.crop((5*16,0,6*16,16)).getbbox())
   self.assertIsNone(im.crop((11*16,0,12*16,16)).getbbox())
   self.assertIsNone(im.crop((0,16,216,18)).getbbox())
   for i,c in enumerate(row['asciiText']):
    self.assertEqual(bool(im.crop((i*8,18,(i+1)*8,34)).getbbox()), c!=' ',repr(c))
   self.assertEqual(len(set(im.getdata())),2)
   self.assertTrue(row['sourceUrl'].startswith('https://'))
   self.assertTrue(row['licenseNote']);self.assertTrue(row['nativeEvidence'])
 def test_tampering(self):
  rows=json.loads((R/'data/catalog.json').read_text())
  for ident in IDS:
   bad=copy.deepcopy(rows);next(r for r in bad if r['id']==ident)['name']+=' changed'
   with self.assertRaises(AssertionError):before_h01_rows(bad)
  with self.assertRaises(AssertionError):before_h01_rows([*rows[:-2],rows[-1],rows[-2]])
  bad=json.loads((R/'data/collection-history.json').read_text());bad['batches'][-1]['ids'].append('wrong')
  with self.assertRaises(AssertionError):before_h01_data('data/collection-history.json',bad)
  bad=json.loads((R/'data/summary.json').read_text());bad['unreviewed']=True
  with self.assertRaises(AssertionError):before_h01_data('data/summary.json',bad)
if __name__=='__main__':unittest.main(verbosity=2)
