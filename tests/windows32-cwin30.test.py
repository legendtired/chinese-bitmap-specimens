#!/usr/bin/env python3
"""No font data embedded. Optional full-source audit: WINDOWS32_SOURCE=DISK6.img."""
import hashlib,importlib.util,json,os,struct,tempfile,unittest,zlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('w32',R/'scripts/windows32_bitmap_export.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
GOLD={13:'19d238a771141c971fc81264093e63e199dddaaebefaa86ca79b5dd5510c6de4',20:'73ff1c50efaef100f781d6bb2db796f726fee2dd7ddb7a76396acad6cdfb4ef1'}
def unpack_png(b):
    assert b[:8]==b'\x89PNG\r\n\x1a\n';p=8;compressed=b'';meta=None
    while p<len(b):
        n=struct.unpack_from('>I',b,p)[0];tag=b[p+4:p+8];data=b[p+8:p+8+n]
        if tag==b'IHDR':meta=struct.unpack('>IIBBBBB',data)
        if tag==b'IDAT':compressed+=data
        p+=n+12
    return meta,zlib.decompress(compressed)
def read_bdf(s):
    result={};cp=None;w=h=0;rows=[];inside=False
    for line in s.splitlines():
        if line.startswith('ENCODING '):cp=int(line.split()[1])
        elif line.startswith('BBX '):w,h=map(int,line.split()[1:3])
        elif line=='BITMAP':rows=[];inside=True
        elif line=='ENDCHAR':result[cp]={'width':w,'height':h,'rows':rows};inside=False
        elif inside:rows.append(int(line,16)>>(((w+7)//8)*8-w))
    return result
class Core(unittest.TestCase):
    def test_inverse_rows_and_padding(self):
        # Synthetic 5x3: 10001 / 01010 / 00100. Last3 stored bits are padding.
        raw=bytes([0b01110111,0b10101111,0b11011111])
        self.assertEqual(m.decode_rows(raw,0,3,3,5),dict(width=5,height=3,rows=[17,10,4]))
    def test_extent_width_stride(self):
        for args in [(b'\0',0,0,1,1),(b'\0',0,1,1,9),(b'\0',-1,1,1,1),(b'\0',0,1,2,1),(b'\0'*3,0,2,3,1)]:
            with self.assertRaises(ValueError):m.decode_rows(*args)
    def test_hash_rejects_unknown(self):
        for n in [13,20]:
            with self.assertRaises(ValueError):m.decode(b'not an approved source',n)
        with self.assertRaises(ValueError):m.fat12_file(bytes(1474560),'SIMSUN13.FO_')
    def test_szdd_literals_and_backreference(self):
        header=b'SZDD\x88\xf0\x273An'+struct.pack('<I',6)
        self.assertEqual(m.szdd(header+b'\x07ABC\xf0\xf0',6),b'ABCABC')
        for b in [b'',header+b'\x07A',header+b'\x07ABC\xf0']:
            with self.assertRaises(ValueError):m.szdd(b,6)
    def test_bdf_synthetic_roundtrip(self):
        gs={65:dict(width=5,height=3,rows=[17,10,4])}
        self.assertEqual(read_bdf(m.bdf(gs,3)),gs)
    def test_png_synthetic_pattern(self):
        gs={65:dict(width=5,height=3,rows=[17,10,4])}
        meta,raw=unpack_png(m.png_data(gs,'A'))
        self.assertEqual(meta[:4],(5,3,8,0))
        self.assertEqual(raw,b'\0\0\xff\xff\xff\0'+b'\0\xff\0\xff\0\xff'+b'\0\xff\xff\0\xff\xff')
    def test_existing_output_rejects_all_before_write(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'second.txt').write_text('old')
            with self.assertRaises(ValueError):m.write_outputs(p,{'first.txt':b'new','second.txt':b'overwrite'})
            self.assertFalse((p/'first.txt').exists());self.assertEqual((p/'second.txt').read_text(),'old')
    def test_write_and_golden_specimens(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'new';m.write_outputs(p,{'test.txt':b'abc'});self.assertEqual((p/'test.txt').read_bytes(),b'abc')
        for n,h in GOLD.items():self.assertEqual(hashlib.sha256((R/f'assets/specimens/win32_simsun_{n}.png').read_bytes()).hexdigest(),h)
    @unittest.skipUnless(os.environ.get('WINDOWS32_SOURCE'),'Optional private source not supplied')
    def test_private_source_all_glyphs_bdf_and_exact_specimens(self):
        for n in [13,20]:
            b=m.read_source(os.environ['WINDOWS32_SOURCE'],n);gs=m.decode(b,n)
            self.assertEqual(len(gs),7540);self.assertEqual(sum(0x4e00<=c<=0x9fff for c in gs),6763)
            self.assertEqual(read_bdf(m.bdf(gs,n)),gs)
            self.assertEqual(hashlib.sha256(m.catalog_png(gs,n)).hexdigest(),GOLD[n])
            changed=bytearray(b);changed[-1]^=1
            with self.assertRaises(ValueError):m.decode(changed,n)
if __name__=='__main__':unittest.main()
