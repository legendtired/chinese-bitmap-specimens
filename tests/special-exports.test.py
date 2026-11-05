"""Synthetic tests, with no distributed third-party font data. Run with Python 3.9+."""
import importlib.util
import json
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
palm=load('cjkos_to_bdf');tumb=load('tumbled_to_bdf')
class PalmTests(unittest.TestCase):
    def test_pixels_10(self):
        for y in range(10):
            for x in range(10):
                data=bytearray(13)
                if x<8:data[y]=1<<(7-x)
                else:data[10+y//4]=1<<(7-2*(y%4)-(x-8))
                out=palm.decode_pixels(data,10)
                self.assertEqual(sum(map(sum,out)),1);self.assertEqual(out[y][x],1)
    def test_pixels_12(self):
        for y in range(12):
            for x in range(12):
                data=bytearray(18);data[(y*12+x)//8]=1<<(7-(y*12+x)%8)
                out=palm.decode_pixels(data,12)
                self.assertEqual(sum(map(sum,out)),1);self.assertEqual(out[y][x],1)
    def test_source_ranges(self):
        gb=palm.source_codes('gb2312');b5=palm.source_codes('big5')
        self.assertEqual((len(gb),gb[0],gb[-1]),(8178,0xa1a1,0xf7fe))
        self.assertEqual((len(b5),b5[0],b5[62],b5[63],b5[-1]),(13973,0xa140,0xa17e,0xa1a1,0xf9fe))
    def test_no_silent_unmapped_loss(self):
        gs=[dict(source_code=0xa140,codepoint=0x3000,canonical=True,pixels=((0,)*10,)*10),
            dict(source_code=0xa141,codepoint=None,canonical=False,pixels=((0,)*10,)*10),
            dict(source_code=0xa142,codepoint=0x3000,canonical=False,pixels=((0,)*10,)*10)]
        text,r=palm.render_bdf(gs,dict(size=10,codec='big5',source_sha256='test'))
        self.assertIn('CHARS 3',text);self.assertEqual(text.count('ENCODING -1\n'),2)
        self.assertEqual(r['encoded_glyphs'],1);self.assertEqual(r['unencoded_glyphs'],2)
        src,r=palm.render_bdf(gs,dict(size=10,codec='big5',source_sha256='test'),'source')
        self.assertNotIn('ENCODING -1',src);self.assertIn('CHARSET_REGISTRY "CJKOSBIG5"',src)
    def test_unknown_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'font.PDB';p.write_bytes(b'not a verified source')
            with self.assertRaisesRegex(ValueError,'SHA-256'):palm.load_font(p)
class SafeOutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name)
        self.source=self.r/'input';self.source.write_bytes(b'input must stay unchanged')
    def tearDown(self):self.tmp.cleanup()
    def check_both(self,output,report):
        original=self.source.read_bytes()
        for module in (palm,tumb):
            with self.subTest(module=module.__name__):
                with self.assertRaises((ValueError,OSError)):
                    module.write_outputs(output,report,self.source,'BDF',{'ok':True})
                self.assertEqual(self.source.read_bytes(),original)
    def test_existing_output(self):
        output=self.r/'out';output.write_bytes(b'keep output');report=self.r/'report'
        self.check_both(output,report)
        self.assertEqual(output.read_bytes(),b'keep output');self.assertFalse(report.exists())
    def test_existing_report(self):
        output=self.r/'out';report=self.r/'report';report.write_bytes(b'keep report')
        self.check_both(output,report)
        self.assertFalse(output.exists());self.assertEqual(report.read_bytes(),b'keep report')
    def test_same_target(self):
        output=self.r/'out';self.check_both(output,output);self.assertFalse(output.exists())
    def test_resolved_alias(self):
        real=self.r/'real';real.mkdir();link=self.r/'alias';link.symlink_to(real,target_is_directory=True)
        self.check_both(real/'out',link/'out');self.assertFalse((real/'out').exists())
    def test_missing_report_parent(self):
        output=self.r/'out';self.check_both(output,self.r/'missing'/'report');self.assertFalse(output.exists())
    def test_missing_output_parent(self):
        report=self.r/'report';self.check_both(self.r/'missing'/'out',report);self.assertFalse(report.exists())
    def test_dangling_output_symlink(self):
        output=self.r/'out';output.symlink_to(self.r/'missing')
        self.check_both(output,self.r/'report');self.assertTrue(output.is_symlink());self.assertFalse((self.r/'missing').exists())
    def test_dangling_report_symlink(self):
        report=self.r/'report';report.symlink_to(self.r/'missing')
        self.check_both(self.r/'out',report);self.assertTrue(report.is_symlink());self.assertFalse((self.r/'out').exists())
    def test_input_output_collision(self):
        self.check_both(self.source,self.r/'report');self.assertFalse((self.r/'report').exists())
    def test_input_report_collision(self):
        self.check_both(self.r/'out',self.source);self.assertFalse((self.r/'out').exists())
    def test_exclusive_creation_after_race(self):
        for module in (palm,tumb):
            output=self.r/(module.__name__+'.out');report=self.r/(module.__name__+'.report')
            report.write_bytes(b'racing existing report')
            with patch.object(module,'preflight_outputs',return_value=(output,report)):
                with self.assertRaises(FileExistsError):module.write_outputs(output,report,self.source,'BDF',{})
            self.assertFalse(output.exists());self.assertEqual(report.read_bytes(),b'racing existing report')
    def test_success_and_refuse_second_write(self):
        for module in (palm,tumb):
            output=self.r/(module.__name__+'.out');report=self.r/(module.__name__+'.report')
            module.write_outputs(output,report,self.source,'BDF',{'ok':True})
            self.assertEqual(output.read_text(),'BDF');self.assertEqual(json.loads(report.read_text()),{'ok':True})
            with self.assertRaises(ValueError):module.write_outputs(output,report,self.source,'changed',{})
            self.assertEqual(output.read_text(),'BDF')
    def test_cli_preflight_keeps_input(self):
        original=self.source.read_bytes()
        for module in (palm,tumb):
            script=ROOT/'scripts'/(module.__name__+'.py')
            cases=[(self.source,self.r/'report'),(self.r/'out',self.r/'missing'/'report'),(self.r/'out',self.r/'out')]
            for output,report in cases:
                result=subprocess.run([sys.executable,str(script),str(self.source),str(output),'--report',str(report)],capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('Error:',result.stderr)
                self.assertEqual(self.source.read_bytes(),original)
        self.assertFalse((self.r/'out').exists());self.assertFalse((self.r/'report').exists())

class TumbledTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name)
        (self.r/'glyphs').mkdir();(self.r/'shapes').mkdir()
        (self.r/'font.json').write_text(json.dumps(dict(name='TUMBLED_18',height=18)))
    def tearDown(self):self.tmp.cleanup()
    def put(self,name,text):(self.r/name).write_text(text)
    def test_composition_bearings_and_overflow(self):
        self.put('shapes/a.txt','-1 -2\n# #\n ##\n');self.put('shapes/b.txt','19 1\n##')
        self.put('glyphs/35270.txt','14\n0 0 a\n1 2 b\n')
        gs,i=tumb.load_font(self.r);g=gs[0]
        self.assertEqual(g['pixels'],{(-2,-1),(0,-1),(-1,0),(0,0),(3,20),(4,20)})
        self.assertEqual((g['advance'],g['left'],g['top'],g['width'],g['height']),(14,-2,-1,7,22))
        text,r=tumb.render_bdf(gs,i)
        self.assertIn('DWIDTH 14 0\nBBX 7 22 -2 -3',text)
        self.assertEqual((r['ascent'],r['descent']),(19,3));self.assertEqual(r['multi_component_glyphs'],1)
    def test_empty_glyph_keeps_advance(self):
        self.put('glyphs/12288.txt','14\n');gs,i=tumb.load_font(self.r);text,r=tumb.render_bdf(gs,i)
        self.assertIn('DWIDTH 14 0\nBBX 0 0 0 0',text);self.assertEqual(r['empty_glyphs'],1)
    def test_missing_shape_is_error(self):
        self.put('glyphs/35270.txt','14\n0 0 missing')
        with self.assertRaises(FileNotFoundError):tumb.load_font(self.r)
    def test_variant_not_silently_replaced(self):
        self.put('glyphs/35270-jp.txt','14\n')
        with self.assertRaisesRegex(ValueError,'Variant filename'):tumb.load_font(self.r)
    def test_no_rasterized_other_sizes(self):
        self.put('font.json',json.dumps(dict(name='TUMBLED_28',height=28)))
        with self.assertRaises(ValueError):tumb.load_font(self.r)
    def test_shape_traversal_and_absolute_rejected(self):
        for name in ('../outside','../../outside','/tmp/outside'):
            self.put('glyphs/35270.txt','14\n0 0 '+name)
            with self.assertRaisesRegex(ValueError,'Unsafe shape name'):tumb.load_font(self.r)
    def test_shape_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            outside=Path(d)/'outside.txt';outside.write_text('0 0\n#')
            (self.r/'shapes'/'escape.txt').symlink_to(outside)
            self.put('glyphs/35270.txt','14\n0 0 escape')
            with self.assertRaisesRegex(ValueError,'escapes font folder'):tumb.load_font(self.r)
    def test_invalid_unicode_scalar_rejected(self):
        for cp in (55296,57343,1114112):
            p=self.r/'glyphs'/f'{cp}.txt';p.write_text('14\n')
            with self.assertRaisesRegex(ValueError,'Unicode scalar'):tumb.load_font(self.r)
            p.unlink()
if __name__=='__main__':unittest.main()
