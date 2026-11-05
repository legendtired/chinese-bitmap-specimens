#!/usr/bin/env python3
"""Source-free tests; optional private integration via IBM_FTCOMP_ARCHIVE."""
import contextlib
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'ibm_ftcomp_unpack.py'
spec = importlib.util.spec_from_file_location('ibm_ftcomp_unpack', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

@contextlib.contextmanager
def scratch():
    with tempfile.TemporaryDirectory() as directory:
        old = Path.cwd()
        os.chdir(directory)
        try:
            yield Path(directory)
        finally:
            os.chdir(old)

class UnpackTests(unittest.TestCase):
    def test_help(self):
        p = subprocess.run([sys.executable, str(SCRIPT), '--help'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn('--archive', p.stdout)
        self.assertIn('--output', p.stdout)

    def test_tables(self):
        self.assertEqual([len(x) for x in m.load_tables()], [433, 433, 433, 129, 4986])

    def test_integer_bounds(self):
        for fn, data, pos in [(m.u16, b'\0', 0), (m.u16, b'\0\0', -1), (m.u32, b'\0'*3, 0)]:
            with self.assertRaises(ValueError): fn(data, pos)

    def test_bit_bounds(self):
        self.assertEqual(m.Bits(b'\xa0', 0).get(3), 5)
        for n in [-1, 9]:
            with self.assertRaises(ValueError): m.Bits(b'\0', 0).get(n)

    def test_empty_tree(self):
        with self.assertRaises(ValueError): m.tree([0]*433)

    def test_stage1_raw(self):
        self.assertEqual(m.Decoder().stage1(b'\xff\xff\x03\0abc', 0), (b'abc', 7))
        with self.assertRaises(ValueError): m.Decoder().stage1(b'\xff\xff\x03\0ab', 0)

    def test_stage1_short_header(self):
        with self.assertRaises(ValueError): m.Decoder().stage1(b'\x01\0', 0)

    def test_stage2_literal(self):
        self.assertEqual(m.Decoder().stage2(b'\x04\0\0abc'), b'abc')
        self.assertEqual(m.Decoder().stage2(b'\x03\0\x01\x9e\xff'), b'\x9e')

    def test_stage2_truncated(self):
        for data in [b'\x04\0\0ab', b'\x02\0\x01\x9e', b'\x03\0\x01\x9e\x00', b'\x03\0\x01\x9e\x80']:
            with self.assertRaises(ValueError): m.Decoder().stage2(data)

    def test_rle_literal_and_empty(self):
        self.assertEqual(m.Decoder().rle21(b'\xffabc'), b'abc')
        with self.assertRaises(ValueError): m.Decoder().rle21(b'')

    def test_output_scope(self):
        with scratch():
            for path in ['elsewhere/new', 'local-research', 'local-research/../escape', '/etc/new']:
                with self.assertRaises(ValueError): m.output_components(path)

    def test_unknown_input_writes_nothing(self):
        with scratch() as root:
            archive = root/'FONT1'
            archive.write_bytes(b'unknown')
            with self.assertRaises(ValueError): m.extract(archive, 'local-research/result')
            self.assertFalse((root/'local-research').exists())
            archive.write_bytes(b'\0'*m.ARCHIVE_SIZE)
            with self.assertRaises(ValueError): m.extract(archive, 'local-research/result')
            self.assertFalse((root/'local-research').exists())

    def test_symlink_archive_rejected(self):
        with scratch() as root:
            (root/'data').write_bytes(b'x')
            (root/'FONT1').symlink_to(root/'data')
            with self.assertRaises(OSError): m.extract(root/'FONT1', 'local-research/result')

    def test_no_overwrite(self):
        with scratch():
            m.write_outputs('local-research/result', [])
            with self.assertRaises(FileExistsError): m.write_outputs('local-research/result', [])

    def test_symlink_root_rejected(self):
        with scratch() as root:
            (root/'other').mkdir()
            (root/'local-research').symlink_to(root/'other', target_is_directory=True)
            with self.assertRaises(OSError): m.write_outputs('local-research/result', [])
            self.assertFalse((root/'other/result').exists())

    def test_symlink_parent_rejected(self):
        with scratch() as root:
            (root/'local-research').mkdir()
            (root/'other').mkdir()
            (root/'local-research/link').symlink_to(root/'other', target_is_directory=True)
            with self.assertRaises(OSError): m.write_outputs('local-research/link/result', [])
            self.assertFalse((root/'other/result').exists())

    def test_symlink_destination_rejected(self):
        with scratch() as root:
            (root/'local-research').mkdir()
            (root/'other').mkdir()
            (root/'local-research/result').symlink_to(root/'other', target_is_directory=True)
            with self.assertRaises(FileExistsError): m.write_outputs('local-research/result', [])

    def test_preflight_precedes_writes(self):
        with scratch() as root:
            archive=root/'FONT1'
            archive.write_bytes(b'\0'*m.ARCHIVE_SIZE)
            with patch.object(m, 'parse_archive', side_effect=ValueError('member hash mismatch')):
                with self.assertRaises(ValueError): m.extract(archive, 'local-research/result')
            self.assertFalse((root/'local-research').exists())

    @unittest.skipUnless(os.environ.get('IBM_FTCOMP_ARCHIVE'), 'private FONT1 not supplied')
    def test_private_known_archive(self):
        archive = Path(os.environ['IBM_FTCOMP_ARCHIVE']).resolve()
        with scratch() as root:
            entries = m.extract(archive, 'local-research/result')
            self.assertEqual(len(entries), 5)
            for name, size, digest in m.EXPECTED:
                data=(root/'local-research/result'/name).read_bytes()
                self.assertEqual(len(data), size)
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)


def synthetic_disk():
    data = bytearray(7*512)
    struct.pack_into('<HBHBHHBH', data, 11, 512, 1, 1, 1, 16, 7, 0xf0, 1)
    data[510:512] = b'\x55\xaa'
    data[1024:1035] = b'FONT1      '
    struct.pack_into('<H', data, 1024+26, 2)
    struct.pack_into('<I', data, 1024+28, 600)
    fat_set(data, 2, 3)
    fat_set(data, 3, 0xfff)
    data[1536:2048] = b'A'*512
    data[2048:2560] = b'B'*512
    return data


def fat_set(data, cluster, value):
    off = 512+cluster*3//2
    old = int.from_bytes(data[off:off+2], 'little')
    new = (old & 0xf) | (value << 4) if cluster & 1 else (old & 0xf000) | value
    data[off:off+2] = new.to_bytes(2, 'little')


class Fat12Tests(unittest.TestCase):
    def test_synthetic_chain(self):
        self.assertEqual(m.read_fat12_font1(synthetic_disk()), b'A'*512+b'B'*88)

    def test_short_or_bad_geometry(self):
        for data in [b'', synthetic_disk()[:-1]]:
            with self.assertRaises(ValueError): m.read_fat12_font1(data)
        for offset, value in [(13, 0), (16, 0)]:
            data=synthetic_disk(); data[offset]=value
            with self.assertRaises(ValueError): m.read_fat12_font1(data)

    def test_chain_loop(self):
        data=synthetic_disk(); fat_set(data, 2, 2)
        with self.assertRaisesRegex(ValueError, 'loop'): m.read_fat12_font1(data)

    def test_bad_cluster_or_truncated_chain(self):
        for value in [0, 1, 6, 0xff0, 0xff7, 0xfff]:
            data=synthetic_disk(); fat_set(data, 2, value)
            with self.assertRaises(ValueError): m.read_fat12_font1(data)

    def test_extra_chain(self):
        data=synthetic_disk(); fat_set(data, 3, 4)
        with self.assertRaises(ValueError): m.read_fat12_font1(data)

    def test_duplicate_and_missing_font1(self):
        data=synthetic_disk(); data[1024:1035]=b'OTHER      '
        with self.assertRaises(ValueError): m.read_fat12_font1(data)
        data=synthetic_disk(); data[1056:1088]=data[1024:1056]
        with self.assertRaises(ValueError): m.read_fat12_font1(data)

    def test_disk_allowlist_and_no_write(self):
        for data in [synthetic_disk(), b'\0'*m.DISK_SIZE]:
            with self.assertRaises(ValueError): m.font1_from_disk(data)
        with scratch() as root:
            disk=root/'Disk03.xdf'; disk.write_bytes(b'\0'*m.DISK_SIZE)
            with self.assertRaises(ValueError): m.extract(disk, 'local-research/result', disk=True)
            self.assertFalse((root/'local-research').exists())

    def test_cli_input_exclusive(self):
        p=subprocess.run([sys.executable, str(SCRIPT), '--archive', 'a', '--disk', 'd',
                          '--output', 'local-research/result'], capture_output=True)
        self.assertEqual(p.returncode, 2)

    @unittest.skipUnless(os.environ.get('IBM_FTCOMP_DISK'), 'private Disk03.xdf not supplied')
    def test_private_known_disk(self):
        disk=Path(os.environ['IBM_FTCOMP_DISK']).resolve()
        with scratch() as root:
            entries=m.extract(disk, 'local-research/result', disk=True)
            self.assertEqual(len(entries), 5)
            for name, size, digest in m.EXPECTED:
                data=(root/'local-research/result'/name).read_bytes()
                self.assertEqual(len(data), size)
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)

if __name__ == '__main__': unittest.main()
