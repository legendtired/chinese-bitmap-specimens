#!/usr/bin/env python3
"""No bundled font data. Set ELISA_SOURCE to enable actual-source regressions."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("elisa_to_bdf", ROOT / "scripts/elisa_to_bdf.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class GuardAndMappingTests(unittest.TestCase):
    def test_mapping_ideographic_space(self):
        self.assertEqual(m.jis_to_unicode(0x2121), 0x3000)

    def test_mapping_fullwidth_zero(self):
        self.assertEqual(m.jis_to_unicode(0x2330), ord("０"))

    def test_strict_jis_wave_dash_not_cp932(self):
        self.assertEqual(m.jis_to_unicode(0x2141), 0x301C)

    def test_non_jis_codes_rejected(self):
        for code in [-1, 0x20, 0x2021, 0x217F, 0x8121, 0xA1A1]:
            with self.subTest(code=code), self.assertRaises(ValueError):
                m.jis_to_unicode(code)

    def test_unassigned_jis_rejected(self):
        with self.assertRaises(ValueError):
            m.jis_to_unicode(0x222F)

    def test_unknown_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "unknown.bdf"
            p.write_bytes(b"STARTFONT 2.1\nENDFONT\n")
            with self.assertRaises(ValueError):
                m.read_verified_source(p)
            with self.assertRaises(ValueError):
                m.convert_bdf(p.read_bytes())

    def test_oversized_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "large"
            with p.open("wb") as f:
                f.truncate(m.SOURCE_SIZE + 1)
            with self.assertRaises(ValueError):
                m.read_verified_source(p)

    def test_refuse_output_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p, r = Path(d) / "out", Path(d) / "report"
            p.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                m.write_outputs(p, r, b"new", {})
            self.assertEqual(p.read_bytes(), b"original")
            self.assertFalse(r.exists())

    def test_refuse_report_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p, r = Path(d) / "out", Path(d) / "report"
            r.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                m.write_outputs(p, r, b"new", {})
            self.assertEqual(r.read_bytes(), b"original")
            self.assertFalse(p.exists())

    def test_refuse_same_path(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "out"
            with self.assertRaises(ValueError):
                m.write_outputs(p, p, b"new", {})
            self.assertFalse(p.exists())

    def test_missing_report_parent_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            p, r = Path(d) / "out", Path(d) / "missing/report"
            with self.assertRaises(ValueError):
                m.write_outputs(p, r, b"new", {})
            self.assertFalse(p.exists())

    def test_missing_output_parent_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            p, r = Path(d) / "missing/out", Path(d) / "report"
            with self.assertRaises(ValueError):
                m.write_outputs(p, r, b"new", {})
            self.assertFalse(r.exists())

    def test_input_output_collision(self):
        with tempfile.TemporaryDirectory() as d:
            p, r = Path(d) / "input", Path(d) / "report"
            p.write_bytes(b"original")
            with self.assertRaises(ValueError):
                m.preflight_outputs(p, r, p)
            self.assertEqual(p.read_bytes(), b"original")

    def test_resolved_directory_alias_collision(self):
        with tempfile.TemporaryDirectory() as d:
            link = Path(d) / "link"
            try:
                link.symlink_to(Path(d), target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks not available")
            with self.assertRaises(ValueError):
                m.write_outputs(Path(d) / "out", link / "out", b"new", {})
            self.assertFalse((Path(d) / "out").exists())

    def test_rollback_removes_only_owned_output(self):
        with tempfile.TemporaryDirectory() as d:
            p, r = Path(d) / "out", Path(d) / "report"
            original_open = Path.open
            def failing_open(path, *args, **kwargs):
                if path == r:
                    raise OSError("simulated report open failure")
                return original_open(path, *args, **kwargs)
            with mock.patch.object(Path, "open", failing_open), self.assertRaises(OSError):
                m.write_outputs(p, r, b"new", {})
            self.assertFalse(p.exists())
            self.assertFalse(r.exists())

    def test_rollback_preserves_replaced_output(self):
        with tempfile.TemporaryDirectory() as d:
            p, r, replacement = [Path(d) / n for n in ["out", "report", "replacement"]]
            replacement.write_bytes(b"other process output")
            original_open = Path.open
            def failing_open(path, *args, **kwargs):
                if path == r:
                    replacement.replace(p)
                    raise OSError("simulated concurrent replacement")
                return original_open(path, *args, **kwargs)
            with mock.patch.object(Path, "open", failing_open), self.assertRaises(OSError):
                m.write_outputs(p, r, b"new", {})
            self.assertEqual(p.read_bytes(), b"other process output")
            self.assertFalse(r.exists())

    def test_refuse_dangling_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p, r = Path(d) / "out", Path(d) / "report"
            try:
                p.symlink_to(Path(d) / "missing")
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks not available")
            with self.assertRaises(FileExistsError):
                m.write_outputs(p, r, b"new", {})
            self.assertTrue(p.is_symlink())
            self.assertFalse(r.exists())

    def test_cli_guard_leaves_no_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            p, o = Path(d) / "wrong", Path(d) / "out.bdf"
            p.write_bytes(b"not the source")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/elisa_to_bdf.py"), "--source", str(p), "--output", str(o)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"Unverified input", result.stderr)
            self.assertFalse(o.exists())
            self.assertFalse(Path(str(o) + ".json").exists())


def independently_parse(text):
    glyphs = {}
    for block in text.split("STARTCHAR ")[1:]:
        lines = block.split("ENDCHAR", 1)[0].splitlines()
        encoding = int(next(x.split()[1] for x in lines if x.startswith("ENCODING ")))
        bbx = tuple(map(int, next(x[4:] for x in lines if x.startswith("BBX ")).split()))
        rows = tuple(int(x, 16) for x in lines[lines.index("BITMAP") + 1:])
        glyphs[encoding] = (bbx, rows)
    return glyphs


@unittest.skipUnless(os.environ.get("ELISA_SOURCE"), "Set ELISA_SOURCE for real-input tests; no font is bundled")
class ActualSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.environ["ELISA_SOURCE"])
        cls.data, cls.kind, cls.digest = m.read_verified_source(cls.source)
        cls.output, cls.report = m.convert_bdf(cls.data)
        cls.glyphs = independently_parse(cls.output.decode("ascii"))

    def test_exact_catalog_source(self):
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), m.SOURCE_SHA256)

    def test_all_glyphs_preserve_rows_and_bearing(self):
        source_glyphs = independently_parse(self.data.decode("ascii"))
        self.assertEqual(len(self.glyphs), 6877)
        # Verify mappings through EUC-JP, independently of the export function.
        for jis, record in source_glyphs.items():
            euc = bytes([(jis >> 8) | 0x80, (jis & 0xFF) | 0x80])
            self.assertEqual(self.glyphs[ord(euc.decode("euc_jp"))], record)
        self.assertEqual(len(set(self.glyphs)), 6877)

    def test_output_header(self):
        text = self.output.decode("ascii")
        for expected in ['FONTBOUNDINGBOX 10 8 0 -2', 'FONT_ASCENT 6', 'FONT_DESCENT 2', 'PIXEL_SIZE 10', 'SIZE 10 75 75', 'DEFAULT_CHAR 12288', 'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"']:
            self.assertIn(expected + "\n", text)
        self.assertEqual(text.count("DWIDTH 10 0\n"), 6877)
        self.assertEqual(text.count("SWIDTH 823 0\n"), 6877)
        self.assertIn('COPYRIGHT "Copyright 1993,1994,1995 (C) by ELISA FONT PJ all rights reserved."', text)

    def test_coverage_and_missing(self):
        for char in m.SAMPLE_HAN + m.SAMPLE_FULLWIDTH:
            self.assertIn(ord(char), self.glyphs)
        for char in "视蓝凜熙ABC012":
            self.assertNotIn(ord(char), self.glyphs)
        self.assertEqual(self.report["blank_glyphs"], ["U+3000"])
        self.assertEqual(self.report["ascii_codepoints_present"], 0)

    def test_deterministic_output(self):
        self.assertEqual(m.convert_bdf(self.data), (self.output, self.report))
        self.assertEqual(self.report["output_sha256"], hashlib.sha256(self.output).hexdigest())

    def test_source_change_rejected(self):
        with self.assertRaises(ValueError):
            m.convert_bdf(self.data[:-1] + b"!")

    def test_cli_success_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "out.bdf"
            args = ["--source", str(self.source), "--output", str(p)]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(args), 0)
                self.assertEqual(m.main(args), 1)
            self.assertEqual(p.read_bytes(), self.output)
            report = json.loads(Path(str(p) + ".json").read_text())
            self.assertEqual(report["input_sha256"], self.digest)

    def test_catalog_pixels_exact(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is required only for specimen pixel validation")
        root = Path(os.environ.get("ELISA_CATALOG_ROOT", ROOT))
        catalog_path = root / "data/catalog.json"
        if not catalog_path.is_file():
            self.skipTest("Set ELISA_CATALOG_ROOT to the catalog checkout")
        entry = next(x for x in json.loads(catalog_path.read_text()) if x["id"] == "elisa_8_native")
        specimen = root / entry["specimen"]
        self.assertEqual(hashlib.sha256(specimen.read_bytes()).hexdigest(), entry["specimenSha256"])
        self.assertEqual(entry["nativeEvidence"]["source_sha256"], m.SOURCE_SHA256)
        actual = Image.new("RGBA", (200, 20), (0, 0, 0, 0))
        for line, text in enumerate([entry["text"], entry["asciiText"]]):
            for i, char in enumerate(text):
                bbx, rows = self.glyphs[ord(char)]
                self.assertEqual(bbx, (10, 8, 0, -2))
                for y, row in enumerate(rows):
                    for x in range(10):
                        if row & (1 << (15 - x)):
                            actual.putpixel((i * 10 + x, line * 12 + y), (17, 17, 17, 255))
        expected = Image.open(specimen).convert("RGBA")
        self.assertEqual(actual.size, expected.size)
        self.assertEqual(actual.tobytes(), expected.tobytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
