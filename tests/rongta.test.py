import json,unittest
from PIL import Image
from approved_rongta import ROOT as R,MANIFEST as M,IDS,sha,digest,before_rongta_rows,before_rongta_bytes
class Rongta(unittest.TestCase):
 def test_reviewed_pair(self):
  rows=json.loads((R/'data/catalog.json').read_text());old=before_rongta_rows(rows)
  self.assertEqual(IDS,['rongta_rls1000_16','rongta_rls1000_24']);self.assertEqual(len(rows),268);self.assertEqual(len(old),266)
  self.assertEqual(digest(old),M['baseRowsSha256'])
  for p,h in M['baseFilesSha256'].items():self.assertEqual(sha(before_rongta_bytes(p)),h,p)
  for p,h in M['newFileHashes'].items():self.assertEqual(sha((R/p).read_bytes()),h,p)
  actual={str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
  self.assertEqual(actual,set(M['baseFilesSha256'])|set(M['newPaths']))
  for row,w,lw in zip(rows[-2:],[16,24],[8,24]):
   self.assertEqual(row['text'],'视野无限广，窗外有蓝天。');self.assertEqual(row['nativeEvidence']['gb2312Han'],6763)
   im=Image.open(R/row['specimen']);self.assertEqual(im.size,(max(len(row['text'])*w,len(row['asciiText'])*lw),2*w+2));self.assertEqual(len(set(im.getdata())),2)
   for y0,text,step in [(0,row['text'],w),(w+2,row['asciiText'],lw)]:
    for i,c in enumerate(text):
     if c not in '　 ':self.assertTrue(im.crop((i*step,y0,(i+1)*step,y0+w)).getbbox(),c)
if __name__=='__main__':unittest.main()
