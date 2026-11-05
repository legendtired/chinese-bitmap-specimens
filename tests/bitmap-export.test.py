"""Deterministic exporter tests; no font files or external dependency required."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bitmap_export', ROOT / 'scripts/bitmap_strike_to_bdf.py')
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


class NativeBitmapExportTests(unittest.TestCase):
    def test_copy_rows_and_padding(self):
        self.assertEqual(export.bitmap_rows([0xA5, 0xFF, 0xEE, 0x81, 0, 0xEE], 10, 2, 3), ['A5C0', '8100'])
        self.assertEqual(export.bitmap_rows([], 0, 0, 0), [])

    def test_reject_bad_buffer(self):
        for args in [([], 8, 1, 1), ([255], 9, 1, 1), ([255], 8, 1, -1)]:
            with self.assertRaises(ValueError):
                export.bitmap_rows(*args)

    def fake_face(self, fmt=123, pixel_mode=1):
        face = NS(selected=None, flags=[], size=NS(ascender=640, descender=-128))
        face.select_charmap = lambda c: setattr(face, 'selected', c)
        face.get_chars = lambda: iter([(65, 1), (66, 2), (0, 0)])
        bitmap = NS(width=2, rows=2, pitch=1, buffer=[0x80, 0x40], pixel_mode=pixel_mode)
        face.glyph = NS(format=fmt, bitmap=bitmap, bitmap_left=-1, bitmap_top=1, advance=NS(x=192, y=0))
        def load(index, flags):
            face.flags.append(flags)
            if index == 2:
                raise RuntimeError('No bitmap in this strike')
        face.load_glyph = load
        ft = NS(FT_ENCODING_UNICODE=42, FT_LOAD_SBITS_ONLY=16384, FT_GLYPH_FORMAT_BITMAP=123,
                FT_PIXEL_MODE_MONO=1, FT_Exception=RuntimeError)
        return face, ft

    def test_native_only_and_missing(self):
        face, ft = self.fake_face()
        glyphs, missing = export.collect_glyphs(face, ft)
        self.assertEqual(face.selected, 42)
        self.assertEqual(face.flags, [16384, 16384])
        self.assertEqual(missing, [66])
        self.assertEqual(glyphs, [{'code': 65, 'advance': 3, 'bbx': [2, 2, -1, -1], 'rows': ['80', '40']}])
        text = export.bdf_text(glyphs, 10, 10, -2, 'abc', 0, 0)
        self.assertIn('BBX 2 2 -1 -1\n', text)
        self.assertIn('DWIDTH 3 0\n', text)
        self.assertIn('FONT_ASCENT 10\nFONT_DESCENT 2', text)

    def test_control_characters_omitted(self):
        face, ft = self.fake_face()
        face.get_chars = lambda: iter([(12, 1), (65, 1), (127, 1)])
        glyphs, missing = export.collect_glyphs(face, ft)
        self.assertEqual([g['code'] for g in glyphs], [65])
        self.assertEqual(missing, [])
        self.assertEqual(face.flags, [16384])

    def test_reject_outline_or_gray(self):
        for kwargs in [{'fmt': 999}, {'pixel_mode': 2}]:
            face, ft = self.fake_face(**kwargs)
            with self.assertRaises(ValueError):
                export.collect_glyphs(face, ft)

    def test_requested_missing_character(self):
        face, ft = self.fake_face()
        _, missing = export.collect_glyphs(face, ft, {65, 67})
        self.assertEqual(missing, [67])
        self.assertEqual(face.flags, [16384])


if __name__ == '__main__':
    unittest.main()
