#!/usr/bin/env python3
"""Source-free IBM PC DOS regression tests. All fixture pixels are invented."""
import contextlib
import ctypes
import ctypes.util
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/ibm_pcdos_to_bdf.py'
spec = importlib.util.spec_from_file_location('ibm_export', SCRIPT)
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


def invented_frame(record_id):
    return bytes((0x10, 0x01, 0x20)[(record_id + i) % 3] for i in range(72))


def invented_font(records=None):
    # Invented prefix tree: eight unary leaves, then eight 11-bit leaves.
    # Nothing here is copied from font data or depends on a local FNT.
    if records is None:
        records = {256: invented_frame(256), 2249: invented_frame(2249),
                   3640: invented_frame(3640)}
    table = bytearray(264)
    codes = {rank: '0' * rank + '1' for rank in range(8)}
    codes.update({rank: '00000000' + f'{rank - 8:03b}' for rank in range(8, 16)})
    for look in range(1, 256):
        bits = f'{look:08b}'
        rank = bits.index('1')
        table[look] = ((rank + 1) << 4) | rank
    for look in range(8):
        table[256 + look] = 0x30 | (look + 8)
    sectors = [bytearray(b'\xff' * 512)]
    first_ids = []
    cursor = 0
    for record_id, frame in sorted(records.items()):
        bits = ''.join(codes[n] for byte in frame for n in (byte >> 4, byte & 15))
        bits += '0' * (-len(bits) % 8)
        payload = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
        record = struct.pack('<HB', record_id, len(payload)) + payload
        if cursor + len(record) > 512:
            sectors.append(bytearray(b'\xff' * 512))
            cursor = 0
        if cursor == 0:
            first_ids.append(record_id)
        sectors[-1][cursor:cursor + len(record)] = record
        cursor += len(record)
    data = bytearray(0x1A00)
    data[:16] = b'System DBCS 24  '
    for offset, value in ((16, 1381), (18, 24), (20, 24), (22, 1), (24, 72), (28, 1)):
        struct.pack_into('<H', data, offset, value)
    data[0x1E:0x26] = b'01/24/92'
    data[0x2A:0x2E] = '楷体'.encode('gb2312')
    data[0xC0:0x1C8] = table
    data[0x200:0xA00] = bytes.fromhex('0123456789abcdef') * 256
    data[0xA00:0x1A00] = b'\xff' * 4096
    leaf_slots = [p for p in range(0xA00, 0x1A00, 4) if not 0xBC0 <= p < 0xBE0]
    if len(first_ids) > len(leaf_slots):
        raise ValueError('Test fixture exceeds directory capacity')
    for index, record_id in enumerate(first_ids):
        struct.pack_into('<HH', data, leaf_slots[index], record_id, 8 + index)
    for page in range(8):
        first_id = struct.unpack_from('<H', data, 0xA00 + 512 * page)[0]
        struct.pack_into('<HH', data, 0xBC0 + page * 4, first_id, page)
    return bytes(data) + b''.join(sectors), records


def read_bdf(data):
    result = {}
    for block in data.decode('ascii').split('STARTCHAR ')[1:]:
        lines = block.splitlines()
        name, encoding = lines[0], int(lines[1].split()[1])
        rows = lines[lines.index('BITMAP') + 1:lines.index('ENDCHAR')]
        if len(rows) != 24 or any(len(row) != 6 for row in rows):
            raise ValueError('Invalid native BDF frame')
        if name in result:
            raise ValueError('Duplicate BDF glyph name')
        result[name] = (encoding, bytes.fromhex(''.join(rows)))
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
            check.assertEqual((strike.x_ppem, strike.y_ppem), (24 * 64, 24 * 64))
            check.assertEqual(strike.height, 24)
            check.assertEqual(ft.FT_Select_Size(face, 0), 0)
            for codepoint, frame in glyphs:
                check.assertNotEqual(ft.FT_Get_Char_Index(face, codepoint), 0)
                check.assertEqual(ft.FT_Load_Char(face, codepoint, 4), 0)  # FT_LOAD_RENDER
                slot = face.contents.glyph.contents
                check.assertEqual((slot.bitmap_left, slot.bitmap_top), (0, 24))
                check.assertEqual((slot.advance.x, slot.advance.y), (24 * 64, 0))
                metrics = slot.metrics
                check.assertEqual((metrics.width, metrics.height, metrics.horiBearingX,
                                   metrics.horiBearingY, metrics.horiAdvance),
                                  (24 * 64, 24 * 64, 0, 24 * 64, 24 * 64))
                bitmap = slot.bitmap
                check.assertEqual((bitmap.width, bitmap.rows, bitmap.pixel_mode), (24, 24, 1))
                check.assertGreaterEqual(bitmap.pitch, 3)
                actual = b''.join(bytes(bitmap.buffer[y * bitmap.pitch + x] for x in range(3))
                                  for y in range(24))
                check.assertEqual(actual, frame, f'FreeType pixels differ for U+{codepoint:04X}')
        finally:
            ft.FT_Done_Face(face)
    finally:
        ft.FT_Done_FreeType(library)
    return len(glyphs)


class IBMExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.records = invented_font()
        cls.mapping, cls.han_ids = mod.gb2312_mapping()

    def test_allowlist_has_only_three_verified_fonts(self):
        actual = {(s['name'], s['size'], s['records'], s['unmapped']) for s in mod.SOURCES.values()}
        self.assertEqual(actual, {('prckt24', 345600, 7503, 59),
                                 ('prcht24', 331776, 7503, 59),
                                 ('prcfs24', 340992, 7472, 28)})
        self.assertTrue(all(len(h) == 64 for h in mod.SOURCES))

    def test_standard_gb2312_mapping_no_guessed_extensions(self):
        self.assertEqual(len(self.mapping), 7445)
        self.assertEqual(len(self.han_ids), 6763)
        for encoded in (b'\xa1\xa1', b'\xa1\xa2', b'\xb0\xa1', b'\xf7\xfe'):
            high, low = encoded
            index = 256 + (high - 0x8C) * 94 + low - 0xA1
            self.assertEqual(self.mapping[index], ord(encoded.decode('gb2312')))
        self.assertEqual(self.mapping[2230], 0x3000)
        self.assertNotIn(256, self.mapping)
        with mock.patch.object(mod, 'MAPPING_SHA256', 'incorrect'):
            with self.assertRaisesRegex(ValueError, 'mapping checksum'):
                mod.gb2312_mapping()

    def test_synthetic_font_all_records_exact_pixels(self):
        self.assertEqual(mod.decode_font(self.data), self.records)
        for record_id, frame in mod.decode_font(self.data).items():
            self.assertEqual(len(frame), 72)
            self.assertEqual(frame, invented_frame(record_id))

    def test_payload_uses_both_previous_rows_and_nibbles(self):
        rules = mod.prefix_rules(self.data[0xC0:0x1C8])
        predictor = bytearray()
        for second in range(16):
            for previous in range(16):
                nibbles = [(rank + previous + second) & 15 for rank in range(16)]
                predictor.extend(nibbles[i] * 16 + nibbles[i + 1] for i in range(0, 16, 2))
        # Code 01 is rank 1, so every residual nibble is 1.
        actual = mod.decode_payload(bytes([0x55]) * 36, rules, predictor)
        expected = bytearray(72)
        for i in range(72):
            prev1 = expected[i - 3] & 15 if i >= 3 else 0
            prev2 = expected[i - 6] & 15 if i >= 6 else 0
            nibble = (1 + prev1 + prev2) & 15
            expected[i] = 17 * nibble
        self.assertEqual(actual, bytes(expected))
        self.assertEqual(actual[:9], b'\x11' * 3 + b'\x22' * 3 + b'\x44' * 3)

    def test_long_huffman_codes_truncation_and_trailing_bytes(self):
        frame = bytes([0xEF]) * 72
        data, records = invented_font({256: frame})
        self.assertEqual(mod.decode_font(data), records)
        rules = mod.prefix_rules(data[0xC0:0x1C8])
        predictor = data[0x200:0xA00]
        for payload in (b'', b'\x80', bytes([255]) * 19):
            with self.assertRaises(ValueError):
                mod.decode_payload(payload, rules, predictor)

    def test_invalid_huffman_and_predictor_tables(self):
        for offset, value in ((0xC0, 1), (0xC1, 0), (0xC2, 0xF0), (0x1C0, 0x40), (0x200, 0)):
            changed = bytearray(self.data)
            changed[offset] = value
            with self.assertRaises(ValueError):
                mod.decode_font(changed)

    def test_invalid_headers_sizes_dimensions_and_directory(self):
        for bad in (b'', self.data[:-1], self.data[:0x1A00]):
            with self.assertRaises(ValueError):
                mod.decode_font(bad)
        for offset in (0, 16, 18, 20, 22, 24, 28, 0xA02, 0xBC0, 0xBC2):
            changed = bytearray(self.data)
            changed[offset] ^= 1
            with self.assertRaises(ValueError):
                mod.decode_font(changed)
        changed = bytearray(self.data)
        changed[0xA04:0xA08] = changed[0xA00:0xA04]
        with self.assertRaisesRegex(ValueError, 'Duplicate leaf'):
            mod.decode_font(changed)

    def test_bad_record_lengths_duplicates_and_sector_boundaries(self):
        for length in (0, 217, 255):
            changed = bytearray(self.data)
            changed[0x1A02] = length
            with self.assertRaisesRegex(ValueError, 'payload length'):
                mod.decode_font(changed)
        changed = bytearray(self.data)
        second = 0x1A00 + 3 + changed[0x1A02]
        changed[second:second + 2] = changed[0x1A00:0x1A02]
        with self.assertRaisesRegex(ValueError, 'Duplicate IBM'):
            mod.decode_font(changed)
        # A full sector of valid repeated long payload records cannot cross it.
        data, _ = invented_font({i: bytes([0xFF]) * 72 for i in range(10)})
        changed = bytearray(data)
        third = 0x1A00 + 2 * (3 + changed[0x1A02])
        changed[third:third + 3] = bytes([250, 0, 200])
        with self.assertRaisesRegex(ValueError, 'crosses sector'):
            mod.decode_font(changed)

    def test_bdf_roundtrip_preserves_unknowns_and_native_metrics(self):
        bdf = mod.make_bdf(self.records, 'prckt24')
        parsed = read_bdf(bdf)
        for index, frame in self.records.items():
            cp = self.mapping.get(index)
            name = f'uni{cp:04X}' if cp is not None else f'IBM{index:04X}'
            self.assertEqual(parsed[name], (cp if cp is not None else -1, frame))
        for line in ('SIZE 24 72 72', 'FONTBOUNDINGBOX 24 24 0 0', 'FONT_ASCENT 24',
                     'FONT_DESCENT 0', 'SWIDTH 1000 0', 'DWIDTH 24 0', 'BBX 24 24 0 0',
                     'RESOLUTION_X 72', 'RESOLUTION_Y 72', 'CHARS 3'):
            self.assertIn((line + '\n').encode(), bdf)
        self.assertIn(b'Synthetic baseline ascent/descent 24/0', bdf)
        self.assertNotIn(b'ENCODING 12288\n', bdf)
        self.assertEqual(bdf.count(b'ENCODING -1\n'), 1)

    def test_bdf_bad_names_frames_ids_and_mappings(self):
        for records in ({65535: bytes(72)}, {-1: bytes(72)}, {1: b''}, {'id': bytes(72)}):
            with self.assertRaises(ValueError):
                mod.make_bdf(records, 'prckt24')
        with self.assertRaises(ValueError):
            mod.make_bdf(self.records, 'prcst24')
        for mapping in ({256: -1}, {256: 0xD800}, {256: 0x110000}, {256: 42, 2249: 42}):
            with self.assertRaises(ValueError):
                mod.make_bdf(self.records, 'prckt24', mapping)

    def test_freetype_native_24_ppem_metrics_and_invented_pixels(self):
        bdf = mod.make_bdf(self.records, 'prckt24')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'invented.bdf'
            path.write_bytes(bdf)
            glyphs = [(self.mapping[i], raw) for i, raw in self.records.items() if i in self.mapping]
            self.assertEqual(freetype_bitmap_check(path, glyphs), 2)

    def test_missing_bad_size_bad_hash_are_read_only_no_output(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            source = Path('source.FNT')
            with self.assertRaisesRegex(ValueError, 'Missing FNT'):
                mod.export(source, 'local-research/out.bdf')
            for size in (1, 345599, 345601):
                source.write_bytes(bytes(size))
                with self.assertRaisesRegex(ValueError, 'size'):
                    mod.export(source, 'local-research/out.bdf')
            source.write_bytes(bytes(345600))
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                mod.export(source, 'local-research/out.bdf')
            self.assertFalse(Path('local-research').exists())

    def test_output_rejects_escape_existing_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            Path('local-research').mkdir()
            existing = Path('local-research/existing.bdf')
            existing.write_bytes(b'keep')
            Path('outside').mkdir()
            Path('local-research/link').symlink_to(Path('outside').absolute(), target_is_directory=True)
            Path('local-research/dangling.bdf').symlink_to(Path('absent').absolute())
            for output in ('out.bdf', '../outside.bdf', 'local-research/../outside.bdf',
                           'local-research/sub/../../escape.bdf', 'local-research/existing.bdf',
                           'local-research/link/escape.bdf', 'local-research/dangling.bdf',
                           'local-research/not-a-bdf.txt'):
                with self.assertRaises(ValueError):
                    mod.export('missing.FNT', output)
            self.assertEqual(existing.read_bytes(), b'keep')
            self.assertEqual(list(Path('outside').iterdir()), [])

    def test_input_symlinks_and_nonregular_inputs(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            Path('real').mkdir()
            Path('real/source.FNT').write_bytes(self.data)
            Path('link').symlink_to(Path('real').absolute(), target_is_directory=True)
            Path('source-link.FNT').symlink_to(Path('real/source.FNT').absolute())
            Path('dangling.FNT').symlink_to(Path('absent').absolute())
            for source in ('source-link.FNT', 'link/source.FNT', 'dangling.FNT'):
                with self.assertRaisesRegex(ValueError, 'Symbolic links'):
                    mod.load_font(source)
            if hasattr(os, 'mkfifo'):
                os.mkfifo('fifo')
                with self.assertRaisesRegex(ValueError, 'regular file'):
                    mod.load_font('fifo')
            with self.assertRaises((ValueError, OSError)):
                mod.load_font('real')

    def test_complete_synthetic_export_is_deterministic_and_preserves_input(self):
        records = {i: invented_frame(i) for i, cp in self.mapping.items() if cp != 0x3000}
        records.update({256: invented_frame(256), 257: invented_frame(257)})
        data, records = invented_font(records)
        indexed = b''.join(i.to_bytes(2, 'little') + records[i] for i in sorted(records))
        source_spec = {'name': 'prckt24', 'size': len(data), 'records': len(records),
                       'unmapped': 2, 'header_name': '楷体', 'indexed_sha256': mod.sha256(indexed)}
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            source = Path('invented.FNT')
            source.write_bytes(data)
            source.chmod(0o444)
            with mock.patch.object(mod, 'SOURCES', {mod.sha256(data): source_spec}):
                real_open = os.open
                with mock.patch.object(mod.os, 'open', wraps=real_open) as opened:
                    first = mod.export(source, 'local-research/first.bdf')
                    self.assertEqual(opened.call_args_list[0].args[1] & os.O_ACCMODE, os.O_RDONLY)
                second = mod.export(source, 'local-research/sub/second.bdf')
                with self.assertRaisesRegex(ValueError, 'never overwritten'):
                    mod.export(source, 'local-research/first.bdf')
            self.assertEqual(first, second)
            self.assertEqual(source.read_bytes(), data)
            self.assertEqual(Path('local-research/first.bdf').read_bytes(),
                             Path('local-research/sub/second.bdf').read_bytes())
            parsed = read_bdf(Path('local-research/first.bdf').read_bytes())
            self.assertEqual(len(parsed), 7446)
            self.assertEqual(sum(cp >= 0 for cp, _ in parsed.values()), 7444)
            self.assertNotIn(0x3000, [cp for cp, _ in parsed.values()])
            self.assertEqual(first['hanzi'], 6763)
            self.assertEqual(first['unmapped'], 2)

    def test_export_validation_failure_precedes_output_creation(self):
        source_spec = dict(next(iter(mod.SOURCES.values())), size=len(self.data))
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            Path('invented.FNT').write_bytes(self.data)
            with mock.patch.object(mod, 'SOURCES', {mod.sha256(self.data): source_spec}):
                with self.assertRaisesRegex(ValueError, 'record count'):
                    mod.export('invented.FNT', 'local-research/nested/out.bdf')
            self.assertFalse(Path('local-research').exists())

    def test_coverage_and_decoded_checksum_checks(self):
        records = {i: invented_frame(i) for i, cp in self.mapping.items() if cp != 0x3000}
        records[256] = invented_frame(256)
        indexed = b''.join(i.to_bytes(2, 'little') + records[i] for i in sorted(records))
        source = {'name': 'prckt24', 'size': 0, 'records': len(records), 'unmapped': 1,
                  'header_name': '楷体', 'indexed_sha256': mod.sha256(indexed)}
        mod.validate_records(self.data, records, source, self.mapping, self.han_ids)
        changed = records.copy()
        changed[2230] = bytes(72)  # U+3000 must never be fabricated.
        with self.assertRaisesRegex(ValueError, r'U\+3000'):
            mod.validate_records(self.data, changed, dict(source, records=len(changed)),
                                 self.mapping, self.han_ids)
        changed = records.copy()
        del changed[next(iter(self.han_ids))]
        with self.assertRaisesRegex(ValueError, 'coverage'):
            mod.validate_records(self.data, changed, dict(source, records=len(changed)),
                                 self.mapping, self.han_ids)
        changed = records.copy()
        changed[next(iter(self.han_ids))] = bytes(72)
        with self.assertRaisesRegex(ValueError, 'blank'):
            mod.validate_records(self.data, changed, source, self.mapping, self.han_ids)
        with self.assertRaisesRegex(ValueError, 'unmapped'):
            mod.validate_records(self.data, records, dict(source, unmapped=99),
                                 self.mapping, self.han_ids)
        changed = records.copy()
        changed[256] = bytes(72)
        with self.assertRaisesRegex(ValueError, 'bitmap checksum'):
            mod.validate_records(self.data, changed, source, self.mapping, self.han_ids)

    def test_directory_writer_rejects_symlink_swaps(self):
        with tempfile.TemporaryDirectory() as temp, working_directory(temp):
            Path('local-research').mkdir()
            Path('outside').mkdir()
            real_open = os.open
            switched = False
            def open_with_swap(path, flags, *args, **kwargs):
                nonlocal switched
                if path == 'local-research' and not switched:
                    switched = True
                    Path('local-research').rmdir()
                    Path('local-research').symlink_to(Path('outside').absolute(), target_is_directory=True)
                return real_open(path, flags, *args, **kwargs)
            with mock.patch.object(mod.os, 'open', side_effect=open_with_swap):
                with self.assertRaises(OSError):
                    mod.write_bdf(Path('local-research/out.bdf'), b'not written')
            self.assertEqual(list(Path('outside').iterdir()), [])

    def test_cli_help_missing_file_and_no_bypass_flags(self):
        with tempfile.TemporaryDirectory() as temp:
            common = [sys.executable, str(SCRIPT)]
            result = subprocess.run(common + ['--help'], cwd=temp, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0)
            self.assertIn('--font', result.stdout)
            self.assertIn('local-research', result.stdout)
            args = ['--font', 'missing.FNT', '--output', 'local-research/out.bdf']
            for python_flags in ([], ['-O']):
                result = subprocess.run([sys.executable] + python_flags + [str(SCRIPT)] + args,
                                        cwd=temp, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 1)
                self.assertIn('Missing FNT file', result.stderr)
            for extra in (['--force'], ['--skip-checksum'], ['--size', '16'], ['--allow-unknown']):
                result = subprocess.run(common + args + extra, cwd=temp, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(temp) / 'local-research').exists())


if __name__ == '__main__':
    unittest.main()
