#!/usr/bin/env python3
"""Source-free Solaris PCF tests: all fixture bitmap pixels are invented."""
from pathlib import Path
import contextlib
import importlib.util
import io
import os
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('solaris_export',ROOT/'scripts/solaris_gbk_to_bdf.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)


@contextlib.contextmanager
def cwd(path):
    prev=Path.cwd();os.chdir(path)
    try:yield
    finally:os.chdir(prev)


def fixture(big=True,msb=True,unit=1,compressed=True):
    """Encode a small invented PCF independently from the decoder."""
    fmt=2|(4 if big else 0)|(8 if msb else 0)|({1:0,2:1,4:2}[unit]<<4)
    en='>' if big else '<'
    pack=lambda f,*v:struct.pack(en+f,*v)
    head=lambda f:struct.pack('<I',f)
    props={'FONT':'invented','FOUNDRY':'test','CHARSET_REGISTRY':'gbk','CHARSET_ENCODING':'0',
           'POINT_SIZE':120,'PIXEL_SIZE':14,'RESOLUTION_X':72,'RESOLUTION_Y':72}
    strings=bytearray();records=[]
    def add(s):
        off=len(strings);strings.extend(s.encode()+b'\0');return off
    for k,v in props.items():
        no=add(k);records.append(pack('IBI',no,isinstance(v,str),add(v) if isinstance(v,str) else v))
    pr=head(fmt)+pack('I',len(props))+b''.join(records);pr+=b'\0'*(-len(pr)%4);pr+=pack('I',len(strings))+strings
    codes=[0x21,0x8140,0xa8bc]
    glyphs=[m.Glyph(8,4,-1,-1,9,750,(0x81,0x42,0x24,0x18)),
            m.Glyph(8,4,0,-1,8,1000,(0x18,0x24,0x42,0x81)),
            m.Glyph(8,4,0,-1,8,1000,(0x11,0x22,0x44,0x88))]
    metrics=[]
    for g in glyphs:
        values=(g.xoff,g.xoff+g.width,g.advance,g.height+g.yoff,-g.yoff)
        metrics.append(bytes(v+128 for v in values) if compressed else pack('5hH',*values,0))
    metfmt=fmt|(0x100 if compressed else 0)
    mt=head(metfmt)+pack('H' if compressed else 'I',len(glyphs))+b''.join(metrics)
    payload=bytearray();offsets=[]
    for g in glyphs:
        offsets.append(len(payload))
        for row in g.rows:
            raw=(row<<24).to_bytes(4,'big')
            if not msb:raw=bytes(int(f'{v:08b}'[::-1],2) for v in raw)
            if big!=msb and unit!=1:raw=b''.join(raw[i:i+unit][::-1] for i in range(0,4,unit))
            payload.extend(raw)
    bm=head(fmt)+pack('I',len(glyphs))+pack('3I',*offsets)+pack('4I',12,24,len(payload),96)+payload
    lo,hi,lb,hb=0x21,0xbc,0,0xa8
    ix=[65535]*((hi-lo+1)*(hb-lb+1))
    for j,c in enumerate(codes):ix[((c>>8)-lb)*(hi-lo+1)+(c&255)-lo]=j
    enc=head(fmt)+pack('5H',lo,hi,lb,hb,0xffff)+pack(str(len(ix))+'H',*ix)
    sw=head(fmt)+pack('I',len(glyphs))+pack('3i',*(g.swidth for g in glyphs))
    acc=head(fmt)+b'\0'*8+pack('3i',6,2,0)
    table_data=[(1,fmt,pr),(2,fmt,acc),(4,metfmt,mt),(8,fmt,bm),(32,fmt,enc),(64,fmt,sw),(256,fmt,acc)]
    off=8+16*len(table_data);desc=[];body=bytearray()
    for kind,f,data in table_data:
        desc.append(struct.pack('<4I',kind,f,len(data),off));body.extend(data);pad=-len(data)%4;body.extend(b'\0'*pad);off+=len(data)+pad
    return b'\1fcp'+struct.pack('<I',len(table_data))+b''.join(desc)+body,dict(zip(codes,glyphs))


def table_offset(data,kind):
    for i in range(struct.unpack_from('<I',data,4)[0]):
        row=struct.unpack_from('<4I',data,8+16*i)
        if row[0]==kind:return row[3]
    raise KeyError(kind)


class DecoderTests(unittest.TestCase):
    def test_all_bit_byte_orders_scan_units_and_metrics(self):
        for big in (False,True):
            for msb in (False,True):
                for unit in (1,2,4):
                    for compressed in (False,True):
                        with self.subTest(big=big,msb=msb,unit=unit,compressed=compressed):
                            raw,wanted=fixture(big,msb,unit,compressed);props,got,asc,desc=m.decode_pcf(raw)
                            self.assertEqual(got,wanted);self.assertEqual((asc,desc),(6,2));self.assertEqual(props['FONT'],'invented')
    def test_known_mapping_and_unresolved_code(self):
        data,wanted=fixture();mapping,unknown=m.map_gbk(wanted)
        self.assertEqual(mapping,{0x21:0x21,0x8140:0x4e02});self.assertEqual(unknown,[0xa8bc]);self.assertNotIn(0x20,mapping)
    def test_bdf_modes_metrics_swidth_and_no_space(self):
        data,wanted=fixture();p,g,a,d=m.decode_pcf(data);mapping,unknown=m.map_gbk(g)
        for mode,num in [('unicode',2),('native-gbk',3)]:
            text=m.make_bdf(p,g,a,d,mapping,mode).decode()
            self.assertIn(f'CHARS {num}\n',text);self.assertIn('FONT_ASCENT 6\n',text);self.assertIn('FONT_DESCENT 2\n',text)
            self.assertIn('BBX 8 4 -1 -1\n',text);self.assertIn('SWIDTH 750 0\n',text);self.assertNotIn('\nENCODING 32\n',text)
            self.assertEqual(text.count('STARTCHAR '),num)
            self.assertEqual('ENCODING 19970\n' in text,mode=='unicode')
            self.assertEqual('ENCODING 43196\n' in text,mode=='native-gbk')
    def test_short_files(self):
        raw,_=fixture()
        for length in [0,3,7,15,100,len(raw)-20]:
            with self.subTest(length=length),self.assertRaises(ValueError):m.decode_pcf(raw[:length])
    def test_magic_count_duplicate_and_bad_offset(self):
        raw,_=fixture()
        changes=[(0,b'BAD!'),(4,struct.pack('<I',99)),(24,struct.pack('<I',1)),(20,struct.pack('<I',1))]
        for off,value in changes:
            bad=bytearray(raw);bad[off:off+len(value)]=value
            with self.assertRaises(ValueError):m.decode_pcf(bad)
    def test_properties_out_of_bounds_and_control_injection(self):
        raw,_=fixture();off=table_offset(raw,1)
        bad=bytearray(raw);struct.pack_into('>I',bad,off+8,0xffffffff)
        with self.assertRaises(ValueError):m.decode_pcf(bad)
        bad=raw.replace(b'invented\0',b'inven\ned\0')
        with self.assertRaises(ValueError):m.decode_pcf(bad)
    def test_bad_bitmap_offset_and_encoding_index(self):
        raw,_=fixture()
        for kind,delta,value,fmt in [(8,8,0xffffffff,'>I'),(32,14,60000,'>H')]:
            bad=bytearray(raw);struct.pack_into(fmt,bad,table_offset(raw,kind)+delta,value)
            with self.assertRaises(ValueError):m.decode_pcf(bad)
    def test_bad_dimensions_and_accelerator_mismatch(self):
        raw,_=fixture();bad=bytearray(raw);off=table_offset(raw,4);bad[off+6]=255;bad[off+7]=0
        with self.assertRaises(ValueError):m.decode_pcf(bad)
        bad=bytearray(raw);struct.pack_into('>i',bad,table_offset(raw,256)+12,7)
        with self.assertRaises(ValueError):m.decode_pcf(bad)
    def test_missing_swidth_and_format_mismatch(self):
        raw,_=fixture();bad=bytearray(raw)
        for i in range(7):
            if struct.unpack_from('<I',bad,8+16*i)[0]==64:struct.pack_into('<I',bad,8+16*i,512)
        with self.assertRaises(ValueError):m.decode_pcf(bad)
        bad=bytearray(raw);struct.pack_into('<I',bad,table_offset(raw,8),0)
        with self.assertRaises(ValueError):m.decode_pcf(bad)
    def test_validation_rejects_invented_data(self):
        p,g,a,d=m.decode_pcf(fixture()[0])
        with self.assertRaises(ValueError):m.validate_font(p,g,a,d,next(iter(m.SOURCES.values())))
    def test_no_force_option(self):
        err=io.StringIO()
        with contextlib.redirect_stderr(err),self.assertRaises(SystemExit) as result:
            m.main(['--font','source.pcf','--output','local-research/out.bdf','--force'])
        self.assertEqual(result.exception.code,2)
        self.assertIn('unrecognized arguments: --force',err.getvalue())


@unittest.skipUnless(m.SAFE_DIR_FD,'POSIX safe file APIs unavailable')
class FileSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_wrong_size_hash_and_compressed(self):
        p=self.path/'input.pcf';p.write_bytes(b'wrong')
        with self.assertRaises(ValueError):m.load_font(p)
        p.write_bytes(b'X'*1696464)
        with self.assertRaisesRegex(ValueError,'SHA-256'):m.load_font(p)
        z=self.path/'input.pcf.Z';z.write_bytes(b'Z')
        with self.assertRaisesRegex(ValueError,'uncompress'):m.load_font(z)
    def test_input_symlink_parent_symlink_fifo_and_directory(self):
        p=self.path/'real';p.write_bytes(b'not-font');link=self.path/'link';link.symlink_to(p)
        with self.assertRaises((OSError,ValueError)):m.load_font(link)
        d=self.path/'d';d.mkdir();(d/'f').write_bytes(b'x');ld=self.path/'linked-dir';ld.symlink_to(d,target_is_directory=True)
        with self.assertRaises((OSError,ValueError)):m.load_font(ld/'f')
        fifo=self.path/'pipe';os.mkfifo(fifo)
        with self.assertRaises((OSError,ValueError)):m.load_font(fifo)
        with self.assertRaises((OSError,ValueError)):m.load_font(d)
    def test_output_new_private_file_and_never_overwrites(self):
        with cwd(self.path):
            p=Path('local-research/sub/out.bdf');m.write_bdf(p,b'first')
            self.assertEqual(p.read_bytes(),b'first');self.assertEqual(p.stat().st_mode&0o777,0o600)
            with self.assertRaises(ValueError):m.write_bdf(p,b'second')
            self.assertEqual(p.read_bytes(),b'first')
    def test_output_outside_traversal_and_wrong_suffix(self):
        with cwd(self.path):
            for p in ['out.bdf','local-research/../escape.bdf','local-research/x.json','local-research']:
                with self.subTest(p=p),self.assertRaises(ValueError):m.write_bdf(p,b'x')
            self.assertFalse(Path('local-research').exists())
    def test_output_links_fifo_and_input_failure_leave_no_output(self):
        with cwd(self.path):
            Path('local-research').mkdir();Path('outside').mkdir();Path('local-research/link').symlink_to(self.path/'outside',target_is_directory=True)
            with self.assertRaises((OSError,ValueError)):m.write_bdf('local-research/link/out.bdf',b'x')
            Path('local-research/dangling.bdf').symlink_to(self.path/'missing')
            with self.assertRaises((OSError,ValueError)):m.write_bdf('local-research/dangling.bdf',b'x')
            os.mkfifo('local-research/fifo.bdf')
            with self.assertRaises((OSError,ValueError)):m.write_bdf('local-research/fifo.bdf',b'x')
            with self.assertRaises((OSError,ValueError)):m.export('missing.pcf','local-research/no.bdf')
            self.assertFalse(Path('local-research/no.bdf').exists())
    def test_write_failure_does_not_delete_replacement(self):
        # A concurrent writer can replace a pathname, but must not have its new
        # file removed by failure cleanup in this exporter.
        with cwd(self.path):
            real_fdopen=m.os.fdopen
            class BrokenWriter:
                def __init__(self,fd):self.handle=real_fdopen(fd,'wb')
                def __enter__(self):return self
                def __exit__(self,*args):self.handle.close()
                def write(self,data):
                    p=Path('local-research/out.bdf');p.unlink();p.write_bytes(b'concurrent file')
                    raise OSError('simulated disk error')
            with patch.object(m.os,'fdopen',side_effect=lambda fd,mode:BrokenWriter(fd)):
                with self.assertRaises(OSError):m.write_bdf('local-research/out.bdf',b'font')
            self.assertEqual(Path('local-research/out.bdf').read_bytes(),b'concurrent file')

    def test_symlink_race_after_preflight(self):
        with cwd(self.path):
            Path('local-research').mkdir();Path('outside').mkdir()
            original=m.output_path
            def raced(path):
                result=original(path)
                Path('local-research/sub').symlink_to(self.path/'outside',target_is_directory=True)
                return result
            with patch.object(m,'output_path',side_effect=raced):
                with self.assertRaises(OSError):m.write_bdf('local-research/sub/out.bdf',b'x')
            self.assertFalse(Path('outside/out.bdf').exists())


if __name__=='__main__':unittest.main()
