#!/usr/bin/env python3
"""Source-free offline regression tests; no ROM or third-party Python packages."""
import ctypes
import ctypes.util
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/sharp_x68000_to_bdf.py'
spec = importlib.util.spec_from_file_location('sharp_export', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synthetic_rom():
    """Invented deterministic patterns, not copied or derived ROM glyphs."""
    rom = bytearray(mod.ROM_SIZE)
    for first, last in mod.ROW_GROUPS:
        for row in range(first, last + 1):
            for cell in range(0x21, 0x7F):
                if mod.unicode_for_jis(row, cell) is None or (row, cell) in mod.BLANK_CODES:
                    continue
                start = mod.slot_index(row, cell) * mod.FRAME_BYTES
                frame = bytes([row, cell]) * 16
                rom[start:start + mod.FRAME_BYTES] = frame
    return bytes(rom)


class SharpExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = synthetic_rom()

    def test_independent_slot_walk_and_boundaries(self):
        index = 0
        for first, last in ((0x21, 0x28), (0x30, 0x4F), (0x50, 0x74)):
            for row in range(first, last + 1):
                for cell in range(0x21, 0x7F):
                    self.assertEqual(mod.slot_index(row, cell), index)
                    index += 1
        self.assertEqual(index, 7238)
        self.assertEqual(mod.slot_index(0x30, 0x21) * 32, 0x5E00)
        self.assertEqual(mod.slot_index(0x50, 0x21) * 32, 0x1D600)
        self.assertEqual((mod.slot_index(0x74, 0x7E) + 1) * 32, 0x388C0)
        for row, cell in [(0x20, 0x21), (0x29, 0x21), (0x2F, 0x21), (0x75, 0x21),
                          (0x21, 0x20), (0x21, 0x7F)]:
            with self.assertRaises(ValueError):
                mod.slot_index(row, cell)

    def test_unicode_mapping_known_codes_and_holes(self):
        self.assertEqual(mod.unicode_for_jis(0x21, 0x21), 0x3000)
        self.assertEqual(mod.unicode_for_jis(0x30, 0x21), ord('亜'))
        self.assertEqual(mod.unicode_for_jis(0x74, 0x25), ord('凜'))
        self.assertEqual(mod.unicode_for_jis(0x74, 0x26), ord('熙'))
        self.assertIsNone(mod.unicode_for_jis(0x22, 0x2F))

    def test_synthetic_extraction_counts_mapping_and_exact_pixels(self):
        glyphs = mod.extract(self.rom)
        self.assertEqual(len(glyphs), 6877)
        self.assertEqual(glyphs, sorted(glyphs))
        frames = dict(glyphs)
        self.assertEqual(len(frames), 6877)
        self.assertEqual(sum(any(frame) for frame in frames.values()), 6876)
        self.assertEqual(frames[0x3000], bytes(32))
        self.assertNotIn(ord('凜'), frames)
        self.assertNotIn(ord('熙'), frames)
        self.assertFalse(set(range(128)) & frames.keys())
        han = 0
        for first, last in mod.ROW_GROUPS:
            for row in range(first, last + 1):
                for cell in range(0x21, 0x7F):
                    cp = mod.unicode_for_jis(row, cell)
                    if cp in frames:
                        start = mod.slot_index(row, cell) * 32
                        self.assertEqual(frames[cp], self.rom[start:start + 32])
                        han += row >= 0x30
        self.assertEqual(han, 6353)
        for character in '視野無限廣，窗外有藍天。':
            self.assertIn(ord(character), frames)

    def test_parser_rejects_changed_blanks_or_unmapped_ink(self):
        for row, cell, expect in [(0x74, 0x25, 'blank/nonblank'),
                                  (0x21, 0x21, 'blank/nonblank'),
                                  (0x22, 0x2F, 'Unmapped nonempty')]:
            rom = bytearray(self.rom)
            rom[mod.slot_index(row, cell) * 32] = 0x80
            with self.assertRaisesRegex(ValueError, expect):
                mod.extract(rom)
        rom = bytearray(self.rom)
        start = mod.slot_index(0x30, 0x21) * 32
        rom[start:start + 32] = bytes(32)
        with self.assertRaisesRegex(ValueError, 'blank/nonblank'):
            mod.extract(rom)
        with self.assertRaisesRegex(ValueError, 'size'):
            mod.extract(b'')

    def test_bdf_native_metrics_and_msb_first_rows(self):
        frame = bytes([0x80, 0x01, 0x40, 0x02]) + bytes(28)
        output = mod.make_bdf([(0x4E00, frame)]).decode('ascii')
        for line in ['FONT_ASCENT 16', 'FONT_DESCENT 0', 'DWIDTH 16 0', 'SWIDTH 1000 0',
                     'BBX 16 16 0 0', 'FONTBOUNDINGBOX 16 16 0 0', 'ENCODING 19968',
                     'CHARS 1', 'SIZE 16 72 72', 'RESOLUTION_X 72', 'RESOLUTION_Y 72']:
            self.assertIn(line + '\n', output)
        font = next(line for line in output.splitlines() if line.startswith('FONT ')).split(' ', 1)[1]
        self.assertEqual(len(font.split('-')[1:]), 14)
        self.assertEqual(font.split('-')[2], 'x68000')
        bitmap = output.split('BITMAP\n')[1].split('ENDCHAR')[0].splitlines()
        self.assertEqual(len(bitmap), 16)
        self.assertTrue(all(len(row) == 4 for row in bitmap))
        self.assertEqual(bitmap[:2], ['8001', '4002'])
        self.assertEqual(bytes.fromhex(''.join(bitmap)), frame)
        self.assertIn('Synthetic baseline', output)

    def test_bdf_rejects_bad_frames_or_codepoints(self):
        for glyphs in [[(0x4E00, b'')], [(0x4E00, bytes(32)), (0x4E00, bytes(32))],
                       [(-1, bytes(32))], [(0x110000, bytes(32))], [(0xD800, bytes(32))]]:
            with self.assertRaises(ValueError):
                mod.make_bdf(glyphs)

    def test_freetype_native_16_ppem_strike_when_available(self):
        library_name = ctypes.util.find_library('freetype')
        if not library_name:
            self.skipTest('Optional system FreeType library is unavailable')
        ft = ctypes.CDLL(library_name)
        class BitmapSize(ctypes.Structure):
            _fields_ = [('height', ctypes.c_short), ('width', ctypes.c_short),
                        ('size', ctypes.c_long), ('x_ppem', ctypes.c_long), ('y_ppem', ctypes.c_long)]
        class FaceHead(ctypes.Structure):
            _fields_ = [('num_faces', ctypes.c_long), ('face_index', ctypes.c_long),
                        ('face_flags', ctypes.c_long), ('style_flags', ctypes.c_long),
                        ('num_glyphs', ctypes.c_long), ('family_name', ctypes.c_char_p),
                        ('style_name', ctypes.c_char_p), ('num_fixed_sizes', ctypes.c_int),
                        ('available_sizes', ctypes.POINTER(BitmapSize))]
        library, face = ctypes.c_void_p(), ctypes.POINTER(FaceHead)()
        ft.FT_Init_FreeType.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        ft.FT_New_Face.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long,
                                  ctypes.POINTER(ctypes.POINTER(FaceHead))]
        ft.FT_Done_Face.argtypes = [ctypes.POINTER(FaceHead)]
        ft.FT_Done_FreeType.argtypes = [ctypes.c_void_p]
        self.assertEqual(ft.FT_Init_FreeType(ctypes.byref(library)), 0)
        try:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'synthetic.bdf'
                path.write_bytes(mod.make_bdf([(0x4E00, bytes(range(32)))]))
                self.assertEqual(ft.FT_New_Face(library, str(path).encode(), 0, ctypes.byref(face)), 0)
                try:
                    self.assertEqual(face.contents.num_fixed_sizes, 1)
                    strike = face.contents.available_sizes[0]
                    self.assertEqual((strike.x_ppem, strike.y_ppem), (16 * 64, 16 * 64))
                    self.assertEqual(strike.height, 16)
                finally:
                    ft.FT_Done_Face(face)
        finally:
            ft.FT_Done_FreeType(library)

    def test_missing_size_and_hash_fail_before_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rom, out = root / 'cgrom.dat', root / 'new' / 'out'
            with self.assertRaisesRegex(ValueError, 'Missing'):
                mod.export(rom, out)
            self.assertFalse(out.parent.exists())
            rom.write_bytes(bytes(17))
            with self.assertRaisesRegex(ValueError, 'size'):
                mod.export(rom, out)
            self.assertFalse(out.parent.exists())
            rom.write_bytes(bytes(mod.ROM_SIZE))
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                mod.export(rom, out)
            self.assertFalse(out.parent.exists())

    def test_existing_paths_and_dangling_output_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / 'out'
            directory.mkdir()
            sentinel = directory / 'keep.txt'
            sentinel.write_text('keep')
            link = root / 'link'
            link.symlink_to(root / 'absent')
            for out in [directory, sentinel, link]:
                with self.assertRaisesRegex(ValueError, 'never overwritten'):
                    mod.export(root / 'missing', out)
            self.assertEqual(sentinel.read_text(), 'keep')
            self.assertTrue(link.is_symlink())

    def test_input_links_and_symlinked_ancestors_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            real = root / 'real'
            real.mkdir()
            rom = real / 'cgrom.dat'
            rom.write_bytes(self.rom)
            link = root / 'rom-link'
            link.symlink_to(rom)
            directory_link = root / 'dir-link'
            directory_link.symlink_to(real, target_is_directory=True)
            dangling = root / 'dangling'
            dangling.symlink_to(root / 'absent')
            for source in [link, directory_link / 'cgrom.dat', dangling]:
                with self.assertRaisesRegex(ValueError, 'Symbolic links'):
                    mod.export(source, root / 'out')
            with self.assertRaisesRegex(ValueError, 'Symbolic links'):
                mod.export(rom, directory_link / 'out')
            self.assertFalse((real / 'out').exists())
            self.assertFalse((root / 'out').exists())

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO test requires POSIX')
    def test_nonregular_input_is_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'fifo'
            os.mkfifo(path)
            with self.assertRaisesRegex(ValueError, 'regular file'):
                mod.load_rom(path)

    def test_synthetic_export_is_deterministic_and_no_extra_font(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rom = root / 'invented-test-only.dat'
            rom.write_bytes(self.rom)
            # Only the expected source hash is patched; load, mapping, layout,
            # counts, output guards, and serialization all run normally.
            with mock.patch.object(mod, 'ROM_SHA256', mod.sha256(self.rom)):
                report = mod.export(rom, root / 'first')
                second = mod.export(rom, root / 'second')
            self.assertEqual(report, second)
            self.assertEqual(sorted(p.name for p in (root / 'first').iterdir()),
                             ['export-report.json', 'sharp-x68000-16x16.bdf'])
            bdf = (root / 'first' / mod.OUTPUT_NAME).read_bytes()
            self.assertEqual(bdf, (root / 'second' / mod.OUTPUT_NAME).read_bytes())
            self.assertEqual(report['sha256'], mod.sha256(bdf))
            self.assertEqual(report, json.loads((root / 'first' / 'export-report.json').read_text()))
            self.assertFalse(report['ank_ascii_exported'])
            self.assertFalse(report['24_dot_exported'])
            self.assertEqual(report['jis_level_1_2_nonempty_hanzi'], 6353)
            self.assertEqual(bdf.count(b'\nSTARTCHAR '), 6877)

    def test_cli_failure_and_no_force_or_size_option(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = [sys.executable, str(SCRIPT), '--rom', str(root / 'absent'),
                    '--output', str(root / 'out')]
            result = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Missing ROM file', result.stderr)
            self.assertFalse((root / 'out').exists())
            for extra in [['--force'], ['--size', '24']]:
                result = subprocess.run(args + extra, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 2)
                self.assertIn('unrecognized arguments', result.stderr)


if __name__ == '__main__':
    unittest.main()
