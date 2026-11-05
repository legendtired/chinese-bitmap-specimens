#!/usr/bin/env python3
"""Source-free Nokia regression tests. Every fixture pixel is invented."""
import contextlib
import ctypes
import ctypes.util
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
SCRIPT = ROOT / 'scripts/nokia_dct3_to_bdf.py'
spec = importlib.util.spec_from_file_location('nokia_export', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


@contextlib.contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def block(address, data):
    return (bytes([11]) + address.to_bytes(3, 'big') + b'\0'
            + len(data).to_bytes(3, 'big') + b'\0' + data)


def invented_ppm():
    # A small file with four format records, twelve width matrices and only
    # invented diagonal/noise patterns. Not extracted or traced source glyphs.
    groups = [(65, 66, 8, 13, 10, 3), (103, 103, 7, 13, 9, 5),
              (0x4E00, 0x4E01, 11, 12, 11, 7)]
    marker = 64
    start = marker + 28
    records_end = start + 4 + 44 * 4
    indexes = [records_end, records_end + 24, records_end + 32, records_end + 40]
    matrix_start = records_end + 48 + 4 * 8
    data_start = matrix_start + 12 * 12
    data = bytearray(data_start + sum(w * 8 for w in range(1, 13)))
    data[:len(mod.PPM_HEADER)] = mod.PPM_HEADER
    data[marker:marker + 9] = b'FONTfconv'
    struct.pack_into('>I', data, start, 4)
    names = [(b'large', b'bold'), (b'small', b'plain'), (b'small', b'bold'), (b'tiny', b'plain')]
    for i, (name, style) in enumerate(names):
        offset = start + 4 + 44 * i
        struct.pack_into('>I', data, offset + 8, indexes[i] - offset)
        struct.pack_into('>H', data, offset + 14, 2 if i == 0 else 0)
        data[offset + 24:offset + 24 + len(name)] = name
        data[offset + 35:offset + 35 + len(style)] = style
    origins, cursor = {}, data_start
    for w in range(1, 13):
        offset = matrix_start + (w - 1) * 12
        struct.pack_into('>IHHI', data, offset, cursor - offset, 1, w, 64)
        origins[w] = cursor
        cursor += w * 8
    expected = {}
    for i, (first, last, w, h, baseline, y) in enumerate(groups):
        packed = (y << 14) | ((w - 1) << 10) | (h << 5) | baseline
        struct.pack_into('>HHI', data, indexes[0] + i * 8, first, last, packed)
        for cp in range(first, last + 1):
            # Row asymmetry detects reversed axes, bit order and byte alignment.
            rows = [((cp * 17 + row * 29) ^ (1 << (row % w))) & ((1 << w) - 1)
                    for row in range(h)]
            expected[cp] = {'width': w, 'height': h, 'baseline': baseline, 'rows': rows}
            for row, bits in enumerate(rows):
                yy = y + (cp - first) * h + row
                for x in range(w):
                    if bits & (1 << (w - x - 1)):
                        data[origins[w] + (yy // 8) * w + x] |= 1 << (yy % 8)
    for index in indexes[1:]:
        struct.pack_into('>HHI', data, index, 32, 32, (1 << 5) | 1)
    return bytes(data), expected, {'start': start, 'indexes': indexes, 'matrix': matrix_start,
                                  'data': data_start, 'origins': origins}


def read_bdf(data):
    result = {}
    for block_text in data.decode('ascii').split('STARTCHAR ')[1:]:
        lines = block_text.splitlines()
        cp = int(next(line for line in lines if line.startswith('ENCODING ')).split()[1])
        w, h, x, y = map(int, next(line for line in lines if line.startswith('BBX ')).split()[1:])
        advance = tuple(map(int, next(line for line in lines if line.startswith('DWIDTH ')).split()[1:]))
        rows = lines[lines.index('BITMAP') + 1:lines.index('ENDCHAR')]
        stride = (w + 7) // 8
        if len(rows) != h or any(len(row) != stride * 2 for row in rows) or cp in result:
            raise ValueError('Invalid or duplicate BDF glyph')
        raw = [int(row, 16) for row in rows]
        if any(row & ((1 << (stride * 8 - w)) - 1) for row in raw):
            raise ValueError('Nonzero BDF row padding')
        result[cp] = {'width': w, 'height': h, 'baseline': y + h,
                      'rows': [row >> (stride * 8 - w) for row in raw],
                      'x': x, 'advance': advance}
    return result


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
    """Read the actual native strike and verify every metric and monochrome pixel."""
    library_name = ctypes.util.find_library('freetype')
    if not library_name:
        raise unittest.SkipTest('Optional system FreeType library is unavailable')
    ft = ctypes.CDLL(library_name)
    face_type = ctypes.POINTER(FTFaceHead)
    ft.FT_Init_FreeType.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    ft.FT_New_Face.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.POINTER(face_type)]
    ft.FT_Select_Size.argtypes = [face_type, ctypes.c_int]
    ft.FT_Get_Char_Index.argtypes = [face_type, ctypes.c_ulong]
    ft.FT_Get_Char_Index.restype = ctypes.c_uint
    ft.FT_Load_Char.argtypes = [face_type, ctypes.c_ulong, ctypes.c_int32]
    ft.FT_Done_Face.argtypes = [face_type]
    ft.FT_Done_FreeType.argtypes = [ctypes.c_void_p]
    check, library, face = unittest.TestCase(), ctypes.c_void_p(), face_type()
    ascent = max(g['baseline'] for g in glyphs.values())
    descent = max(g['height'] - g['baseline'] for g in glyphs.values())
    check.assertEqual(ft.FT_Init_FreeType(ctypes.byref(library)), 0)
    try:
        check.assertEqual(ft.FT_New_Face(library, os.fsencode(path), 0, ctypes.byref(face)), 0)
        try:
            check.assertEqual(face.contents.num_fixed_sizes, 1)
            strike = face.contents.available_sizes[0]
            check.assertEqual((strike.x_ppem, strike.y_ppem), ((ascent + descent) * 64,) * 2)
            check.assertEqual(strike.height, ascent + descent)
            check.assertEqual(ft.FT_Select_Size(face, 0), 0)
            for cp, g in glyphs.items():
                w, h, baseline = g['width'], g['height'], g['baseline']
                check.assertNotEqual(ft.FT_Get_Char_Index(face, cp), 0)
                check.assertEqual(ft.FT_Load_Char(face, cp, 4), 0)  # FT_LOAD_RENDER
                slot = face.contents.glyph.contents
                check.assertEqual((slot.bitmap_left, slot.bitmap_top), (0, baseline))
                check.assertEqual((slot.advance.x, slot.advance.y), (w * 64, 0))
                metrics = slot.metrics
                check.assertEqual((metrics.width, metrics.height, metrics.horiBearingX,
                                   metrics.horiBearingY, metrics.horiAdvance),
                                  (w * 64, h * 64, 0, baseline * 64, w * 64))
                bitmap = slot.bitmap
                stride = (w + 7) // 8
                check.assertEqual((bitmap.width, bitmap.rows, bitmap.pixel_mode), (w, h, 1))
                check.assertGreaterEqual(bitmap.pitch, stride)
                actual = b''.join(bytes(bitmap.buffer[y * bitmap.pitch + x] for x in range(stride))
                                  for y in range(h))
                expected = b''.join((row << (stride * 8 - w)).to_bytes(stride, 'big') for row in g['rows'])
                check.assertEqual(actual, expected, f'FreeType pixels differ for U+{cp:04X}')
        finally:
            ft.FT_Done_Face(face)
    finally:
        ft.FT_Done_FreeType(library)
    return len(glyphs)


class NokiaExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ppm, cls.glyphs, cls.locations = invented_ppm()

    def test_exact_source_allowlist(self):
        self.assertEqual(mod.SOURCE_SIZE, 656080)
        self.assertEqual(mod.SOURCE_SHA256, '6fc1ac3669091c615d22ebccb39ee0e056239fd1a0ab99a44053a52ad26cc444')
        for data in (b'', b'PPM\0', b'\0' * mod.SOURCE_SIZE, b'MZ' + bytes(mod.SOURCE_SIZE - 2)):
            with self.assertRaisesRegex(ValueError, 'Unsupported input'):
                mod.decode(data)

    def test_blocks_valid_non_aligned_and_max_size(self):
        self.assertEqual(mod.normalize(block(4096, b'abc') + block(4099, b'def')), (b'abcdef', 2))
        self.assertEqual(mod.normalize(block(0, bytes(8192))), (bytes(8192), 1))

    def test_blocks_reject_boundaries_lengths_addresses_and_trailing_data(self):
        good = block(4096, b'abc')
        bad = [b'', good[:-1], good + b'\0', good + block(4100, b'def'),
               b'\x0a' + good[1:], block(0, b''), block(0, bytes(8193)),
               block(0xFFFFFF, b'ab'), bytes(mod.SOURCE_SIZE + 1)]
        for data in bad:
            with self.subTest(length=len(data)), self.assertRaises(ValueError):
                mod.normalize(data)

    def test_integer_boundaries(self):
        self.assertEqual(mod.integer(b'\x01\x02', 0, 2), 258)
        for offset, size in ((-1, 2), (1, 2), (0, 4), (0, 3)):
            with self.assertRaises(ValueError):
                mod.integer(b'\x01\x02', offset, size)

    def test_synthetic_vertical_packing_all_pixels(self):
        actual, start = mod.parse_ppm(self.ppm)
        self.assertEqual(start, self.locations['start'])
        self.assertEqual(actual, self.glyphs)
        # A two-character range crosses vertical-byte boundaries repeatedly.
        self.assertNotEqual(actual[65]['rows'], actual[66]['rows'])
        self.assertEqual((actual[0x4E00]['width'], actual[0x4E00]['height']), (11, 12))
        self.assertEqual(actual[65]['height'], 13)

    def test_ppm_truncated_headers_tables_matrices_and_duplicates(self):
        for length in (0, 35, 70, self.locations['start'] + 3,
                       self.locations['indexes'][0] - 1, self.locations['matrix'] - 1,
                       self.locations['data'] - 1, len(self.ppm) - 1):
            with self.subTest(length=length), self.assertRaises(ValueError):
                mod.parse_ppm(self.ppm[:length])
        changed = bytearray(self.ppm)
        changed[-9:] = b'FONTfconv'
        with self.assertRaisesRegex(ValueError, 'one FONT'):
            mod.parse_ppm(changed)
        changed = bytearray(self.ppm)
        changed[self.locations['start'] + 4 + 24] = 255
        with self.assertRaisesRegex(ValueError, 'name'):
            mod.parse_ppm(changed)

    def test_ppm_record_pointer_and_matrix_rejections(self):
        start, index, matrix = self.locations['start'], self.locations['indexes'][0], self.locations['matrix']
        cases = [(start, 4, 3), (start + 4 + 8, 4, 0), (start + 4 + 8, 4, len(self.ppm)),
                 (start + 4 + 14, 2, 65535), (matrix, 4, 0), (matrix, 4, len(self.ppm)),
                 (matrix + 4, 2, 0), (matrix + 6, 2, 0), (matrix + 6, 2, 13),
                 (matrix + 12 + 6, 2, 1), (matrix + 8, 4, 0), (matrix + 8, 4, 63),
                 (matrix + 8, 4, 1000000)]
        for offset, size, value in cases:
            changed = bytearray(self.ppm)
            changed[offset:offset + size] = value.to_bytes(size, 'big')
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                mod.parse_ppm(changed)
        # Change the second font name to large-bold: selecting ambiguously is forbidden.
        changed = bytearray(self.ppm)
        changed[start + 4 + 44 + 24:start + 4 + 44 + 41] = changed[start + 4 + 24:start + 4 + 41]
        with self.assertRaisesRegex(ValueError, 'one large-bold'):
            mod.parse_ppm(changed)

    def test_character_groups_reject_duplicates_surrogates_and_overflow(self):
        index = self.locations['indexes'][0]
        for first, last, w, h, baseline, y in ((66, 65, 8, 13, 10, 3),
                (0xD7FF, 0xD800, 8, 13, 10, 3), (0xDFFF, 0xE000, 8, 13, 10, 3),
                (65, 66, 13, 13, 10, 3), (65, 66, 8, 0, 0, 3),
                (65, 66, 8, 13, 14, 3), (65, 66, 8, 13, 10, 50)):
            changed = bytearray(self.ppm)
            packed = (y << 14) | ((w - 1) << 10) | (h << 5) | baseline
            struct.pack_into('>HHI', changed, index, first, last, packed)
            with self.subTest(first=first, w=w, h=h, y=y), self.assertRaises(ValueError):
                mod.parse_ppm(changed)
        changed = bytearray(self.ppm)
        changed[index + 8:index + 16] = changed[index:index + 8]
        with self.assertRaisesRegex(ValueError, 'Duplicate Unicode'):
            mod.parse_ppm(changed)

    def test_validation_checks_coverage_and_independent_pixel_digest(self):
        with self.assertRaisesRegex(ValueError, 'coverage'):
            mod.validate_glyphs(self.glyphs)
        han = sorted(mod.gb2312_hanzi())
        han_set = set(han)
        han += [cp for cp in range(0x4E00, 0xA000) if cp not in han_set][:2241]
        full = {cp: {'width': 11, 'height': 12, 'baseline': 11, 'rows': [1] * 12} for cp in han}
        full.update({cp: {'width': 3, 'height': 13, 'baseline': 10, 'rows': [1] * 13}
                     for cp in range(381)})
        digest = mod.indexed_digest(full)
        with mock.patch.object(mod, 'INDEXED_SHA256', digest):
            mod.validate_glyphs(full)
            modified = dict(full)
            modified[han[0]] = dict(full[han[0]], rows=[0] * 12)
            with self.assertRaisesRegex(ValueError, 'blank'):
                mod.validate_glyphs(modified)
            modified[han[0]] = dict(full[han[0]], rows=[2] * 12)
            with self.assertRaisesRegex(ValueError, 'checksum'):
                mod.validate_glyphs(modified)
            del modified[han[0]]
            replacement = next(cp for cp in range(0x4E00, 0xA000) if cp not in full)
            modified[replacement] = full[han[0]]
            with self.assertRaisesRegex(ValueError, 'Missing GB2312'):
                mod.validate_glyphs(modified)

    def test_gb2312_hanzi_standard_coverage(self):
        self.assertEqual(len(mod.gb2312_hanzi()), 6763)
        for pair in (b'\xb0\xa1', b'\xd6\xd0', b'\xf7\xfe'):
            self.assertIn(ord(pair.decode('gb2312')), mod.gb2312_hanzi())

    def test_bdf_roundtrip_metrics_11x12_han_13high_latin_and_padding(self):
        bdf = mod.make_bdf(self.glyphs)
        parsed = read_bdf(bdf)
        for cp, g in self.glyphs.items():
            self.assertEqual(parsed[cp], dict(g, x=0, advance=(g['width'], 0)))
        for line in ('SIZE 15 72 72', 'FONTBOUNDINGBOX 11 15 0 -4', 'FONT_ASCENT 11',
                     'FONT_DESCENT 4', 'PIXEL_SIZE 15', 'POINT_SIZE 150', 'RESOLUTION_X 72',
                     'RESOLUTION_Y 72', 'BBX 11 12 0 -1', 'BBX 8 13 0 -3', 'BBX 7 13 0 -4'):
            self.assertIn((line + '\n').encode(), bdf)
        tiny = mod.make_bdf({65: {'width': 3, 'height': 4, 'baseline': 3, 'rows': [2, 5, 7, 5]}})
        self.assertIn(b'BBX 3 4 0 -1\nBITMAP\n40\nA0\nE0\nA0', tiny)
        han = {cp: g for cp, g in self.glyphs.items() if cp >= 0x4E00}
        self.assertIn(b'SIZE 12 72 72\nFONTBOUNDINGBOX 11 12 0 -1', mod.make_bdf(han))

    def test_bdf_rejects_bad_glyphs(self):
        g = self.glyphs[65]
        for bad in ({}, {-1: g}, {0xD800: g}, {0x10000: g}, {'65': g}, {True: g},
                    {65: dict(g, width=0)}, {65: dict(g, height=0)}, {65: dict(g, baseline=14)},
                    {65: dict(g, rows=[1])}, {65: dict(g, rows=[256] * 13)},
                    {65: dict(g, rows=[-1] * 13)}, {65: dict(g, rows=[True] * 13)},
                    {65: dict(g, unexpected=0)}):
            with self.assertRaises(ValueError):
                mod.make_bdf(bad)

    def test_freetype_native_strikes_and_all_invented_metrics_pixels(self):
        with tempfile.TemporaryDirectory() as temp:
            for chosen in (self.glyphs, {cp: g for cp, g in self.glyphs.items() if cp >= 0x4E00}):
                path = Path(temp) / 'invented.bdf'
                path.write_bytes(mod.make_bdf(chosen))
                self.assertEqual(freetype_bitmap_check(path, chosen), len(chosen))

    def test_missing_size_hash_failures_create_no_outputs(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            for data in (None, b'', bytes(mod.SOURCE_SIZE - 1), bytes(mod.SOURCE_SIZE + 1), bytes(mod.SOURCE_SIZE)):
                if data is not None:
                    Path('source').write_bytes(data)
                with self.assertRaises(ValueError):
                    mod.export('source', 'local-research/out.bdf')
                self.assertFalse(Path('local-research').exists())

    def test_input_symlinks_and_nonregular_inputs(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            Path('real').mkdir()
            Path('real/source').write_bytes(self.ppm)
            Path('link').symlink_to(Path('real').absolute(), target_is_directory=True)
            Path('source-link').symlink_to(Path('real/source').absolute())
            Path('dangling').symlink_to(Path('absent').absolute())
            for source in ('source-link', 'link/source', 'dangling'):
                with self.assertRaisesRegex(ValueError, 'Symbolic links'):
                    mod.load_font(source)
            if hasattr(os, 'mkfifo'):
                os.mkfifo('fifo')
                with self.assertRaisesRegex(ValueError, 'regular file'):
                    mod.load_font('fifo')
            with self.assertRaises((OSError, ValueError)):
                mod.load_font('real')

    def test_output_and_report_reject_existing_files_escapes_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            Path('local-research').mkdir()
            Path('local-research/existing.bdf').write_bytes(b'keep')
            Path('local-research/existing.json').write_bytes(b'keep')
            Path('outside').mkdir()
            Path('local-research/link').symlink_to(Path('outside').absolute(), target_is_directory=True)
            Path('local-research/dangling.bdf').symlink_to(Path('absent').absolute())
            for output in ('out.bdf', '../out.bdf', 'local-research/../out.bdf',
                           'local-research/existing.bdf', 'local-research/link/out.bdf',
                           'local-research/dangling.bdf', 'local-research/out.txt'):
                with self.assertRaises(ValueError):
                    mod.export('missing', output)
            for report in ('out.json', '../out.json', 'local-research/../out.json',
                           'local-research/existing.json', 'local-research/link/out.json',
                           'local-research/out.bdf'):
                with self.assertRaises(ValueError):
                    mod.export('missing', 'local-research/out.bdf', report)
            for source in ('local-research/out.bdf', 'local-research/out.json'):
                with self.assertRaisesRegex(ValueError, 'overwrite the input'):
                    mod.export(source, 'local-research/out.bdf')
            self.assertEqual(Path('local-research/existing.bdf').read_bytes(), b'keep')
            self.assertEqual(Path('local-research/existing.json').read_bytes(), b'keep')
            self.assertEqual(list(Path('outside').iterdir()), [])

    def test_synthetic_export_is_deterministic_read_only_and_filters_cjk(self):
        fake_source = b'invented source, no firmware'
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            source = Path('invented')
            source.write_bytes(fake_source)
            source.chmod(0o444)
            with mock.patch.multiple(mod, SOURCE_SIZE=len(fake_source), SOURCE_SHA256=mod.sha256(fake_source)), \
                    mock.patch.object(mod, 'decode', side_effect=lambda _: (self.glyphs, {'glyphs': len(self.glyphs)})):
                first = mod.export(source, 'local-research/first.bdf')
                second = mod.export(source, 'local-research/nested/second.bdf')
                self.assertEqual(first, second)
                han = mod.export(source, 'local-research/han.bdf', cjk_only=True)
                self.assertEqual(han['exported_glyphs'], 2)
                self.assertEqual(han['bdf_ascent_descent'], [11, 1])
                with self.assertRaisesRegex(ValueError, 'never overwritten'):
                    mod.export(source, 'local-research/first.bdf')
                with self.assertRaisesRegex(ValueError, 'never overwritten'):
                    mod.export(source, 'local-research/new.bdf', 'local-research/first.json')
                self.assertFalse(Path('local-research/new.bdf').exists())
            self.assertEqual(source.read_bytes(), fake_source)
            self.assertEqual(Path('local-research/first.bdf').read_bytes(),
                             Path('local-research/nested/second.bdf').read_bytes())
            self.assertEqual(json.loads(Path('local-research/first.json').read_text()), first)
            self.assertEqual(first['bdf_ascent_descent'], [11, 4])

    def test_parser_failure_precedes_output_directory_creation(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            with mock.patch.object(mod, 'load_font', return_value=b'not valid'):
                with self.assertRaises(ValueError):
                    mod.export('source', 'local-research/nested/out.bdf')
            self.assertFalse(Path('local-research').exists())

    def test_pair_rollback_when_second_creation_fails(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            real_open = os.open
            def fail_report(path, flags, *args, **kwargs):
                if path == 'out.json' and flags & os.O_CREAT:
                    raise OSError('Invented report write failure')
                return real_open(path, flags, *args, **kwargs)
            with mock.patch.object(mod.os, 'open', side_effect=fail_report):
                with self.assertRaisesRegex(OSError, 'Invented'):
                    mod.write_outputs('local-research/out.bdf', b'invented', 'local-research/out.json', b'{}')
            self.assertFalse(Path('local-research/out.bdf').exists())
            self.assertFalse(Path('local-research/out.json').exists())

    def test_exclusive_pair_creation_preserves_racing_report(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            real_open = os.open
            def report_appears(path, flags, *args, **kwargs):
                if path == 'out.json' and flags & os.O_CREAT:
                    Path('local-research/out.json').write_bytes(b'keep racing file')
                return real_open(path, flags, *args, **kwargs)
            with mock.patch.object(mod.os, 'open', side_effect=report_appears):
                with self.assertRaises(FileExistsError):
                    mod.write_outputs('local-research/out.bdf', b'invented', 'local-research/out.json', b'{}')
            self.assertFalse(Path('local-research/out.bdf').exists())
            self.assertEqual(Path('local-research/out.json').read_bytes(), b'keep racing file')

    def test_read_only_input_and_private_output_permissions(self):
        data = b'invented bytes'
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            Path('source').write_bytes(data)
            real_open = os.open
            with mock.patch.multiple(mod, SOURCE_SIZE=len(data), SOURCE_SHA256=mod.sha256(data)), \
                    mock.patch.object(mod.os, 'open', wraps=real_open) as opened:
                self.assertEqual(mod.load_font('source'), data)
                self.assertTrue(all(call.args[1] & os.O_ACCMODE == os.O_RDONLY
                                    for call in opened.call_args_list))
            mod.write_outputs('local-research/out.bdf', b'invented', 'local-research/reports/out.json', b'{}')
            for path in ('local-research/out.bdf', 'local-research/reports/out.json'):
                self.assertEqual(Path(path).stat().st_mode & 0o777, 0o600)
            os.link('source', 'local-research/hardlink.bdf')
            with self.assertRaisesRegex(ValueError, 'never overwritten'):
                mod.export('source', 'local-research/hardlink.bdf')
            self.assertEqual(Path('source').read_bytes(), data)

    def test_writer_refuses_directory_symlink_swap(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            Path('local-research').mkdir()
            Path('outside').mkdir()
            real_open, swapped = os.open, False
            def open_with_swap(path, flags, *args, **kwargs):
                nonlocal swapped
                if path == 'local-research' and not swapped:
                    swapped = True
                    Path('local-research').rmdir()
                    Path('local-research').symlink_to(Path('outside').absolute(), target_is_directory=True)
                return real_open(path, flags, *args, **kwargs)
            with mock.patch.object(mod.os, 'open', side_effect=open_with_swap):
                with self.assertRaises(OSError):
                    mod.write_outputs('local-research/out.bdf', b'invented', 'local-research/out.json', b'{}')
            self.assertEqual(list(Path('outside').iterdir()), [])

    def test_input_directory_symlink_swap_is_not_followed(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            Path('input').mkdir()
            Path('input/source').write_bytes(b'keep')
            Path('outside').mkdir()
            Path('outside/source').write_bytes(b'other')
            real_open, swapped = os.open, False
            def open_with_swap(path, flags, *args, **kwargs):
                nonlocal swapped
                if path == 'input' and not swapped:
                    swapped = True
                    Path('input').rename('saved-input')
                    Path('input').symlink_to(Path('outside').absolute(), target_is_directory=True)
                return real_open(path, flags, *args, **kwargs)
            with mock.patch.object(mod.os, 'open', side_effect=open_with_swap):
                with self.assertRaises(OSError):
                    mod.load_font('input/source')
            self.assertEqual(Path('saved-input/source').read_bytes(), b'keep')
            self.assertEqual(Path('outside/source').read_bytes(), b'other')

    def test_safe_platform_requirement_fails_closed(self):
        with mock.patch.object(mod, 'SAFE_DIR_FD', False):
            with self.assertRaisesRegex(ValueError, 'POSIX'):
                mod.load_font('anything')
            with self.assertRaisesRegex(ValueError, 'POSIX'):
                mod.write_outputs('local-research/out.bdf', b'', 'local-research/out.json', b'')

    def test_cli_help_optimized_hash_rejection_and_no_bypass_flags(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'bad').write_bytes(bytes(mod.SOURCE_SIZE))
            base = [sys.executable, str(SCRIPT)]
            result = subprocess.run(base + ['--help'], cwd=temp, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0)
            self.assertIn('local-research', result.stdout)
            args = ['--font', 'bad', '--output', 'local-research/out.bdf']
            for flags in ([], ['-O']):
                result = subprocess.run([sys.executable] + flags + [str(SCRIPT)] + args,
                                        cwd=temp, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 1)
                self.assertIn('SHA-256 mismatch', result.stderr)
            for extra in (['--force'], ['--skip-checksum'], ['--allow-unknown'], ['--size', '12']):
                result = subprocess.run(base + args + extra, cwd=temp, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 2)
            self.assertFalse((path / 'local-research').exists())


if __name__ == '__main__':
    unittest.main()
