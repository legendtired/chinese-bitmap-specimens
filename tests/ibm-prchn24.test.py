"""Run with optional local IBM source: IBM_PRCHN24=/path/PRCHN24.FNT python -m unittest ..."""
import importlib.util,os,re,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('prchn',Path(__file__).resolve().parents[1]/'scripts/ibm_prchn24_to_bdf.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_unknown_source(self):
  with self.assertRaises(ValueError):m.convert(bytes(9216))
 def test_invalid_combine(self):
  with self.assertRaises(ValueError):m.combine('garbage','garbage')
 @unittest.skipUnless(os.getenv('IBM_PRCHN24'),'local original source not supplied')
 def test_roundtrip(self):
  b=Path(os.environ['IBM_PRCHN24']).read_bytes();s=m.convert(b)
  glyphs=re.findall(r'STARTCHAR.*?ENCODING (\d+).*?BITMAP\n(.*?)\nENDCHAR',s,re.S)
  self.assertEqual([int(x[0]) for x in glyphs],list(range(32,127)))
  for code,bitmap in glyphs:
   value=0
   for row in bitmap.splitlines():
    self.assertEqual(int(row,16)&15,0);value=(value<<12)|(int(row,16)>>4)
   c=int(code);self.assertEqual(value.to_bytes(36,'big'),b[c*36:(c+1)*36])
if __name__=='__main__':unittest.main()
