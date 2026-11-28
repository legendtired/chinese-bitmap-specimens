from approved_rongta import before_rongta_rows,before_rongta_bytes,MANIFEST as RONGTA
"""Verify one reviewed CXDOS release and preserve all prior public files."""
import json,unittest
from PIL import Image
from approved_cxdos import ROOT as R,MANIFEST as M,IDS,sha,digest,before_cxdos_rows,before_cxdos_bytes
class CXDOS(unittest.TestCase):
 def test_single_addition(self):
  rows=before_rongta_rows(json.loads((R/'data/catalog.json').read_text()));old=before_cxdos_rows(rows)
  self.assertEqual(IDS,['cxdos_50_cclib_16']);self.assertEqual(len(rows),266);self.assertEqual(len(old),265)
  self.assertEqual(digest(old),M['baseRowsSha256']);self.assertEqual(sum(r['priority']>0 for r in rows),20)
  for p,h in M['baseFilesSha256'].items():self.assertEqual(sha(before_cxdos_bytes(p)),h,p)
  for p,h in M['newFileHashes'].items():self.assertEqual(sha(before_rongta_bytes(p)),h,p)
  actual={str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
  self.assertEqual(actual-set(RONGTA['newPaths']),set(M['baseFilesSha256'])|set(M['newPaths']))
  row=rows[-1];self.assertEqual(row['text'],'视野无限广，窗外有蓝天。')
  self.assertEqual(row['asciiOrigin'],'fullwidth-native');self.assertEqual(row['nativeEvidence']['gb2312Han'],6763);self.assertEqual(row['priority'],0);self.assertEqual(row['asciiMissing'],['　'])
  im=Image.open(R/row['specimen']);self.assertEqual(im.size,(432,34));self.assertEqual(len(set(im.getdata())),2)
  for y0,text in [(0,row['text']),(18,row['asciiText'])]:
   for i,c in enumerate(text):self.assertEqual(bool(im.crop((i*16,y0,(i+1)*16,y0+16)).getbbox()),c!='　',c)
if __name__=='__main__':unittest.main()
