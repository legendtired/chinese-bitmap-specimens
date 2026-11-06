"""Source-free safety/format tests; optional exact-source integration tests."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest import mock

R = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('samsung_r208', R/'scripts/samsung_r208_bitmap_export.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
PNG_SHA256 = '3c907fb8750476b2c59015ea73da90cac2cfafb291b2a2e1bb20bb20402b6b13'


class FormatSafety(unittest.TestCase):
    def test_synthetic_page_orientation(self):
        for width in (8, 16):
            for byte in range(width*2):
                for bit in range(8):
                    raw = bytearray(width*2)
                    raw[byte] = 1 << bit
                    glyph = m.decode_rows(raw, width)
                    expected = [0]*16
                    expected[8*(byte//width)+bit] = 1 << (width-1-byte%width)
                    self.assertEqual(glyph['rows'], expected)
        for length in (0, 1, 15, 17, 31, 33):
            with self.assertRaises(ValueError):
                m.decode_rows(bytes(length), 16)
        with self.assertRaises(ValueError):
            m.decode_rows(bytes(32), 15)

    def test_source_gates_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'source'
            source.write_bytes(b'abc')
            self.assertEqual(m.read_source(source, 3, m.sha(b'abc')), b'abc')
            for size, digest in [(2,m.sha(b'abc')), (3,'0'*64)]:
                with self.assertRaises(ValueError):
                    m.read_source(source,size,digest)
            (root/'link').symlink_to(source)
            (root/'parent-link').symlink_to(root, target_is_directory=True)
            for path in [root/'link',root/'parent-link/source',root/'missing',root]:
                with self.assertRaises((ValueError,OSError)):
                    m.read_source(path,3,m.sha(b'abc'))
            with self.assertRaises(ValueError):
                m.read_source(str(root/'x/../source'),3,m.sha(b'abc'))
            fifo=root/'fifo';os.mkfifo(fifo)
            with self.assertRaises(ValueError):
                m.read_source(fifo,0,m.sha(b''))
        with self.assertRaises(ValueError):
            m.decode(b'',b'')

    def test_output_refuses_all_conflicts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); existing=root/'existing';existing.mkdir()
            (existing/'keep').write_bytes(b'unchanged')
            (root/'file').write_bytes(b'also unchanged')
            (root/'link').symlink_to(existing,target_is_directory=True)
            (root/'dangling').symlink_to(root/'absent')
            (root/'ancestor').symlink_to(root,target_is_directory=True)
            for p in [existing,root/'file',root/'link',root/'dangling',root/'ancestor/new',root/'missing/new']:
                with self.assertRaises((ValueError,OSError)):
                    m.write_new_directory(p, {'a':b'a','b':b'b'})
            with self.assertRaises(ValueError):
                m.write_new_directory(str(root/'existing/../new'), {'a':b'a'})
            for name in ['../escape','a/b','.','..']:
                with self.assertRaises(ValueError):
                    m.write_new_directory(root/'new', {name:b'a'})
            self.assertFalse((root/'new').exists())
            self.assertFalse((root/'escape').exists())
            self.assertEqual((existing/'keep').read_bytes(),b'unchanged')
            self.assertEqual((root/'file').read_bytes(),b'also unchanged')
            m.write_new_directory(root/'success',{'a':b'a','b':b'b'})
            self.assertEqual(sorted(p.name for p in (root/'success').iterdir()),['a','b'])

    def test_output_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calls=0;real=os.write
            def fail_second(fd,data):
                nonlocal calls
                calls+=1
                if calls==2:raise OSError('simulated write failure')
                return real(fd,data)
            with mock.patch.object(m.os,'write',side_effect=fail_second):
                with self.assertRaises(OSError):
                    m.write_new_directory(root/'out',{'a':b'a','b':b'b'})
            self.assertEqual(list(root.iterdir()),[])

    def test_bdf_convention(self):
        glyphs={65:dict(width=8,height=16,rows=[128]+[0]*15),0x4e00:dict(width=16,height=16,rows=[32768]+[0]*15)}
        text=m.bdf_bytes(glyphs).decode()
        self.assertIn('SIZE 16 75 75\n',text)
        self.assertIn('SWIDTH 480 0\nDWIDTH 8 0\nBBX 8 16 0 0',text)
        self.assertIn('SWIDTH 960 0\nDWIDTH 16 0\nBBX 16 16 0 0',text)
        self.assertIn('CHARS 2\n',text)

    def test_public_specimen(self):
        blob=(R/'assets/specimens/samsung_r208_16.png').read_bytes()
        self.assertEqual(m.sha(blob),PNG_SHA256)
        self.assertEqual(struct.unpack_from('>II',blob,16),(224,44))
        report=json.loads((R/'data/samsung-r208-report.json').read_text())
        self.assertEqual((report['supportedNonblankHan'],report['gb2312Han'],report['exportedGlyphs']),(15645,6763,15742))
        self.assertEqual(report['specimen']['sha256'],PNG_SHA256)
        self.assertEqual((report['specimen']['width'],report['specimen']['asciiWidth']),(224,216))


@unittest.skipUnless(os.environ.get('SAMSUNG_R208_AXF') and os.environ.get('SAMSUNG_R208_OGM'), 'Private exact source pair not supplied')
class SourceIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.axf=m.read_source(os.environ['SAMSUNG_R208_AXF'],m.AXF_SIZE,m.AXF_SHA256)
        cls.ogm=m.read_source(os.environ['SAMSUNG_R208_OGM'],m.OGM_SIZE,m.OGM_SHA256)
        cls.gs=m.decode(cls.axf,cls.ogm)

    def test_all_coverage_and_fixed_png(self):
        self.assertEqual(len(self.gs),15742)
        self.assertNotIn(0x9fa6,self.gs)
        self.assertTrue(m.gb2312_han()<=self.gs.keys())
        self.assertEqual(self.gs[0xff0c],self.gs[0x2c])
        self.assertEqual(self.gs[0xff0c]['width'],8)
        self.assertEqual(m.sha(m.png_bytes(*m.specimen_pixels(self.gs))),PNG_SHA256)
        for i in [0,0x4e6c,len(self.axf)-1]:
            corrupt=bytearray(self.axf);corrupt[i]^=1
            with self.assertRaises(ValueError):m.decode(corrupt,self.ogm)
        for i in [0,m.HAN_INDEX,m.HAN_BITMAP,len(self.ogm)-1]:
            corrupt=bytearray(self.ogm);corrupt[i]^=1
            with self.assertRaises(ValueError):m.decode(self.axf,corrupt)

    def test_cli_success_and_no_partial_bad_source(self):
        script=R/'scripts/samsung_r208_bitmap_export.py'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            bad=root/'bad.axf';bad.write_bytes(self.axf[:-1])
            for source in [bad,root/'missing']:
                p=subprocess.run([sys.executable,str(script),str(source),os.environ['SAMSUNG_R208_OGM'],'--output',str(root/'failed')],capture_output=True)
                self.assertNotEqual(p.returncode,0);self.assertFalse((root/'failed').exists())
            # Complete BDF remains in a private TemporaryDirectory and is removed.
            p=subprocess.run([sys.executable,str(script),os.environ['SAMSUNG_R208_AXF'],os.environ['SAMSUNG_R208_OGM'],'--output',str(root/'good'),'--export-bdf'],capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual({x.name for x in (root/'good').iterdir()},{m.PNG_NAME,m.REPORT_NAME,m.BDF_NAME})
            self.assertEqual(m.sha((root/'good'/m.PNG_NAME).read_bytes()),PNG_SHA256)
            before={p.name:p.read_bytes()for p in (root/'good').iterdir()}
            p=subprocess.run([sys.executable,str(script),os.environ['SAMSUNG_R208_AXF'],os.environ['SAMSUNG_R208_OGM'],'--output',str(root/'good')],capture_output=True)
            self.assertNotEqual(p.returncode,0)
            self.assertEqual(before,{p.name:p.read_bytes()for p in (root/'good').iterdir()})


if __name__=='__main__':unittest.main(verbosity=2)
