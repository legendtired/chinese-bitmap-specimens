from approved_rongta import MANIFEST as RONGTA
from approved_cxdos import MANIFEST as CXDOS
from approved_jqk import before_jqk_rows,before_jqk_bytes,MANIFEST as JQK
"""Verify the single approved GTWIN addition and preserve the preceding release."""
import json,unittest
from PIL import Image
from approved_gtwin import ROOT as R,MANIFEST as M,IDS,sha,digest,before_gtwin_rows,before_gtwin_bytes
class GTWIN(unittest.TestCase):
 def test_single_addition(self):
  rows=before_jqk_rows(json.loads((R/'data/catalog.json').read_text()));old=before_gtwin_rows(rows)
  self.assertEqual(IDS,['panasonic_gtwin_mdsch_16']);self.assertEqual(len(rows),264);self.assertEqual(len(old),263)
  self.assertEqual(digest(old),M['baseRowsSha256']);self.assertEqual(sum(r['priority']>0 for r in rows),20)
  for p,h in M['baseFilesSha256'].items():self.assertEqual(sha(before_gtwin_bytes(p)),h,p)
  for p,h in M['newFileHashes'].items():self.assertEqual(sha(before_jqk_bytes(p)),h,p)
  actual={str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
  self.assertEqual(actual-(set(JQK['newPaths']) | (set(CXDOS['newPaths']) | set(RONGTA['newPaths']))),set(M['baseFilesSha256'])|set(M['newPaths']))
  row=rows[-1];self.assertEqual(row['text'],'视野无限广，窗外有蓝天。');self.assertEqual(row['asciiText'],'0123456789 AaBb GgMm !?:+-.')
  self.assertEqual(row['nativeEvidence']['gb2312Han'],6763);self.assertEqual(row['nativeEvidence']['printableAscii'],95)
  self.assertEqual(row['asciiOrigin'],'native');self.assertEqual(row['priority'],0);self.assertEqual(row['missing'],[])
  self.assertEqual(Image.open(R/row['specimen']).size,(216,34))
if __name__=='__main__':unittest.main()
