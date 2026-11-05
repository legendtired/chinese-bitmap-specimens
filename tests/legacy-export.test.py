#!/usr/bin/env python3
"""Source-free regression tests. Synthetic fixtures contain no real font glyphs.

Optional real inputs: LEGACY_EXPORT_CNS40_HBF and LEGACY_EXPORT_DEC_ISO.
Run directly with Python 3; no third-party packages or network are required.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts' if (ROOT / 'scripts').is_dir() else ROOT


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cns = load('cns40_hbf_to_bdf')
dec = load('extract_dec_font_subsets')
SHA = lambda data: hashlib.sha256(data).hexdigest()
RANGES = (
    (0x2121, 0x234E, '4040w0.bin', 0),
    (0x2421, 0x2570, '4040w0.bin', 46800),
    (0x2621, 0x263E, '4040w0.bin', 81600),
    (0x2721, 0x2939, '4040w0.bin', 87600),
    (0x4221, 0x4241, '4040w0.bin', 130200),
    (0x4421, 0x7D4B, '4040w1.bin', 0),
)


def synthetic_hbf(folder):
    header = [
        'HBF_START_FONT 1.1', 'HBF_CODE_SCHEME CNS11643-92p1',
        'FONT SYNTHETIC', 'SIZE 40 150 150',
        'HBF_BITMAP_BOUNDING_BOX 40 40 0 -6', 'FONTBOUNDINGBOX 40 40 0 -6',
        'STARTPROPERTIES 7', 'CHARSET_REGISTRY "CNS11643.92p1"',
        'CHARSET_ENCODING "0"', 'FONT_ASCENT 34', 'FONT_DESCENT 6',
        'RESOLUTION_X 75', 'RESOLUTION_Y 75', 'DEFAULT_CHAR 0x2121',
        'ENDPROPERTIES', 'HBF_START_BYTE_2_RANGES 1',
        'HBF_BYTE_2_RANGE 0x21-0x7E', 'HBF_END_BYTE_2_RANGES',
        'HBF_START_CODE_RANGES 6',
    ]
    header += [f'HBF_CODE_RANGE 0x{a:04X}-0x{b:04X} {name} {off}'
               for a, b, name, off in RANGES]
    header += ['HBF_END_CODE_RANGES', 'HBF_END_FONT']
    data = {
        'cns40-1.hbf': ('\n'.join(header) + '\n').encode('ascii'),
        # Deterministic byte patterns, not real glyph or font content.
        '4040w0.bin': (bytes(range(200)) * 684),
        '4040w1.bin': (bytes(reversed(range(200))) * 5401),
    }
    for name, raw in data.items():
        (folder / name).write_bytes(raw)
    return folder / 'cns40-1.hbf', {name: SHA(raw) for name, raw in data.items()}


def expected_glyphs(source_dir):
    raw = {name: (source_dir / name).read_bytes() for name in ('4040w0.bin', '4040w1.bin')}
    expected = {}
    for first, last, name, offset in RANGES:
        count = 0
        for row in range(first >> 8, (last >> 8) + 1):
            for column in range(0x21, 0x7F):
                code = row * 256 + column
                if first <= code <= last:
                    expected[code] = raw[name][offset + 200*count:offset + 200*(count+1)]
                    count += 1
    return expected


def parsed_bdf(text):
    result = {}
    for block in text.split('STARTCHAR ')[1:]:
        header, body = block.split('BITMAP\n')
        values = {line.split()[0]: line.split()[1:] for line in header.splitlines()[1:]}
        code = int(values['ENCODING'][0])
        result[code] = (tuple(map(int, values['BBX'])), tuple(map(int, values['DWIDTH'])),
                        bytes.fromhex(''.join(body.split('ENDCHAR')[0].splitlines())))
    return result


def iso_record(name, extent, size, directory=False, rr_name=None):
    name = name if isinstance(name, bytes) else name.encode('ascii')
    extra = b''
    if rr_name is not None:
        value = rr_name.encode('ascii')
        extra = b'NM' + bytes((5 + len(value), 1, 0)) + value
    length = 33 + len(name) + (len(name) % 2 == 0) + len(extra)
    record = bytearray(length)
    record[0] = length
    struct.pack_into('<I', record, 2, extent)
    struct.pack_into('>I', record, 6, extent)
    struct.pack_into('<I', record, 10, size)
    struct.pack_into('>I', record, 14, size)
    record[25] = 2 if directory else 0
    record[28:32] = b'\x01\x00\x00\x01'
    record[32] = len(name)
    record[33:33+len(name)] = name
    if extra:
        record[-len(extra):] = extra
    return bytes(record)


def synthetic_iso(path):
    payloads = {'IOSZHSFONTP505': b'SYNTHETIC SIMPLIFIED FONT SUBSET',
                'IOSZHTFONTP505': b'SYNTHETIC TRADITIONAL FONT SUBSET'}
    blob = bytearray(25 * 2048)
    def put(offset, content):
        blob[offset:offset+len(content)] = content
    put(16*2048, b'\x01CD001\x01')
    put(16*2048+40, b'V5.0Ar1094_A1'.ljust(32, b' '))
    put(16*2048+156, iso_record(b'\x00', 20, 2048, True))
    put(20*2048, iso_record('WORLDWID', 21, 2048, True, 'Worldwide_Language_Support'))
    put(21*2048, iso_record('KIT', 22, 2048, True, 'kit'))
    rows = []
    for sector, (name, data) in enumerate(payloads.items(), 23):
        rows.append(iso_record('IOSZHSFO.000;1' if sector == 23 else 'IOSZHTFO.000;1',
                               sector, len(data), rr_name=name))
        put(sector*2048, data)
    put(22*2048, b''.join(rows))
    path.write_bytes(blob)
    return {name: (SHA(data), len(data)) for name, data in payloads.items()}, payloads


class TemporaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def symlink(self, path, target):
        try:
            path.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('Symlink creation is unavailable.')


class CNS40Tests(TemporaryTest):
    def setUp(self):
        super().setUp()
        self.hbf, self.hashes = synthetic_hbf(self.base)
        self.output, self.report = self.base/'font.bdf', self.base/'report.json'
        self.patch = mock.patch.object(cns, 'EXPECTED', self.hashes)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def convert(self):
        return cns.convert(self.hbf, self.output, self.report)

    def test_full_synthetic_roundtrip_source_codes_metrics_and_rows(self):
        details = self.convert()
        text = self.output.read_text()
        parsed = parsed_bdf(text)
        expected = expected_glyphs(self.base)
        self.assertEqual(len(parsed), 6085)
        self.assertEqual(set(parsed), set(expected))
        for code, (bbx, advance, pixels) in parsed.items():
            self.assertEqual((bbx, advance), ((40, 40, 0, -6), (40, 0)))
            self.assertEqual(pixels, expected[code])
        for line in ('DEFAULT_CHAR 8481', 'CHARSET_REGISTRY "CNS11643.92p1"',
                     'FONT_ASCENT 34', 'FONT_DESCENT 6', 'SIZE 40 150 150', 'RESOLUTION_X 75'):
            self.assertIn(line+'\n', text)
        self.assertFalse(details['unicode_remapped'])
        self.assertEqual(details['bdf_sha256'], SHA(self.output.read_bytes()))
        self.assertEqual(json.loads(self.report.read_text()), details)

    def test_production_hashes_reject_synthetic_source(self):
        self.patch.stop()
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.convert()
        self.assertFalse(self.output.exists())

    def test_mutation_of_each_input_rejected(self):
        for name in self.hashes:
            with self.subTest(name=name):
                path = self.base/name
                original = path.read_bytes()
                path.write_bytes(original+b'changed')
                with self.assertRaisesRegex(ValueError, 'hash'):
                    self.convert()
                self.assertFalse(self.output.exists())
                self.assertFalse(self.report.exists())
                path.write_bytes(original)

    def test_missing_each_input_rejected(self):
        for name in self.hashes:
            with self.subTest(name=name):
                path = self.base/name
                raw = path.read_bytes()
                path.unlink()
                with self.assertRaises(FileNotFoundError):
                    self.convert()
                self.assertFalse(self.output.exists())
                path.write_bytes(raw)

    def test_existing_bdf_or_report_not_overwritten(self):
        for path in (self.output, self.report):
            with self.subTest(path=path.name):
                path.write_bytes(b'keep')
                with self.assertRaisesRegex(ValueError, 'overwrite'):
                    self.convert()
                self.assertEqual(path.read_bytes(), b'keep')
                other = self.report if path == self.output else self.output
                self.assertFalse(other.exists())
                path.unlink()

    def test_same_output_and_report_rejected(self):
        with self.assertRaisesRegex(ValueError, 'different'):
            cns.convert(self.hbf, self.output, self.output)
        self.assertFalse(self.output.exists())

    def test_symlink_alias_output_report_rejected(self):
        self.symlink(self.report, self.output)
        with self.assertRaisesRegex(ValueError, 'different'):
            self.convert()
        self.assertFalse(self.output.exists())

    def test_dangling_report_symlink_rejected_before_bdf_write(self):
        self.symlink(self.report, self.base/'absent')
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            self.convert()
        self.assertFalse(self.output.exists())
        self.assertFalse((self.base/'absent').exists())

    def test_missing_report_parent_rejected_before_bdf_write(self):
        with self.assertRaisesRegex(ValueError, 'parent'):
            cns.convert(self.hbf, self.output, self.base/'missing'/'report.json')
        self.assertFalse(self.output.exists())


class ISOStructureTests(unittest.TestCase):
    def test_padded_sector_and_rock_ridge_name(self):
        data = bytes(2048) + iso_record('SHORT.;1', 30, 99, rr_name='Full_Name')
        record, = dec.records(data)
        self.assertEqual((record['name'], record['iso_name'], record['extent'], record['size']),
                         ('Full_Name', 'SHORT.', 30, 99))

    def test_short_record_rejected(self):
        with self.assertRaises(ValueError):
            list(dec.records(bytes((20,))+bytes(19)))

    def test_truncated_record_rejected(self):
        raw = iso_record('NAME', 20, 2048)
        with self.assertRaises(ValueError):
            list(dec.records(raw[:-1]))

    def test_record_crossing_sector_rejected(self):
        prefix = bytearray(2048)
        # Valid records can fill most of a sector, leaving too little for the last.
        large = iso_record('X'*221, 20, 2048)
        prefix[:len(large)*8] = large*8
        self.assertEqual(len(large), 254)
        prefix[2032] = 34
        with self.assertRaises(ValueError):
            list(dec.records(bytes(prefix)+bytes(34)))

    def test_invalid_identifier_length_rejected(self):
        for count in (0, 100):
            with self.subTest(count=count):
                raw = bytearray(iso_record('A', 20, 2048))
                raw[32] = count
                with self.assertRaises(ValueError):
                    list(dec.records(bytes(raw)))

    def test_invalid_rock_ridge_field_lengths_rejected(self):
        for field_length in (0, 3, 100):
            with self.subTest(field_length=field_length):
                raw = bytearray(iso_record('A', 20, 2048, rr_name='FULL'))
                raw[36] = field_length
                with self.assertRaises(ValueError):
                    list(dec.records(bytes(raw)))


class ExtractorTests(TemporaryTest):
    def setUp(self):
        super().setUp()
        self.iso, self.output = self.base/'test.iso', self.base/'export'
        self.expected, self.payloads = synthetic_iso(self.iso)
        self.patch = mock.patch.object(dec, 'SUBSETS', self.expected)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def extract(self):
        return dec.extract(self.iso, self.output)

    def mutate(self, offset, data):
        with self.iso.open('r+b') as stream:
            stream.seek(offset)
            stream.write(data)

    def test_success_only_expected_files_and_report(self):
        result = self.extract()
        self.assertEqual({p.name for p in self.output.iterdir()}, {*self.payloads, 'extraction-report.json'})
        for name, raw in self.payloads.items():
            self.assertEqual((self.output/name).read_bytes(), raw)
        report = json.loads((self.output/'extraction-report.json').read_text())
        self.assertEqual(report['subsets'], result)
        self.assertEqual(report['volume'], 'V5.0Ar1094_A1')

    def test_invalid_volume_rejected(self):
        self.mutate(16*2048+40, b'WRONG_VOLUME'.ljust(32,b' '))
        with self.assertRaisesRegex(ValueError, 'audited'):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_invalid_magic_rejected(self):
        self.mutate(16*2048+1, b'XXXXX')
        with self.assertRaisesRegex(ValueError, 'audited'):
            self.extract()

    def test_truncated_pvd_rejected(self):
        with self.iso.open('r+b') as stream:
            stream.truncate(16*2048+100)
        with self.assertRaisesRegex(ValueError, 'truncated'):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_missing_root_record_is_value_error(self):
        self.mutate(16*2048+156, bytes(34))
        with self.assertRaisesRegex(ValueError, 'root directory'):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_nondirectory_root_rejected(self):
        self.mutate(16*2048+156+25, b'\0')
        with self.assertRaisesRegex(ValueError, 'root directory'):
            self.extract()

    def test_empty_or_ambiguous_directory_rejected(self):
        original = self.iso.read_bytes()
        for data in (bytes(2048), iso_record('WORLDWID',21,2048,True)*2):
            self.iso.write_bytes(original)
            self.mutate(20*2048, data)
            with self.assertRaisesRegex(ValueError, 'Missing or ambiguous'):
                self.extract()
            self.assertFalse(self.output.exists())

    def test_oversize_extent_rejected(self):
        self.mutate(16*2048+156+10, struct.pack('<I',8000001))
        with self.assertRaisesRegex(ValueError, 'extent size'):
            self.extract()

    def test_truncated_payload_rejected(self):
        with self.iso.open('r+b') as stream:
            stream.truncate(24*2048+1)
        with self.assertRaisesRegex(ValueError, 'truncated'):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_hash_mismatch_prevents_all_output(self):
        self.mutate(24*2048, b'CHANGED')
        with self.assertRaisesRegex(ValueError, 'Hash mismatch'):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_production_profile_rejects_synthetic_payloads(self):
        self.patch.stop()
        with self.assertRaisesRegex(ValueError, 'unexpected font subset'):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_existing_subset_or_report_rejected_before_any_write(self):
        self.output.mkdir()
        for name in (*self.payloads, 'extraction-report.json'):
            with self.subTest(name=name):
                path = self.output/name
                path.write_bytes(b'keep')
                with self.assertRaisesRegex(ValueError, 'overwrite'):
                    self.extract()
                self.assertEqual(path.read_bytes(), b'keep')
                self.assertEqual(list(self.output.iterdir()), [path])
                path.unlink()

    def test_dangling_report_symlink_rejected_before_any_write(self):
        self.output.mkdir()
        path = self.output/'extraction-report.json'
        self.symlink(path, self.base/'absent')
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            self.extract()
        self.assertEqual(list(self.output.iterdir()), [path])
        self.assertFalse((self.base/'absent').exists())

    def test_missing_iso_rejected(self):
        self.iso.unlink()
        with self.assertRaises(FileNotFoundError):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_cli_malformed_root_reports_error_without_traceback(self):
        self.mutate(16*2048+156, bytes(34))
        result = subprocess.run([sys.executable, str(SCRIPTS/'extract_dec_font_subsets.py'),
                                 str(self.iso), str(self.output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Error:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)


class OptionalRealInputTests(TemporaryTest):
    @unittest.skipUnless(os.environ.get('LEGACY_EXPORT_CNS40_HBF'), 'optional real CNS40 input not supplied')
    def test_real_cns40_all_source_codes_metrics_and_pixels(self):
        source = Path(os.environ['LEGACY_EXPORT_CNS40_HBF'])
        output, report = self.base/'real.bdf', self.base/'real.json'
        details = cns.convert(source, output, report)
        expected = expected_glyphs(source.parent)
        actual = parsed_bdf(output.read_text())
        self.assertEqual(len(actual), 6085)
        self.assertEqual({code: pixels for code, (_, _, pixels) in actual.items()}, expected)
        self.assertTrue(all((bbx, advance) == ((40,40,0,-6),(40,0)) for bbx, advance, _ in actual.values()))
        self.assertEqual(details['source_sha256'], cns.EXPECTED)

    @unittest.skipUnless(os.environ.get('LEGACY_EXPORT_DEC_ISO'), 'optional real DEC ISO input not supplied')
    def test_real_dec_subset_hashes(self):
        output = self.base/'real-dec'
        result = dec.extract(Path(os.environ['LEGACY_EXPORT_DEC_ISO']), output)
        self.assertEqual(len(result), 2)
        for name, (sha, size) in dec.SUBSETS.items():
            data = (output/name).read_bytes()
            self.assertEqual((SHA(data), len(data)), (sha, size))


if __name__ == '__main__':
    unittest.main()
