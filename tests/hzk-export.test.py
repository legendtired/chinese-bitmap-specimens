#!/usr/bin/env python3
"""Synthetic tests contain no real font glyphs. Optional real-input checks use HZK_TEST_SOURCE_DIR."""
import contextlib
from dataclasses import replace
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hzk_to_bdf", ROOT / "scripts" / "hzk_to_bdf.py")
hzk = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = hzk
spec.loader.exec_module(hzk)


def synthetic_profile(data, pixels=12):
    return hzk.Profile("SYNTHETIC", pixels, len(data), hashlib.sha256(data).hexdigest(), "synthetic")


class MappingTests(unittest.TestCase):
    def test_first_slot_and_space(self):
        self.assertEqual(hzk.gb_slot(0), b"\xa1\xa1")
        self.assertEqual(hzk.unicode_for_slot(0), 0x3000)

    def test_row_transition(self):
        self.assertEqual(hzk.gb_slot(93), b"\xa1\xfe")
        self.assertEqual(hzk.gb_slot(94), b"\xa2\xa1")

    def test_known_han_codepoint(self):
        self.assertEqual(hzk.unicode_for_slot((0xD2 - 0xA1) * 94 + 0xBB - 0xA1), ord("一"))

    def test_fullwidth_is_not_ascii(self):
        self.assertEqual(hzk.unicode_for_slot((0xA3 - 0xA1) * 94 + 0xC1 - 0xA1), 0xFF21)

    def test_unassigned_is_not_guessed(self):
        self.assertIsNone(hzk.unicode_for_slot(94))

    def test_out_of_range_rejected(self):
        for index in (-1, 8836):
            with self.assertRaises(hzk.ConversionError):
                hzk.gb_slot(index)


class BitmapTests(unittest.TestCase):
    def test_msb_rows_no_rotation(self):
        raw = b"\x80\x10" + b"\x40\x20" + bytes(20)
        p = synthetic_profile(raw)
        rows = hzk.bitmap_rows(raw, p)
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[:2], (b"\x80\x10", b"\x40\x20"))

    def test_padding_is_checked(self):
        for n in (12, 14):
            raw = bytes(n * 2 - 1) + b"\x01"
            with self.assertRaises(hzk.ConversionError):
                hzk.bitmap_rows(raw, synthetic_profile(raw, n))

    def test_partial_record_rejected(self):
        p = synthetic_profile(bytes(24))
        with self.assertRaises(hzk.ConversionError):
            hzk.bitmap_rows(bytes(23), p)

    def test_blank_space_kept_other_blank_skipped(self):
        raw = bytes(48)
        glyphs, report = hzk.collect_glyphs(raw, synthetic_profile(raw))
        self.assertEqual([g[0] for g in glyphs], [0x3000])
        self.assertEqual(report["empty_assigned_slots_skipped"], [{"unicode": "U+3001", "gb2312": "A1A2"}])

    def test_unmapped_occupied_slot_reported(self):
        raw = bytes(94 * 24) + b"\x80\x00" + bytes(22)
        glyphs, report = hzk.collect_glyphs(raw, synthetic_profile(raw))
        self.assertEqual(report["unmapped_nonempty_slots_skipped"], ["A2A1"])
        self.assertNotIn(None, [g[0] for g in glyphs])

    def test_bdf_preserves_cell_and_rows(self):
        raw = b"\x80\x10" + bytes(22)
        p = synthetic_profile(raw)
        glyphs, _ = hzk.collect_glyphs(raw, p)
        text = hzk.make_bdf(p, glyphs).decode("ascii")
        self.assertIn("CHARS 1\n", text)
        self.assertIn("ENCODING 12288\n", text)
        self.assertIn("BBX 12 12 0 0\nBITMAP\n8010\n", text)
        self.assertIn("DWIDTH 12 0\n", text)
        self.assertTrue(text.endswith("ENDFONT\n"))


class SafetyTests(unittest.TestCase):
    def test_unknown_same_size_rejected(self):
        with self.assertRaises(hzk.ConversionError):
            hzk.identify(bytes(hzk.PROFILES[0].size))

    def test_empty_rejected(self):
        with self.assertRaises(hzk.ConversionError):
            hzk.identify(b"")

    def test_input_size_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "oversize"
            path.write_bytes(bytes(max(p.size for p in hzk.PROFILES) + 1))
            with self.assertRaises(hzk.ConversionError):
                hzk.read_source(path)

    def test_no_overwrite_bdf_or_report(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            first, second = base / "font.bdf", base / "font.json"
            second.write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                hzk.write_new_files([(first, b"new"), (second, b"new")])
            self.assertEqual(second.read_bytes(), b"keep")
            self.assertFalse(first.exists())

    def test_same_output_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "same"
            with self.assertRaises(hzk.ConversionError):
                hzk.write_new_files([(path, b"a"), (path, b"b")])
            self.assertFalse(path.exists())

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            target, link = base / "target", base / "link"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("OS does not permit symlink creation")
            with self.assertRaises(FileExistsError):
                hzk.write_new_files([(link, b"new")])
            self.assertFalse(target.exists())

    def test_input_output_identity_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "same"
            path.write_bytes(b"original")
            with contextlib.redirect_stderr(io.StringIO()):
                result = hzk.main(["--input", str(path), "--output", str(path)])
            self.assertEqual(result, 1)
            self.assertEqual(path.read_bytes(), b"original")

    def test_exclusive_success(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder) / "a", Path(folder) / "b"
            hzk.write_new_files([(a, b"first"), (b, b"second")])
            self.assertEqual((a.read_bytes(), b.read_bytes()), (b"first", b"second"))


@unittest.skipUnless(os.environ.get("HZK_TEST_SOURCE_DIR"), "optional real HZK inputs not supplied")
class ActualInputsTests(unittest.TestCase):
    def test_all_supported_real_inputs_and_full_bdf_roundtrip(self):
        root = Path(os.environ["HZK_TEST_SOURCE_DIR"])
        for p in hzk.PROFILES:
            with self.subTest(profile=p.name):
                data, detected = hzk.read_source(root / p.name)
                self.assertEqual(detected, p)
                blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                self.assertEqual(blob, p.git_blob)
                glyphs, report = hzk.collect_glyphs(data, p)
                expected = 7439 if p.name == "HZK16" else 7445
                self.assertEqual(len(glyphs), expected)
                text = hzk.make_bdf(p, glyphs).decode("ascii")
                blocks = text.split("STARTCHAR ")[1:]
                self.assertEqual(len(blocks), expected)
                for block in blocks:
                    lines = block.splitlines()
                    slot = bytes.fromhex(lines[0].split("_GB")[1])
                    cp = int(next(line.split()[1] for line in lines if line.startswith("ENCODING ")))
                    self.assertEqual(chr(cp), slot.decode("gb2312"))
                    index = (slot[0] - 161) * 94 + slot[1] - 161
                    start = lines.index("BITMAP") + 1
                    restored = bytes.fromhex("".join(lines[start:start + p.pixels]))
                    self.assertEqual(restored, data[index * p.stride:(index + 1) * p.stride])
                self.assertNotIn(65, [g[0] for g in glyphs])
                self.assertIn(0xFF21, [g[0] for g in glyphs])

    def test_real_16f_rejected_when_available(self):
        path = Path(os.environ["HZK_TEST_SOURCE_DIR"]) / "HZK16F"
        if not path.exists():
            self.skipTest("optional excluded HZK16F input not supplied")
        with self.assertRaisesRegex(hzk.ConversionError, "繁体"):
            hzk.read_source(path)


if __name__ == "__main__":
    unittest.main()
