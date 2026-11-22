from approved_h01 import MANIFEST as H01
"""Exactly two approved Zhenhan device specimens; prior collection stays immutable."""
import copy,json,unittest
from approved_palm_gbk24 import before_palm_gbk24_rows, before_palm_gbk24_data, before_palm_gbk24_bytes, MANIFEST as PALM

from PIL import Image
from approved_zhenhan import ROOT as R,MANIFEST as M,IDS,sha,digest,before_zhenhan_rows,before_zhenhan_data,before_zhenhan_bytes
class Zhenhan(unittest.TestCase):
 def test_scope_and_preservation(self):
  rows=before_palm_gbk24_rows(json.loads((R/'data/catalog.json').read_text()));old=before_zhenhan_rows(rows)
  self.assertEqual(IDS,['zhenhan_16x15','zhenhan_kaiti_24'])
  self.assertEqual(len(rows),261);self.assertEqual(len(old),259)
  self.assertEqual(digest(old),M['baseRowsSha256'])
  self.assertEqual({r['id']:digest(r) for r in rows[-2:]},M['rowSha256ById'])
  self.assertEqual([r['priority'] for r in rows[-2:]],[0,0]);self.assertEqual(sum(r['priority']>0 for r in rows),20)
  self.assertEqual(M['batch'],{'sourceManifest':'release-zhenhan-v300.json','ids':IDS})
  for p,h in M['baseFilesSha256'].items():self.assertEqual(sha(before_zhenhan_bytes(p)),h,p)
  for p,h in M['newFileHashes'].items():self.assertEqual(sha(before_palm_gbk24_bytes(p)),h,p)
  actual={str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
  self.assertEqual(actual-(set(PALM['newPaths']) | set(H01['newPaths'])),set(M['baseFilesSha256'])|set(M['newPaths']))
  self.assertEqual(set(M['newPaths'])-{'data/release-zhenhan-v300.json'},set(M['newFileHashes']))
  for p in actual:
   f=R/p;self.assertFalse(f.is_symlink());self.assertEqual(f.stat().st_nlink,1)
   self.assertNotIn(f.suffix.lower(),{'.bdf','.rom','.bin','.fnt','.woff','.woff2','.ttf','.otf','.zip','.7z'})
 def test_fixed_specimens(self):
  rows=before_palm_gbk24_rows(json.loads((R/'data/catalog.json').read_text()))[-2:]
  for row,cell in zip(rows,[(16,15),(24,24)]):
   self.assertEqual((row['width'],row['height']),cell)
   self.assertEqual((row['cellWidth'],row['cellHeight']),cell)
   self.assertNotEqual(row.get('sampleKind'),'reference')
   self.assertFalse(row['hanMissing'])
   png=R/row['specimen'];im=Image.open(png)
   self.assertEqual(im.size,(row['specimenWidth'],row['specimenHeight']))
   self.assertEqual(sha(png.read_bytes()),row['specimenSha256'])
   self.assertLessEqual(len(set(im.getdata())),2)
   self.assertTrue(row['sourceUrl'].startswith('https://'))
   self.assertTrue(row['licenseNote']);self.assertTrue(row['nativeEvidence'])
 def test_tampering(self):
  rows=before_palm_gbk24_rows(json.loads((R/'data/catalog.json').read_text()))
  for ident in IDS:
   bad=copy.deepcopy(rows);next(r for r in bad if r['id']==ident)['name']+=' changed'
   with self.assertRaises(AssertionError):before_zhenhan_rows(bad)
  with self.assertRaises(AssertionError):before_zhenhan_rows([*rows[:-2],rows[-1],rows[-2]])
  bad=before_palm_gbk24_data('data/collection-history.json',json.loads((R/'data/collection-history.json').read_text()));bad['batches'][-1]['ids'].append('wrong')
  with self.assertRaises(AssertionError):before_zhenhan_data('data/collection-history.json',bad)
  bad=json.loads((R/'data/summary.json').read_text());bad['unreviewed']=True
  with self.assertRaises(AssertionError):before_zhenhan_data('data/summary.json',bad)
if __name__=='__main__':unittest.main(verbosity=2)
