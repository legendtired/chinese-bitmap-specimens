#!/usr/bin/env python3
"""Source-free offline regression tests: invented pixels, no ROM dependency."""
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
SCRIPT = ROOT / 'scripts/fmtowns_f20_to_bdf.py'
spec = importlib.util.spec_from_file_location('fmtowns_export', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synthetic_frame(row, cell):
    """Invented deterministic patterns, not copied or derived ROM glyphs."""
    return b''.join(bytes((row ^ y, cell ^ (19 - y), ((row + cell + y) & 15) << 4))
                    for y in range(20))


def synthetic_rom():
    rom = bytearray(mod.ROM_SIZE)
    rom[:16] = mod.HEADER
    for row in range(0x30, 0x75):
        for cell in range(0x21, 0x7F):
            if mod.unicode_for_jis(row, cell) is None:
                continue
            start = mod.glyph_offset(row, cell)
            rom[start:start + 60] = synthetic_frame(row, cell)
    return bytes(rom)


class FTGeneric(ctypes.Structure):
    _fields_ = [('data', ctypes.c_void_p), ('finalizer', ctypes.c_void_p)]


class FTVector(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]


class FTBBox(ctypes.Structure):
    _fields_ = [(name, ctypes.c_long) for name in ('xMin', 'yMin', 'xMax', 'yMax')]


class FTBitmapSize(ctypes.Structure):
    _fields_ = [('height', ctypes.c_short), ('width', ctypes.c_short),
                ('size', ctypes.c_long), ('x_ppem', ctypes.c_long), ('y_ppem', ctypes.c_long)]


class FTGlyphMetrics(ctypes.Structure):
    _fields_ = [(name, ctypes.c_long) for name in
                ('width', 'height', 'horiBearingX', 'horiBearingY', 'horiAdvance',
                 'vertBearingX', 'vertBearingY', 'vertAdvance')]


class FTBitmap(ctypes.Structure):
    _fields_ = [('rows', ctypes.c_uint), ('width', ctypes.c_uint), ('pitch', ctypes.c_int),
                ('buffer', ctypes.POINTER(ctypes.c_ubyte)), ('num_grays', ctypes.c_ushort),
                ('pixel_mode', ctypes.c_ubyte), ('palette_mode', ctypes.c_ubyte),
                ('palette', ctypes.c_void_p)]


class FTGlyphSlotHead(ctypes.Structure):
    _fields_ = [('library', ctypes.c_void_p), ('face', ctypes.c_void_p),
                ('next', ctypes.c_void_p), ('glyph_index', ctypes.c_uint), ('generic', FTGeneric),
                ('metrics', FTGlyphMetrics), ('linearHoriAdvance', ctypes.c_long),
                ('linearVertAdvance', ctypes.c_long), ('advance', FTVector),
                ('format', ctypes.c_uint32), ('bitmap', FTBitmap),
                ('bitmap_left', ctypes.c_int), ('bitmap_top', ctypes.c_int)]


class FTFaceHead(ctypes.Structure):
    _fields_ = [('num_faces', ctypes.c_long), ('face_index', ctypes.c_long),
                ('face_flags', ctypes.c_long), ('style_flags', ctypes.c_long),
                ('num_glyphs', ctypes.c_long), ('family_name', ctypes.c_char_p),
                ('style_name', ctypes.c_char_p), ('num_fixed_sizes', ctypes.c_int),
                ('available_sizes', ctypes.POINTER(FTBitmapSize)),
                ('num_charmaps', ctypes.c_int), ('charmaps', ctypes.c_void_p),
                ('generic', FTGeneric), ('bbox', FTBBox), ('units_per_EM', ctypes.c_ushort),
                ('ascender', ctypes.c_short), ('descender', ctypes.c_short),
                ('height', ctypes.c_short), ('max_advance_width', ctypes.c_short),
                ('max_advance_height', ctypes.c_short), ('underline_position', ctypes.c_short),
                ('underline_thickness', ctypes.c_short),
                ('glyph', ctypes.POINTER(FTGlyphSlotHead))]


def freetype_bitmap_check(path, glyphs):
    """Verify the actual FreeType strike, metrics and monochrome bitmap bytes."""
    library_name = ctypes.util.find_library('freetype')
    if not library_name:
        raise unittest.SkipTest('Optional system FreeType library is unavailable')
    ft = ctypes.CDLL(library_name)
    face_type = ctypes.POINTER(FTFaceHead)
    ft.FT_Init_FreeType.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    ft.FT_New_Face.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long,
                              ctypes.POINTER(face_type)]
    ft.FT_Select_Size.argtypes = [face_type, ctypes.c_int]
    ft.FT_Get_Char_Index.argtypes = [face_type, ctypes.c_ulong]
    ft.FT_Get_Char_Index.restype = ctypes.c_uint
    ft.FT_Load_Char.argtypes = [face_type, ctypes.c_ulong, ctypes.c_int32]
    ft.FT_Done_Face.argtypes = [face_type]
    ft.FT_Done_FreeType.argtypes = [ctypes.c_void_p]
    check = unittest.TestCase()
    library, face = ctypes.c_void_p(), face_type()
    check.assertEqual(ft.FT_Init_FreeType(ctypes.byref(library)), 0)
    try:
        check.assertEqual(ft.FT_New_Face(library, os.fsencode(path), 0, ctypes.byref(face)), 0)
        try:
            check.assertEqual(face.contents.num_fixed_sizes, 1)
            strike = face.contents.available_sizes[0]
            check.assertEqual((strike.x_ppem, strike.y_ppem), (20 * 64, 20 * 64))
            check.assertEqual(strike.height, 20)
            check.assertEqual(ft.FT_Select_Size(face, 0), 0)
            for codepoint, frame in glyphs:
                check.assertNotEqual(ft.FT_Get_Char_Index(face, codepoint), 0)
                check.assertEqual(ft.FT_Load_Char(face, codepoint, 4), 0)  # FT_LOAD_RENDER
                slot = face.contents.glyph.contents
                check.assertEqual((slot.bitmap_left, slot.bitmap_top), (0, 20))
                check.assertEqual((slot.advance.x, slot.advance.y), (20 * 64, 0))
                metrics = slot.metrics
                check.assertEqual((metrics.width, metrics.height, metrics.horiBearingX,
                                   metrics.horiBearingY, metrics.horiAdvance),
                                  (20 * 64, 20 * 64, 0, 20 * 64, 20 * 64))
                bitmap = slot.bitmap
                check.assertEqual((bitmap.width, bitmap.rows, bitmap.pixel_mode), (20, 20, 1))
                check.assertGreaterEqual(bitmap.pitch, 3)
                actual = b''.join(bytes(bitmap.buffer[y * bitmap.pitch + x] for x in range(3))
                                  for y in range(20))
                check.assertEqual(actual, frame, f'FreeType pixels differ for U+{codepoint:04X}')
        finally:
            ft.FT_Done_Face(face)
    finally:
        ft.FT_Done_FreeType(library)
    return len(glyphs)


class FMTownsExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = synthetic_rom()

    def test_independent_slot_walk_and_boundaries(self):
        offset = 0x17288
        count = 0
        for row in range(0x30, 0x75):
            for cell in range(0x21, 0x7F):
                self.assertEqual(mod.glyph_offset(row, cell), offset)
                offset += 60
                count += 1
        self.assertEqual((count, offset), (6486, 0x762B0))
        for row, cell in [(0x21, 0x21), (0x2F, 0x21), (0x75, 0x21),
                          (0x30, 0x20), (0x30, 0x7F)]:
            with self.assertRaises(ValueError):
                mod.glyph_offset(row, cell)

    def test_unicode_known_codes_and_holes(self):
        self.assertEqual(mod.unicode_for_jis(0x30, 0x21), ord('亜'))
        self.assertEqual(mod.unicode_for_jis(0x74, 0x25), ord('凜'))
        self.assertEqual(mod.unicode_for_jis(0x74, 0x26), ord('熙'))
        self.assertIsNone(mod.unicode_for_jis(0x4F, 0x54))
        self.assertIsNone(mod.unicode_for_jis(0x74, 0x27))

    def test_all_synthetic_pixels_and_hanzi_only_counts(self):
        glyphs = mod.extract(self.rom)
        self.assertEqual(glyphs, sorted(glyphs))
        frames = dict(glyphs)
        self.assertEqual(len(glyphs), len(frames))
        self.assertEqual(len(frames), 6355)
        self.assertEqual(sum(any(frame) for frame in frames.values()), 6355)
        count = 0
        for row in range(0x30, 0x75):
            for cell in range(0x21, 0x7F):
                cp = mod.unicode_for_jis(row, cell)
                if cp is None:
                    continue
                count += 1
                self.assertEqual(frames[cp], synthetic_frame(row, cell))
                for y in range(20):
                    row_bits = int.from_bytes(frames[cp][y * 3:y * 3 + 3], 'big')
                    self.assertEqual(row_bits & 15, 0)
                    for x in range(20):
                        self.assertEqual(bool(frames[cp][y * 3 + x // 8] & (128 >> (x % 8))),
                                         bool(row_bits & (1 << (23 - x))))
        self.assertEqual(count, 6355)
        for character in '視野無限廣窗外有藍天凜熙':
            self.assertIn(ord(character), frames)
        for character in '，。　Aa0':
            self.assertNotIn(ord(character), frames)
        self.assertTrue(all(0x4E00 <= cp <= 0x9FFF for cp in frames))

    def test_bad_size_header_blank_unmapped_or_padding(self):
        with self.assertRaisesRegex(ValueError, 'size'):
            mod.extract(b'')
        for row, cell, mutation, message in [
                (0x30, 0x21, bytes(60), 'blank Hanzi'),
                (0x74, 0x27, bytes([128]) + bytes(59), 'Unmapped nonempty'),
                (0x30, 0x21, bytes([128, 0, 1]) + bytes(57), 'right padding')]:
            changed = bytearray(self.rom)
            start = mod.glyph_offset(row, cell)
            changed[start:start + 60] = mutation
            with self.assertRaisesRegex(ValueError, message):
                mod.extract(changed)
        for offset in (0, 10, 12):
            changed = bytearray(self.rom)
            changed[offset] ^= 1
            with self.assertRaisesRegex(ValueError, 'header'):
                mod.extract(changed)
        with mock.patch.object(mod, 'MAPPING_SHA256', 'not-the-mapping-hash'):
            with self.assertRaisesRegex(ValueError, 'mapping checksum'):
                mod.extract(self.rom)

    def test_bdf_native_metrics_rows_and_synthetic_baseline(self):
        frame = bytes([128, 0, 16, 64, 0, 32]) + bytes(54)
        output = mod.make_bdf([(0x4E00, frame)]).decode('ascii')
        for line in ['FONT_ASCENT 20', 'FONT_DESCENT 0', 'DWIDTH 20 0', 'SWIDTH 1000 0',
                     'BBX 20 20 0 0', 'FONTBOUNDINGBOX 20 20 0 0', 'ENCODING 19968',
                     'CHARS 1', 'SIZE 20 72 72', 'RESOLUTION_X 72', 'RESOLUTION_Y 72']:
            self.assertIn(line + '\n', output)
        font = next(line for line in output.splitlines() if line.startswith('FONT ')).split(' ', 1)[1]
        self.assertEqual(len(font.split('-')[1:]), 14)
        self.assertEqual(font.split('-')[2], 'fmtowns_f20')
        self.assertEqual(font.split('-')[7:], ['20', '200', '72', '72', 'c', '200', 'iso10646', '1'])
        bitmap = output.split('BITMAP\n')[1].split('ENDCHAR')[0].splitlines()
        self.assertEqual(len(bitmap), 20)
        self.assertTrue(all(len(row) == 6 and row[-1] == '0' for row in bitmap))
        self.assertEqual(bitmap[:2], ['800010', '400020'])
        self.assertEqual(bytes.fromhex(''.join(bitmap)), frame)
        self.assertIn('Synthetic baseline ascent/descent 20/0', output)

    def test_bdf_rejects_bad_frames_codepoints_and_padding(self):
        for glyphs in [[(0x4E00, b'')], [(0x4E00, bytes(60)), (0x4E00, bytes(60))],
                       [(-1, bytes(60))], [(0x110000, bytes(60))], [(0xD800, bytes(60))],
                       [(ord('A'), bytes(60))], [(ord('，'), bytes(60))],
                       [(0x4E00, bytes([128, 0, 1]) + bytes(57))]]:
            with self.assertRaises(ValueError):
                mod.make_bdf(glyphs)

    def test_freetype_native_20_ppem_metrics_and_pixels_when_available(self):
        glyphs = [(ord('一'), synthetic_frame(0x30, 0x21)),
                  (ord('凜'), bytes([128, 0, 16]) + bytes(54) + bytes([64, 0, 32]))]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'invented.bdf'
            path.write_bytes(mod.make_bdf(glyphs))
            self.assertEqual(freetype_bitmap_check(path, glyphs), 2)

    def test_missing_size_and_hash_fail_before_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rom, output = root / 'FMT_F20.ROM', root / 'new' / 'out'
            with self.assertRaisesRegex(ValueError, 'Missing'):
                mod.export(rom, output)
            self.assertFalse(output.parent.exists())
            for size in (17, mod.ROM_SIZE - 1, mod.ROM_SIZE + 1):
                rom.write_bytes(bytes(size))
                with self.assertRaisesRegex(ValueError, 'size'):
                    mod.export(rom, output)
                self.assertFalse(output.parent.exists())
            rom.write_bytes(self.rom)
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                mod.export(rom, output)
            self.assertFalse(output.parent.exists())

    def test_parser_failure_also_precedes_output_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            changed = bytearray(self.rom)
            changed[0] ^= 1
            rom = root / 'invented.dat'
            rom.write_bytes(changed)
            with mock.patch.object(mod, 'ROM_SHA256', mod.sha256(changed)):
                with self.assertRaisesRegex(ValueError, 'header'):
                    mod.export(rom, root / 'new' / 'out')
            self.assertFalse((root / 'new').exists())

    def test_existing_paths_and_dangling_output_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / 'out'
            directory.mkdir()
            sentinel = directory / 'keep.txt'
            sentinel.write_text('keep')
            link = root / 'link'
            link.symlink_to(root / 'absent')
            for output in [directory, sentinel, link]:
                with self.assertRaisesRegex(ValueError, 'never overwritten'):
                    mod.export(root / 'missing', output)
            self.assertEqual(sentinel.read_text(), 'keep')
            self.assertTrue(link.is_symlink())

    def test_input_links_and_symlinked_ancestors_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            real = root / 'real'
            real.mkdir()
            rom = real / 'FMT_F20.ROM'
            rom.write_bytes(self.rom)
            link = root / 'rom-link'
            link.symlink_to(rom)
            directory_link = root / 'dir-link'
            directory_link.symlink_to(real, target_is_directory=True)
            dangling = root / 'dangling'
            dangling.symlink_to(root / 'absent')
            for source in [link, directory_link / 'FMT_F20.ROM', dangling]:
                with self.assertRaisesRegex(ValueError, 'Symbolic links'):
                    mod.export(source, root / 'out')
            with self.assertRaisesRegex(ValueError, 'Symbolic links'):
                mod.export(rom, directory_link / 'out')
            self.assertFalse((real / 'out').exists())
            self.assertFalse((root / 'out').exists())

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO test requires POSIX')
    def test_nonregular_input_is_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fifo = root / 'fifo'
            os.mkfifo(fifo)
            with self.assertRaisesRegex(ValueError, 'regular file'):
                mod.load_rom(fifo)
            with self.assertRaises((OSError, ValueError)):
                mod.load_rom(root)

    def test_read_only_deterministic_export_and_no_extra_fonts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rom = root / 'invented-test-only.dat'
            rom.write_bytes(self.rom)
            rom.chmod(0o444)
            # Patch only the expected input hash: real load, header, mapping,
            # counts, padding, serialization and output guards remain active.
            real_open = os.open
            with mock.patch.object(mod, 'ROM_SHA256', mod.sha256(self.rom)):
                with mock.patch.object(mod.os, 'open', wraps=real_open) as opened:
                    first = mod.export(rom, root / 'first')
                    flags = opened.call_args_list[0].args[1]
                    self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
                second = mod.export(rom, root / 'second')
                with self.assertRaisesRegex(ValueError, 'never overwritten'):
                    mod.export(rom, root / 'first')
            self.assertEqual(rom.read_bytes(), self.rom)
            self.assertEqual(first, second)
            self.assertEqual(sorted(path.name for path in (root / 'first').iterdir()),
                             ['export-report.json', 'fmtowns-f20-20x20.bdf'])
            bdf = (root / 'first' / mod.OUTPUT_NAME).read_bytes()
            self.assertEqual(bdf, (root / 'second' / mod.OUTPUT_NAME).read_bytes())
            self.assertEqual(first['sha256'], mod.sha256(bdf))
            self.assertEqual(first, json.loads((root / 'first' / 'export-report.json').read_text()))
            self.assertEqual(first['jis_level_1_2_nonempty_hanzi'], 6355)
            self.assertEqual(first['unmapped_blank_hanzi_slots'], 131)
            self.assertEqual(first['synthetic_ascent_descent'], [20, 0])
            self.assertTrue(first['right_padding_bits_zero'])
            for key in ['symbols_exported', 'ank_ascii_exported', '16_dot_exported']:
                self.assertFalse(first[key])
            self.assertEqual(bdf.count(b'\nSTARTCHAR '), 6355)

    def test_cli_failure_and_no_force_size_or_symbol_option(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = [sys.executable, str(SCRIPT), '--rom', str(root / 'absent'),
                    '--output', str(root / 'out')]
            result = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Missing ROM file', result.stderr)
            self.assertFalse((root / 'out').exists())
            for extra in [['--force'], ['--size', '16'], ['--symbols'], ['--skip-checksum']]:
                result = subprocess.run(args + extra, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 2)
                self.assertIn('unrecognized arguments', result.stderr)
            self.assertFalse((root / 'out').exists())


if __name__ == '__main__':
    unittest.main()
