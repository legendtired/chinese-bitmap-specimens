#!/usr/bin/env python3
"""Synthetic tests always run; FLIPPERCN_TGZ enables private source validation.
FLIPPERCN_SPECIMEN optionally enables exact comparison with the public specimen.
No font, firmware, or source bitmap rows are included in this test file.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'flippercn_to_bdf.py'
SPEC = importlib.util.spec_from_file_location('flippercn_to_bdf', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
HEADER = bytes([1, 0, 3, 2, 4, 4, 3, 4, 5, 3, 2, 255, 255] + [0] * 10)


def packed(fields):
    bits = []
    for value, width in fields:
        bits.extend((value >> bit) & 1 for bit in range(width))
    return bytes(sum(bits[index + bit] << bit for bit in range(min(8, len(bits) - index)))
                 for index in range(0, len(bits), 8))


def metrics(width=3, height=2, x=-1, y=-1, advance=4):
    return [(width, 4), (height, 4), (x + 4, 3), (y + 8, 4), (advance + 16, 5)]


def read_bdf(text):
    glyphs = {}
    glyph = None
    bitmap = False
    for line in text.splitlines():
        fields = line.split()
        key = fields[0] if fields else ''
        if key == 'STARTCHAR':
            glyph = {'rows': []}
            bitmap = False
        elif key == 'ENDCHAR':
            width = glyph['bbx'][0]
            padding = ((width + 7) // 8) * 8 - width
            glyph['rows'] = [row >> padding for row in glyph['rows']]
            glyphs[glyph['unicode']] = glyph
            glyph = None
            bitmap = False
        elif glyph is not None:
            if key == 'ENCODING':
                glyph['unicode'] = int(fields[1])
            elif key == 'BBX':
                glyph['bbx'] = list(map(int, fields[1:]))
            elif key == 'DWIDTH':
                glyph['advance'] = int(fields[1])
            elif key == 'BITMAP':
                bitmap = True
            elif bitmap:
                glyph['rows'].append(int(line, 16))
    return glyphs


class SyntheticTests(unittest.TestCase):
    def test_lsb_fields_cross_byte_boundaries(self):
        stream = MODULE.Bits(packed([(5, 3), (29, 5), (6, 3)]))
        self.assertEqual([stream.unsigned(n) for n in (3, 5, 3)], [5, 29, 6])

    def test_signed_bias_is_not_twos_complement(self):
        stream = MODULE.Bits(packed([(0, 3), (7, 3)]))
        self.assertEqual([stream.signed(3), stream.signed(3)], [-4, 3])

    def test_repeat_bit_and_row_wrap(self):
        raw = packed(metrics() + [(1, 3), (1, 2), (1, 1), (1, 1), (0, 1)])
        glyph = MODULE.decode_glyph(0x2603, raw, HEADER)
        self.assertEqual(glyph['rows'], [0b010, 0b101])
        self.assertEqual(glyph['bbx'], [3, 2, -1, -1])
        self.assertEqual(glyph['advance'], 4)

    def test_blank_glyph_keeps_advance_and_bearing(self):
        glyph = MODULE.decode_glyph(32, packed(metrics(0, 0, 0, 1, 1)), HEADER)
        self.assertEqual(glyph, {'unicode': 32, 'bbx': [0, 0, 0, 1], 'advance': 1, 'rows': []})

    def test_zero_length_run_rejected(self):
        with self.assertRaisesRegex(ValueError, 'no progress'):
            MODULE.decode_glyph(65, packed(metrics() + [(0, 3), (0, 2)]), HEADER)

    def test_overrun_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            MODULE.decode_glyph(65, packed(metrics() + [(7, 3), (1, 2)]), HEADER)

    def test_truncated_stream_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.decode_glyph(65, b'\x00', HEADER)

    def test_trailing_complete_bytes_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unused'):
            MODULE.decode_glyph(32, packed(metrics(0, 0)) + b'\x00\x00', HEADER)

    def test_wrong_archive_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown input'):
            MODULE.recover(b'Not a firmware archive')

    def test_bdf_roundtrip_keeps_original_metrics(self):
        glyphs = [{'unicode': 0x2603, 'bbx': [3, 2, -1, -1], 'advance': 4, 'rows': [2, 5]},
                  {'unicode': 32, 'bbx': [0, 0, 0, 1], 'advance': 1, 'rows': []}]
        text = MODULE.bdf_text({'bbox': [10, 11, -1, -2], 'glyphs': glyphs})
        self.assertIn('FONTBOUNDINGBOX 10 11 -1 -2\n', text)
        self.assertIn('BITMAP\n40\nA0\nENDCHAR', text)
        self.assertEqual(read_bdf(text), {glyph['unicode']: glyph for glyph in glyphs})

    def test_cli_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'existing.bdf'
            output.write_text('keep me')
            result = subprocess.run([sys.executable, str(SCRIPT), 'absent.tgz', str(output)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('already exists', result.stderr)
            self.assertEqual(output.read_text(), 'keep me')


@unittest.skipUnless(os.environ.get('FLIPPERCN_TGZ'), 'Set FLIPPERCN_TGZ for private source checks')
class PrivateSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.environ['FLIPPERCN_TGZ'])
        cls.archive = cls.source.read_bytes()
        cls.font = MODULE.recover(cls.archive)
        cls.glyphs = {glyph['unicode']: glyph for glyph in cls.font['glyphs']}
        cls.bdf = MODULE.bdf_text(cls.font)

    def test_full_coverage_and_metrics(self):
        self.assertEqual(len(self.glyphs), 604)
        self.assertEqual(sum(0x4E00 <= cp <= 0x9FFF for cp in self.glyphs), 503)
        self.assertTrue(all(cp in self.glyphs for cp in range(32, 127)))
        self.assertNotIn(ord('天'), self.glyphs)
        self.assertNotIn(ord('野'), self.glyphs)
        self.assertEqual(self.font['bbox'], [10, 11, -1, -2])
        self.assertEqual(self.glyphs[ord('足')]['bbx'], [9, 9, -1, -1])
        self.assertEqual(self.glyphs[ord('足')]['advance'], 9)
        self.assertEqual(self.glyphs[ord('选')]['advance'], 11)
        tall = {chr(cp) for cp, glyph in self.glyphs.items()
                if 0x4E00 <= cp <= 0x9FFF and glyph['bbx'][1] == 10}
        self.assertEqual(tall, set('位某波脚默'))

    def test_all_604_bdf_glyphs_roundtrip(self):
        self.assertEqual(read_bdf(self.bdf), self.glyphs)

    def test_same_size_mutation_is_rejected(self):
        modified = bytearray(self.archive)
        modified[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'Unknown input'):
            MODULE.recover(modified)

    def test_cli_inspection_and_export(self):
        inspection = subprocess.run([sys.executable, str(SCRIPT), str(self.source), '--inspect'],
                                    check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(inspection.stdout)['glyphs'], 604)
        with tempfile.TemporaryDirectory() as temporary:
            output, report = Path(temporary) / 'font.bdf', Path(temporary) / 'report.json'
            subprocess.run([sys.executable, str(SCRIPT), str(self.source), str(output),
                            '--report', str(report)], check=True, capture_output=True)
            self.assertEqual(output.read_text(), self.bdf)
            self.assertEqual(json.loads(report.read_text())['outputSha256'], MODULE.sha256(self.bdf.encode('ascii')))

    @unittest.skipUnless(os.environ.get('FLIPPERCN_SPECIMEN'), 'Set FLIPPERCN_SPECIMEN for specimen comparison')
    def test_bdf_pixels_exactly_match_existing_specimen(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow is needed only for the optional existing PNG comparison')
        reference = Image.open(os.environ['FLIPPERCN_SPECIMEN']).convert('RGBA')
        lines = ['设置   显示   输入   返回   确认   菜单',
                 '蓝牙   无线   屏幕   信号   视频   系统',
                 '0123456789   AaBb   GgMm   !?:+-.']
        self.assertEqual(reference.size, (137, 41))
        recovered = Image.new('RGBA', (137, 41))
        glyphs = read_bdf(self.bdf)
        for line_number, text in enumerate(lines):
            cursor, baseline = 0, 9 + line_number * 15
            for character in text:
                glyph = glyphs[ord(character)]
                width, height, x, y = glyph['bbx']
                for row_number, row in enumerate(glyph['rows']):
                    for col in range(width):
                        if row & (1 << (width - 1 - col)):
                            recovered.putpixel((cursor + x + col, baseline - height - y + row_number),
                                               (17, 17, 17, 255))
                cursor += glyph['advance']
        self.assertEqual(recovered.tobytes(), reference.tobytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)
