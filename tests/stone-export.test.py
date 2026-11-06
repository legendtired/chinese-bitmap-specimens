#!/usr/bin/env python3
"""Offline synthetic and guard tests; no ROM or third-party dependencies."""
import ctypes
import ctypes.util
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/stone_ms2401h_to_bdf.py'
spec = importlib.util.spec_from_file_location('stone_export', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class StoneExportTests(unittest.TestCase):
    def test_repeat_initial_rank_and_zero_fill(self):
        lookup = bytes([7]) + bytes(255)
        self.assertEqual(mod.decode(b'\x00', lookup), bytes([7]) * 8 + bytes(120))

    def test_new_rank_and_repeat(self):
        # 1 | 000 | 1 sets rank 1, then three zero control bits repeat it.
        self.assertEqual(mod.decode(b'\x88', bytes(range(256))), bytes([1]) * 4 + bytes(124))

    def test_truncated_next_rank(self):
        # Five zero controls followed by 100: incomplete three-bit size field.
        self.assertEqual(mod.decode(b'\x04', bytes([9]) + bytes(255)), bytes([9]) * 5 + bytes(123))
        # 1|111 needs eight rank bits, but only four remain: no emitted byte.
        self.assertEqual(mod.decode(b'\xf0', bytes(range(256))), bytes(128))

    def test_empty_and_overrun(self):
        self.assertEqual(mod.decode(b'', bytes(256)), bytes(128))
        self.assertEqual(mod.decode(bytes(17), bytes(256)), bytes(128))
        with self.assertRaisesRegex(ValueError, 'overrun'):
            mod.decode(bytes(17), bytes([1]) * 256)
        with self.assertRaises(ValueError):
            mod.decode(b'', bytes(255))

    def test_column_to_row_permutation(self):
        source = bytes(range(128))
        rows = mod.row_major(source)
        self.assertEqual(rows[:8], bytes([0, 32, 64, 96, 1, 33, 65, 97]))
        self.assertEqual(rows[-4:], bytes([31, 63, 95, 127]))
        self.assertEqual(sorted(rows), list(range(128)))
        with self.assertRaises(ValueError):
            mod.row_major(b'')

    def test_gb_mapping(self):
        values = [mod.unicode_for_slot(i) for i in range(mod.SLOTS)]
        self.assertEqual(sum(v is not None for v in values), 6763)
        self.assertEqual(len(set(v for v in values if v is not None)), 6763)
        self.assertEqual([i for i, v in enumerate(values) if v is None], list(range(3755, 3760)))
        self.assertEqual(chr(values[0]), '啊')
        for bad in (-1, 6768):
            with self.assertRaises(ValueError):
                mod.unicode_for_slot(bad)

    def test_bdf_native_metrics(self):
        output = mod.make_bdf(1, [(0x4E00, bytes(range(128)))]).decode('ascii')
        for line in ['FONT_ASCENT 32', 'FONT_DESCENT 0', 'DWIDTH 32 0',
                     'BBX 32 32 0 0', 'ENCODING 19968', 'CHARS 1',
                     'SIZE 32 72 72', 'RESOLUTION_X 72', 'RESOLUTION_Y 72']:
            self.assertIn(line + '\n', output)
        font = next(line for line in output.splitlines() if line.startswith('FONT ')).split(' ', 1)[1]
        self.assertEqual(len(font.split('-')[1:]), 14)
        self.assertEqual(font.split('-')[2], 'ms2401h_style1')
        bitmap = output.split('BITMAP\n')[1].split('ENDCHAR')[0].splitlines()
        self.assertEqual(len(bitmap), 32)
        self.assertEqual(bytes.fromhex(''.join(bitmap)), bytes(range(128)))

    def test_symbol_label_does_not_alias_ascii(self):
        output = mod.make_bdf(1, [(0xFF21, bytes(128))], True).decode('ascii')
        self.assertIn('fullwidth Latin, not ASCII', output)
        self.assertIn('ENCODING 65313\n', output)
        self.assertNotIn('ENCODING 65\n', output)

    def test_symbol_descriptor_guard(self):
        sources = {name: bytes(32) for name in mod.SOURCES}
        sources['ALPS_BIOS-ST-M27C256B.BIN'] = bytes(32768)
        with self.assertRaisesRegex(ValueError, 'descriptor'):
            mod.extract_symbols(sources)

    def test_freetype_native_strike_when_available(self):
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
        library = ctypes.c_void_p()
        face = ctypes.POINTER(FaceHead)()
        ft.FT_Init_FreeType.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        ft.FT_New_Face.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long,
                                  ctypes.POINTER(ctypes.POINTER(FaceHead))]
        ft.FT_Done_Face.argtypes = [ctypes.POINTER(FaceHead)]
        ft.FT_Done_FreeType.argtypes = [ctypes.c_void_p]
        self.assertEqual(ft.FT_Init_FreeType(ctypes.byref(library)), 0)
        try:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'synthetic.bdf'
                path.write_bytes(mod.make_bdf(1, [(0x4E00, bytes(range(128)))]))
                self.assertEqual(ft.FT_New_Face(library, str(path).encode(), 0, ctypes.byref(face)), 0)
                try:
                    self.assertEqual(face.contents.num_fixed_sizes, 1)
                    strike = face.contents.available_sizes[0]
                    self.assertEqual((strike.x_ppem, strike.y_ppem), (32 * 64, 32 * 64))
                finally:
                    ft.FT_Done_Face(face)
        finally:
            ft.FT_Done_FreeType(library)

    def test_missing_and_wrong_hash_leave_no_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'out'
            with self.assertRaisesRegex(ValueError, 'missing'):
                mod.export(root, out)
            self.assertFalse(out.exists())
            name, (size, _) = next(iter(mod.SOURCES.items()))
            (root / name).write_bytes(bytes(size))
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                mod.export(root, out)
            self.assertFalse(out.exists())

    def test_existing_output_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'out'
            out.mkdir()
            sentinel = out / 'keep.txt'
            sentinel.write_text('keep')
            with self.assertRaisesRegex(ValueError, 'never overwritten'):
                mod.export(root, out)
            self.assertEqual(sentinel.read_text(), 'keep')
            link = root / 'link'
            link.symlink_to(root / 'absent')
            with self.assertRaisesRegex(ValueError, 'never overwritten'):
                mod.export(root, link)

    def test_cli_failure_and_no_force_option(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, str(SCRIPT), '--rom-dir', temp,
                                     '--output', str(Path(temp) / 'out')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('missing file', result.stderr)
            self.assertFalse((Path(temp) / 'out').exists())
        result = subprocess.run([sys.executable, str(SCRIPT), '--force'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
