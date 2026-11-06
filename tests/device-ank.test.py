"""Synthetic tests only; no embedded historical font bytes."""
import sys, unittest, tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import device_ank_to_bdf as m
class TestANK(unittest.TestCase):
 def test_rejects_source(self):
  for dev in m.CONFIG:
   with self.assertRaises(ValueError):m.extract_ank(b'bad',dev)
 def test_native_roman_mapping_and_frames(self):
  for dev,(mod,base,w,h,rb) in m.CONFIG.items():
   b=bytearray(mod.ROM_SIZE)
   for cp in range(33,127):b[base+cp*h*rb]=128
   with patch.object(mod,'ROM_SHA256',m.hashlib.sha256(b).hexdigest()):
    g=m.extract_ank(bytes(b),dev)
   self.assertEqual(len(g),95);self.assertNotIn(92,g);self.assertNotIn(126,g)
   self.assertIn(165,g);self.assertIn(8254,g)
   for cp in list(range(48,58))+list(range(65,91))+list(range(97,123)):
    self.assertEqual(g[cp][:2],(w,h))
   out=m.make_bdf(g,h,dev).decode();self.assertIn('CHARS 95',out)
 def test_existing_destination(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):m.export('does-not-exist',d,'sharp')
 def test_bad_frame(self):
  with self.assertRaises(ValueError):m.make_bdf({65:(8,16,b'x')},16,'sharp')
unittest.main()
