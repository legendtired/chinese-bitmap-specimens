from approved_rongta import MANIFEST as RONGTA
from approved_cxdos import MANIFEST as CXDOS
from approved_jqk import MANIFEST as JQK
from approved_gtwin import MANIFEST as GTWIN
from approved_h01 import MANIFEST as H01
from approved_palm_gbk24 import MANIFEST as PALM
from approved_zhenhan import MANIFEST as ZHENHAN
"""One separate Advisor entry, unchanged prior collection and no complete fonts."""
from pathlib import Path
import copy,json,unittest
from PIL import Image
from approved_advisor import ROOT as R,MANIFEST as M,IDS,sha,digest,before_advisor_rows,before_advisor_data,before_advisor_bytes
from approved_wonder import MANIFEST as WONDER, before_wonder_bytes, before_wonder_data, before_wonder_rows
class Advisor(unittest.TestCase):
 def test_reviewed_scope(self):
  rows=before_wonder_rows(json.loads((R/'data/catalog.json').read_text()));old=before_advisor_rows(rows)
  self.assertEqual(IDS,['motorola_advisor_16']);self.assertEqual(len(rows),258);self.assertEqual(len(old),257)
  self.assertEqual(digest(old),M['baseRowsSha256']);self.assertEqual(digest(rows[-1]),M['rowSha256'])
  self.assertEqual(rows[-1]['priority'],0);self.assertEqual(sum(r['priority']>0 for r in rows),20)
  for p,h in M['baseFilesSha256'].items():self.assertEqual(sha(before_advisor_bytes(p)),h,p)
  for p,h in M['newFileHashes'].items():self.assertEqual(sha(before_wonder_bytes(p)),h,p)
  actual={str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
  actual-=set(WONDER['newPaths']) | (set(ZHENHAN['newPaths']) | (set(PALM['newPaths']) | (set(H01['newPaths']) | (set(GTWIN['newPaths']) | (set(JQK['newPaths']) | (set(CXDOS['newPaths']) | set(RONGTA['newPaths'])))))))
  self.assertEqual(actual,set(M['baseFilesSha256'])|set(M['newPaths']))
  for p in actual:
   f=R/p;self.assertFalse(f.is_symlink());self.assertEqual(f.stat().st_nlink,1)
   self.assertNotIn(f.suffix.lower(),{'.bdf','.rom','.bin','.woff','.woff2','.ttf','.otf','.zip','.7z'})
  bad=copy.deepcopy(rows);bad[-1]['name']+=' changed'
  with self.assertRaises(AssertionError):before_advisor_rows(bad)
  bad=before_wonder_data('data/collection-history.json',json.loads((R/'data/collection-history.json').read_text()));bad['batches'][-1]['ids'].append('wrong')
  with self.assertRaises(AssertionError):before_advisor_data('data/collection-history.json',bad)
 def test_pixels_and_boundaries(self):
  row=before_wonder_rows(json.loads((R/'data/catalog.json').read_text()))[-1]
  self.assertEqual((row['width'],row['height']),(16,16))
  png=R/row['specimen'];im=Image.open(png)
  self.assertEqual(im.size,(row['specimenWidth'],row['specimenHeight']))
  self.assertEqual(sha(png.read_bytes()),row['specimenSha256'])
  self.assertEqual(len(row['text']),10)
  self.assertEqual(im.size,(160,16));self.assertEqual(im.mode,'RGBA')
  self.assertLessEqual(len(set(im.getdata())),2)
  self.assertEqual(row['asciiText'],'');self.assertNotEqual(row['asciiOrigin'],'native')
  self.assertIn('6,763',row['coverage']);self.assertIn('2,258',row['notes'])
  self.assertIn('不能据此确定',row['notes']);self.assertEqual(row['sourceUrl'],'https://0w0.pw/529.html')
if __name__=='__main__':unittest.main(verbosity=2)
