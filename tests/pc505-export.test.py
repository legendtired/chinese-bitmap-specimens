#!/usr/bin/env python3
"""Source-free tests; all safety guards and checks survive python -O."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pc505_export', ROOT/'scripts/pc505_to_bdf.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.old = Path.cwd(); self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name); os.chdir(self.root)
    def tearDown(self):
        os.chdir(self.old); self.temp.cleanup()
    def rejected(self, fun, *args):
        with self.assertRaises((ValueError,OSError)): fun(*args)
    def test_short_source(self): self.rejected(m.validate_source, b'bad')
    def test_oversized_source(self): self.rejected(m.validate_source, bytes(m.SOURCE_BYTES+1))
    def test_wrong_hash(self): self.rejected(m.validate_source, bytes(m.SOURCE_BYTES))
    def test_crc_guard(self):
        with patch.object(m, 'sha256', return_value=m.SOURCE_SHA256):
            self.rejected(m.validate_source, bytes(m.SOURCE_BYTES))
    def test_decode_truncation(self): self.rejected(m.recover, bytes(100))
    def test_file_short(self):
        Path('obj').write_bytes(b'bad'); self.rejected(m.load_obj, 'obj')
    def test_file_wrong_hash(self):
        with open('obj','wb') as f: f.truncate(m.SOURCE_BYTES)
        self.rejected(m.load_obj,'obj')
    def test_directory_input(self):
        Path('obj').mkdir(); self.rejected(m.load_obj,'obj')
    def test_fifo_input(self):
        os.mkfifo('fifo'); self.rejected(m.load_obj,'fifo')
    def test_input_symlink(self):
        Path('target').write_bytes(b'safe'); Path('obj').symlink_to('target')
        self.rejected(m.load_obj,'obj'); self.assertEqual(Path('target').read_bytes(),b'safe')
    def test_input_parent_symlink(self):
        Path('dir').mkdir(); Path('alias').symlink_to('dir',target_is_directory=True)
        self.rejected(m.load_obj,'alias/obj')
    def test_input_traversal(self): self.rejected(m.load_obj,'a/../obj')
    def test_unsupported_platform(self):
        with patch.object(m,'SAFE_DIR_FD',False):
            self.rejected(m.load_obj,'obj'); self.rejected(m.output_path,'local-research/out.bdf')
    def test_public_output(self): self.rejected(m.output_path,'assets/font.bdf')
    def test_output_traversal(self): self.rejected(m.output_path,'local-research/a/../out.bdf')
    def test_output_suffix(self): self.rejected(m.output_path,'local-research/out.json')
    def test_output_same_root(self): self.rejected(m.output_path,'local-research')
    def test_no_overwrite(self):
        p=Path('local-research/out.bdf'); p.parent.mkdir(); p.write_bytes(b'safe')
        self.rejected(m.write_bdf,p,b'new'); self.assertEqual(p.read_bytes(),b'safe')
    def test_output_symlink(self):
        Path('local-research').mkdir(); Path('target').write_bytes(b'safe')
        p=Path('local-research/out.bdf'); p.symlink_to(self.root/'target')
        self.rejected(m.write_bdf,p,b'new'); self.assertEqual(Path('target').read_bytes(),b'safe')
    def test_output_parent_symlink(self):
        Path('target').mkdir(); Path('local-research').symlink_to('target',target_is_directory=True)
        self.rejected(m.write_bdf,'local-research/out.bdf',b'new')
        self.assertEqual(list(Path('target').iterdir()),[])
    def test_output_leaf_race(self):
        Path('local-research').mkdir(); Path('target').write_bytes(b'safe'); old=m.output_path
        def race(path):
            p=old(path); p.symlink_to(self.root/'target'); return p
        with patch.object(m,'output_path',side_effect=race): self.rejected(m.write_bdf,'local-research/out.bdf',b'new')
        self.assertEqual(Path('target').read_bytes(),b'safe')
    def test_output_parent_race(self):
        Path('local-research/child').mkdir(parents=True); Path('target').mkdir(); old=m.output_path
        def race(path):
            p=old(path); p.parent.rmdir(); p.parent.symlink_to(self.root/'target',target_is_directory=True); return p
        with patch.object(m,'output_path',side_effect=race): self.rejected(m.write_bdf,'local-research/child/out.bdf',b'new')
        self.assertEqual(list(Path('target').iterdir()),[])
    def test_private_creation(self):
        p=Path('local-research/a/out.bdf'); m.write_bdf(p,b'test')
        self.assertEqual(p.read_bytes(),b'test'); self.assertEqual(p.stat().st_mode & 0o777,0o600)
    def test_mapping(self):
        rows=m.mapping(); self.assertEqual(len(rows),7445)
        d={code:(cp,slot) for cp,code,slot in rows}
        self.assertEqual(d[0xa1a4][0],0x30fb); self.assertEqual(d[0xa1aa][0],0x2015)
        self.assertNotIn(0xd7fa,d); self.assertEqual(d[0xf7fe][1],7598)
    def test_bdf_metrics(self):
        s=m.make_bdf({0x4e00:(14,(1,)*15),32:(8,(0,)*16)},'GB2312ASCII').decode()
        self.assertIn('SIZE 16 72 72',s); self.assertIn('FONTBOUNDINGBOX 14 16 0 0',s)
        self.assertIn('SWIDTH 875 0\nDWIDTH 14 0\nBBX 14 15 0 0',s)
        self.assertIn('SWIDTH 500 0\nDWIDTH 8 0\nBBX 8 16 0 0',s)
        self.assertIn('72-72-P-140-',s); self.assertNotIn('DEFAULT_CHAR',s)
    def test_bdf_invalid_row(self): self.rejected(m.make_bdf,{65:(8,(256,)*16)},'ASCII')
    def test_failed_export_creates_nothing(self):
        Path('obj').write_bytes(b'bad'); self.rejected(m.export,'obj','local-research/out.bdf')
        self.assertFalse(Path('local-research').exists())

if __name__=='__main__': unittest.main(verbosity=2)
