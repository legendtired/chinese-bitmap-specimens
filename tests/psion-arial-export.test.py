"""No source data embedded; actual ROM roundtrip is opt-in."""
import importlib.util,os,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/psion_arial_to_bdf.py'
s=importlib.util.spec_from_file_location('psion_arial',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_source_guards(self):
  for fn in (m.decode,m.arial,m.combined):
   with self.assertRaises(ValueError):fn(b'invalid source',8)
 @unittest.skipUnless(os.getenv('PSION_ARIAL_ROM'),'local ROM not supplied')
 def test_actual_original_glyphs(self):
  rom=Path(os.environ['PSION_ARIAL_ROM']).read_bytes()
  for size,count in [(8,16810),(11,16818)]:
   han=m.decode(rom[0x7815d0:0x7815d0+0x158130],size);lat=m.arial(rom[0x2c1480:0x2c1480+0x23085],size);all=m.combined(rom,size)
   self.assertEqual(set(lat),set(range(32,127)));self.assertEqual(len(all),count)
   for cp,g in han.items():self.assertEqual(all[cp],g)
   for cp,g in lat.items():self.assertEqual(all[cp],g)
if __name__=='__main__':unittest.main()
