from approved_cxdos import before_cxdos_rows,before_cxdos_bytes,MANIFEST as CXDOS
"""Verify one reviewed JQK release and all preceding public files."""
import json,unittest
from PIL import Image
from approved_jqk import ROOT as R,MANIFEST as M,IDS,sha,digest,before_jqk_rows,before_jqk_bytes
class JQK(unittest.TestCase):
 def test_single_addition(self):
  rows=before_cxdos_rows(json.loads((R/'data/catalog.json').read_text()));old=before_jqk_rows(rows)
  self.assertEqual(IDS,['jqk_release_j_16x15']);self.assertEqual(len(rows),265);self.assertEqual(len(old),264)
  self.assertEqual(digest(old),M['baseRowsSha256']);self.assertEqual(sum(r['priority']>0 for r in rows),20)
  for p,h in M['baseFilesSha256'].items():self.assertEqual(sha(before_jqk_bytes(p)),h,p)
  for p,h in M['newFileHashes'].items():self.assertEqual(sha(before_cxdos_bytes(p)),h,p)
  actual={str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
  self.assertEqual(actual-set(CXDOS['newPaths']),set(M['baseFilesSha256'])|set(M['newPaths']))
  row=rows[-1];self.assertEqual(row['text'],'视野无限广，窗外有蓝天。')
  self.assertEqual(row['asciiOrigin'],'fullwidth-native');self.assertEqual(row['nativeEvidence']['gb2312Han'],6763);self.assertEqual(row['priority'],0)
  im=Image.open(R/row['specimen']);self.assertEqual(im.size,(432,32));self.assertEqual(len(set(im.getdata())),2)
  for y0,text in [(0,row['text']),(17,row['asciiText'])]:
   for i,c in enumerate(text):self.assertEqual(bool(im.crop((i*16,y0,(i+1)*16,y0+15)).getbbox()),c!='　',c)
if __name__=='__main__':unittest.main()
