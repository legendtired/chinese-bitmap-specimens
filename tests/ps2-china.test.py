#!/usr/bin/env python3
"""No font data embedded. PS2_ROM2 optionally enables complete private-source checks."""
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
R = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ps2', R/'scripts/ps2_china_bitmap_export.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
GOLD = 'a3ce9e56eaf3409eff7bf3c678874b43840f52d726a8179811aaf859e5f27533'

def unpack_png(data):
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    p = 8; compressed = b''; meta = None
    while p < len(data):
        n = struct.unpack_from('>I', data, p)[0]
        tag = data[p+4:p+8]; chunk = data[p+8:p+8+n]
        if tag == b'IHDR': meta = struct.unpack('>IIBBBBB', chunk)
        if tag == b'IDAT': compressed += chunk
        p += 12+n
    return meta, zlib.decompress(compressed)

def bdf_rows(text):
    result = {}; cp = None; rows = []; inside = False
    for line in text.splitlines():
        if line.startswith('ENCODING '): cp = int(line.split()[1])
        elif line == 'BITMAP': rows = []; inside = True
        elif line == 'ENDCHAR': result[cp] = tuple(rows); inside = False
        elif inside: rows.append(int(line,16))
    return result

class Core(unittest.TestCase):
    def test_bit_order_without_source(self):
        raw = bytes((0x80,0,1)) + bytes((0,1,0)) + bytes(66)
        rows = m.decode_rows(raw)
        self.assertEqual(rows, (0x800001,0x100)+(0,)*22)
        for bad in (b'', bytes(71), bytes(73)):
            with self.assertRaises(ValueError): m.decode_rows(bad)

    def test_mapping_boundaries(self):
        for a,b,index in [(0xa1,0xa1,0),(0xa9,0xfe,845),(0xb0,0xa1,846),(0xf7,0xfe,7613),
                          (0x81,0x40,7614),(0x81,0x7e,7676),(0x81,0x80,7677),(0xa0,0xfe,13693),
                          (0xaa,0x40,13694),(0xfe,0xa0,21853)]:
            self.assertEqual(m.slot_index(a,b),index)
        for a,b in [(0x81,0x7f),(0xa8,0x40),(0xa9,0x80),(0xaa,0xa1),(0x80,0x40),(0xff,0x40)]:
            self.assertIsNone(m.slot_index(a,b))

    def test_repertoire_counts_and_two_symbol_differences(self):
        gb = m.mapping('gb2312'); gk = m.mapping('gbk')
        self.assertEqual(len(gb),7445); self.assertEqual(len(gk),21638)
        self.assertEqual(sum(0x4e00<=c<=0x9fff for c in gb),6763)
        self.assertEqual(set(range(0x4e00,0x9fa6)),{c for c in gk if 0x4e00<=c<=0x9fff})
        self.assertEqual(gb[0x30fb],gk[0xb7]); self.assertEqual(gb[0x2015],gk[0x2014])
        with self.assertRaises(ValueError): m.mapping('gb18030')

    def test_romdir_synthetic_and_bounds(self):
        raw = bytearray(m.ROM_SIZE)
        records = [('RESET',8,0),('ROMDIR',84,96),('EXTINFO',0,108),('FNTHANCH',8,6912),('GB18030',8,2058552)]
        for i,(name,ext,size) in enumerate(records):
            struct.pack_into('<10sHI',raw,i*16,name.encode(),ext,size)
        self.assertEqual(m.romdir(raw)['FNTHANCH'],(0xd0,6912))
        self.assertEqual(m.romdir(raw)['GB18030'],(0x1bd0,2058552))
        struct.pack_into('<I',raw,0x4c,m.ROM_SIZE)
        with self.assertRaises(ValueError): m.romdir(raw)

    def test_wrong_source_rejected(self):
        for data in (b'', bytes(524288), bytes(m.ROM_SIZE)):
            with self.assertRaises(ValueError): m.validate_source(data)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'wrong.ROM2';p.write_bytes(bytes(524288))
            with self.assertRaises(ValueError): m.read_source(p)

    def test_png_synthetic_pixels(self):
        gs={65:(0x800001,)+(0,)*23}
        meta,raw=unpack_png(m.png_data(gs,['A']))
        self.assertEqual(meta[:4],(24,24,8,6));self.assertEqual(raw[0],0)
        self.assertEqual(raw[1:5],b'\0\0\0\xff');self.assertEqual(raw[5:9],b'\xff'*4)
        self.assertEqual(raw[1+23*4:1+24*4],b'\0\0\0\xff')
        with self.assertRaises(ValueError): m.png_data(gs,['B'])

    def test_bdf_synthetic_roundtrip_and_explicit_layout(self):
        gs={65:(0x800001,)+(0,)*23,32:(0,)*24}
        text=m.bdf(gs);self.assertEqual(bdf_rows(text),gs)
        self.assertIn('STORAGE-CELL CONVENTION ONLY',text);self.assertIn('SWIDTH 960 0',text)
        self.assertIn('runtime advance and baseline are unverified',text)

    def test_output_collision_rejects_before_writing(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'second.txt').write_text('old')
            with self.assertRaises(ValueError): m.write_outputs(p,{'first.txt':b'new','second.txt':b'new'})
            self.assertFalse((p/'first.txt').exists());self.assertEqual((p/'second.txt').read_text(),'old')
            with self.assertRaises(ValueError): m.write_outputs(p,{'../outside':b'x'})

    def test_symlink_input_and_output_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'target').mkdir();(p/'link').symlink_to(p/'target',target_is_directory=True)
            with self.assertRaises(ValueError): m.write_outputs(p/'link',{'x':b'x'})
            with self.assertRaises(ValueError): m.read_source(p/'link'/'x')

    def test_public_specimen_hash_and_dimensions(self):
        b=(R/'assets/specimens/ps2_scph50009_24.png').read_bytes()
        self.assertEqual(hashlib.sha256(b).hexdigest(),GOLD)
        meta,_=unpack_png(b);self.assertEqual(meta[:2],(674,52))

    @unittest.skipUnless(os.environ.get('PS2_ROM2'),'Optional private source not supplied')
    def test_private_source_and_all_mapped_bdf_roundtrip(self):
        data=m.read_source(os.environ['PS2_ROM2'])
        for rep,count in [('gbk',21733),('gb2312',7540)]:
            gs=m.decode(data,rep);self.assertEqual(len(gs),count)
            self.assertEqual(bdf_rows(m.bdf(gs)),gs)
            self.assertEqual(hashlib.sha256(m.png_data(gs,[m.PHRASE,m.ASCII],gap=1)).hexdigest(),GOLD)
            self.assertEqual(gs[32],(0,)*24)
            self.assertTrue(all(row & 0xfff == 0 for cp in range(32,127) for row in gs[cp]))
        bad=bytearray(data);bad[0xd0+72]^=1
        with self.assertRaises(ValueError):m.decode(bad)

if __name__=='__main__': unittest.main()
