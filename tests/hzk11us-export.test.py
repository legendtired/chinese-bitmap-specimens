#!/usr/bin/env python3
"""Synthetic tests embed no font glyphs; real input checks are opt-in."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hzk11us_to_bdf", ROOT / "scripts" / "hzk11us_to_bdf.py")
hzk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hzk)


def synthetic_data():
    """Artificial diagonal/edge patterns, not copied from any font."""
    raw = bytearray(hzk.SOURCE_BYTES)
    for index, point in enumerate(hzk.unicode_table()):
        if hzk.is_han(point):
            for row in range(11):
                value = (0x8000 >> ((index + row) % 11)) | 0x20
                start = index * 22 + row * 2
                raw[start:start + 2] = value.to_bytes(2, "big")
        else:
            # Even nonempty, badly padded symbols must never become glyphs.
            raw[index * 22:index * 22 + 2] = b"\xff\xff"
    return bytes(raw)


def read_bdf_records(bdf):
    records = {}
    for block in bdf.decode("ascii").split("STARTCHAR ")[1:]:
        lines = block.splitlines()
        point = int(next(line.split()[1] for line in lines if line.startswith("ENCODING ")))
        assert point not in records
        start = lines.index("BITMAP") + 1
        end = lines.index("ENDCHAR")
        assert end - start == 11
        records[point] = bytes.fromhex("".join(lines[start:end]))
    return records


class MappingTests(unittest.TestCase):
    def test_exact_table_size_fingerprint_and_order(self):
        points = hzk.unicode_table()
        self.assertEqual(len(points), 7445)
        self.assertEqual(tuple(sorted(set(points))), points)
        digest = hashlib.sha256(b"".join(p.to_bytes(2, "big") for p in points)).hexdigest()
        self.assertEqual(digest, hzk.MAPPING_SHA256)

    def test_han_scope_and_sorted_record_index(self):
        points = hzk.unicode_table()
        han = [p for p in points if hzk.is_han(p)]
        self.assertEqual(len(han), 6763)
        self.assertEqual((han[0], han[-1]), (0x4E00, 0x9FA0))
        self.assertEqual(points.index(ord("一")), 584)
        gb_index = (0xD2 - 0xA1) * 94 + 0xBB - 0xA1
        self.assertNotEqual(gb_index, points.index(ord("一")))

    def test_no_ascii_and_symbols_not_han(self):
        points = hzk.unicode_table()
        self.assertNotIn(ord("A"), points)
        for character in "，。ぁアＡ０αЯ":
            self.assertIn(ord(character), points)
            self.assertFalse(hzk.is_han(ord(character)))

    def test_mapping_fingerprint_mismatch_rejected(self):
        with mock.patch.object(hzk, "MAPPING_SHA256", "0" * 64):
            with self.assertRaisesRegex(hzk.ConversionError, "unicode_tab"):
                hzk.unicode_table()


class BitmapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = synthetic_data()
        cls.table = hzk.unicode_table()

    def test_rows_msb_order_and_right_edge_preserved(self):
        raw = b"\x80\x20\x40\x00" + bytes(18)
        rows = hzk.bitmap_rows(raw)
        self.assertEqual(len(rows), 11)
        self.assertEqual(rows[:2], (b"\x80\x20", b"\x40\x00"))
        self.assertEqual(b"".join(rows), raw)

    def test_all_five_padding_bits_rejected(self):
        for bit in range(5):
            with self.subTest(bit=bit), self.assertRaises(hzk.ConversionError):
                hzk.bitmap_rows(bytes(21) + bytes((1 << bit,)))

    def test_partial_or_oversize_record_rejected(self):
        for size in (0, 21, 23):
            with self.subTest(size=size), self.assertRaises(hzk.ConversionError):
                hzk.bitmap_rows(bytes(size))

    def test_only_han_exported_and_nonhan_untouched(self):
        glyphs, nonempty = hzk.collect_glyphs(self.data)
        self.assertEqual(len(glyphs), 6763)
        self.assertEqual(nonempty, 682)
        self.assertTrue(all(hzk.is_han(p) for p, _, _ in glyphs))
        self.assertEqual([p for p, _, _ in glyphs], sorted(p for p, _, _ in glyphs))

    def test_empty_han_is_an_error_not_a_filled_missing_glyph(self):
        data = bytearray(self.data)
        index = self.table.index(ord("一"))
        data[index * 22:(index + 1) * 22] = bytes(22)
        with self.assertRaisesRegex(hzk.ConversionError, "为空"):
            hzk.collect_glyphs(bytes(data))

    def test_partial_file_rejected(self):
        with self.assertRaises(hzk.ConversionError):
            hzk.collect_glyphs(self.data[:-1])

    def test_all_exported_bytes_roundtrip_and_metrics(self):
        glyphs, _ = hzk.collect_glyphs(self.data)
        bdf = hzk.make_bdf(glyphs)
        text = bdf.decode("ascii")
        self.assertIn("CHARS 6763\n", text)
        self.assertIn("FONTBOUNDINGBOX 11 11 0 0\n", text)
        self.assertIn("FONT_ASCENT 11\nFONT_DESCENT 0\n", text)
        self.assertIn("Baseline at cell bottom is an export convention", text)
        font_line = next(line for line in text.splitlines() if line.startswith("FONT "))
        self.assertEqual(len(font_line.split()[1].split("-")), 15)
        records = read_bdf_records(bdf)
        self.assertEqual(len(records), 6763)
        for point, index, _ in glyphs:
            self.assertEqual(records[point], self.data[index * 22:(index + 1) * 22])
        result = hzk.verify_roundtrip(bdf, self.data, self.table)
        self.assertEqual(result["verified_glyphs"], 6763)
        self.assertEqual(result["verified_source_bytes"], 148786)

    def test_roundtrip_rejects_altered_encoding_pixels_and_count(self):
        glyphs, _ = hzk.collect_glyphs(self.data)
        bdf = hzk.make_bdf(glyphs)
        first_row = glyphs[0][2][0].hex().upper().encode()
        variants = (
            bdf.replace(b"ENCODING 19968\n", b"ENCODING 19969\n", 1),
            bdf.replace(b"BITMAP\n" + first_row, b"BITMAP\n0000", 1),
            bdf[:bdf.index(b"STARTCHAR ")],
        )
        for altered in variants:
            with self.assertRaises(hzk.ConversionError):
                hzk.verify_roundtrip(altered, self.data, self.table)


class SafetyTests(unittest.TestCase):
    def test_same_size_unverified_file_rejected_by_public_entry(self):
        with self.assertRaises(hzk.ConversionError):
            hzk.convert(bytes(hzk.SOURCE_BYTES))

    def test_empty_rejected(self):
        with self.assertRaises(hzk.ConversionError):
            hzk.identify(b"")

    def test_input_size_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "oversize"
            path.write_bytes(bytes(hzk.SOURCE_BYTES + 1))
            with self.assertRaisesRegex(hzk.ConversionError, "超过"):
                hzk.read_source(path)

    def test_no_overwrite_either_output(self):
        for existing_index in (0, 1):
            with tempfile.TemporaryDirectory() as folder:
                paths = [Path(folder) / "font.bdf", Path(folder) / "font.json"]
                paths[existing_index].write_bytes(b"keep")
                with self.assertRaises(FileExistsError):
                    hzk.write_new_files([(path, b"new") for path in paths])
                self.assertEqual(paths[existing_index].read_bytes(), b"keep")
                self.assertFalse(paths[1 - existing_index].exists())

    def test_same_output_path_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "same"
            with self.assertRaises(hzk.ConversionError):
                hzk.write_new_files([(path, b"a"), (path, b"b")])
            self.assertFalse(path.exists())

    def test_dangling_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target, link = Path(folder) / "target", Path(folder) / "link"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("OS does not permit symlink creation")
            with self.assertRaises(FileExistsError):
                hzk.write_new_files([(link, b"new")])
            self.assertFalse(target.exists())

    def test_missing_output_parent_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "font.bdf"
            second = Path(folder) / "missing" / "report.json"
            with self.assertRaises(FileNotFoundError):
                hzk.write_new_files([(first, b"a"), (second, b"b")])
            self.assertFalse(first.exists())

    def test_exclusive_creation_race_cleans_only_own_file(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / "first", Path(folder) / "second"
            real_open = os.open

            def competing_open(path, flags, mode):
                if path == second:
                    second.write_bytes(b"other writer")
                return real_open(path, flags, mode)

            with mock.patch.object(hzk.os, "open", side_effect=competing_open):
                with self.assertRaises(FileExistsError):
                    hzk.write_new_files([(first, b"a"), (second, b"b")])
            self.assertFalse(first.exists())
            self.assertEqual(second.read_bytes(), b"other writer")

    def test_input_cannot_be_bdf_or_report(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input"
            path.write_bytes(b"original")
            for extra in (["--output", str(path)], ["--output", str(path) + ".bdf", "--report", str(path)]):
                with contextlib.redirect_stderr(io.StringIO()):
                    status = hzk.main(["--input", str(path)] + extra)
                self.assertEqual(status, 1)
                self.assertEqual(path.read_bytes(), b"original")

    def test_successful_exclusive_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / "font", Path(folder) / "report"]
            hzk.write_new_files([(paths[0], b"a"), (paths[1], b"b")])
            self.assertEqual([p.read_bytes() for p in paths], [b"a", b"b"])

    def test_write_failure_removes_only_new_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / "font", Path(folder) / "report"]
            with mock.patch.object(hzk.os, "fsync", side_effect=OSError("simulated storage failure")):
                with self.assertRaises(OSError):
                    hzk.write_new_files([(path, b"new") for path in paths])
            self.assertFalse(any(path.exists() for path in paths))

    def test_list_needs_no_input(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(hzk.main(["--list"]), 0)
        self.assertIn(hzk.SOURCE_SHA256, output.getvalue())
        self.assertIn("Han-only 6763", output.getvalue())

    def test_unknown_cli_input_creates_no_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "input", Path(folder) / "output.bdf"
            source.write_bytes(bytes(hzk.SOURCE_BYTES))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(hzk.main(["--input", str(source), "--output", str(output)]), 1)
            self.assertFalse(output.exists())
            self.assertFalse(Path(str(output) + ".json").exists())


@unittest.skipUnless(os.environ.get("HZK11US_TEST_INPUT"), "optional verified HZK11US not supplied")
class ActualInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(os.environ["HZK11US_TEST_INPUT"])
        cls.data = hzk.read_source(cls.path)
        cls.bdf, cls.report = hzk.convert(cls.data)

    def test_source_identity_and_full_byte_roundtrip(self):
        blob = hashlib.sha1(b"blob " + str(len(self.data)).encode() + b"\0" + self.data).hexdigest()
        self.assertEqual(blob, hzk.SOURCE_GIT_BLOB)
        records = read_bdf_records(self.bdf)
        table = hzk.unicode_table()
        expected = [point for point in table if hzk.is_han(point)]
        self.assertEqual(sorted(records), expected)
        for point, raw in records.items():
            index = table.index(point)
            self.assertEqual(raw, self.data[index * 22:(index + 1) * 22])
            self.assertTrue(any(raw))
            self.assertTrue(all(raw[row * 2 + 1] & 0x1F == 0 for row in range(11)))
        self.assertEqual(self.report["excluded_non_han_records"], 682)
        self.assertEqual(self.report["excluded_non_han_nonempty_records"], 661)
        self.assertEqual(self.report["verification"]["verified_source_bytes"], 148786)

    def test_author_mapping_without_executing_source(self):
        value = os.environ.get("HZK11US_TEST_MAPPING_SOURCE")
        if not value:
            self.skipTest("optional author gen_smlib.py not supplied")
        source = Path(value).read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), hzk.MAPPING_SOURCE_SHA256)
        tree = ast.parse(source.decode("utf-8"))
        tables = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                  and any(getattr(target, "id", "") == "unicode_tab" for target in node.targets)]
        self.assertEqual(len(tables), 1)
        self.assertEqual(tuple(tables[0]), hzk.unicode_table())

    def test_catalog_sample_pixels_from_bdf(self):
        value = os.environ.get("HZK11US_TEST_SPECIMEN")
        if not value:
            self.skipTest("optional catalog specimen not supplied")
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow required only for optional PNG comparison")
        path = Path(value)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         "e36a4ddc048c8e62ff0dfa89fe408f14333e9c9904430b43e576febe545b7522")
        with Image.open(path) as image:
            image = image.convert("RGBA")
            self.assertEqual(image.size, (132, 11))
            alpha = list(image.getchannel("A").tobytes())
        records = read_bdf_records(self.bdf)
        text = "视野无限广，窗外有蓝天。"
        pixels = []
        for y in range(11):
            for char in text:
                raw = records.get(ord(char), bytes(22))
                row = int.from_bytes(raw[y * 2:y * 2 + 2], "big")
                pixels.extend(255 if row & (1 << (15 - x)) else 0 for x in range(11))
        self.assertEqual(pixels, alpha)
        self.assertEqual(sum(bool(p) for p in pixels), 467)
        self.assertNotIn(ord("，"), records)
        self.assertNotIn(ord("。"), records)

    def test_cli_outputs_report_and_refuses_second_run(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "han.bdf"
            args = ["--input", str(self.path), "--output", str(output)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(hzk.main(args), 0)
            self.assertEqual(output.read_bytes(), self.bdf)
            report = json.loads(Path(str(output) + ".json").read_text())
            self.assertEqual(report, self.report)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(hzk.main(args), 1)
            self.assertEqual(output.read_bytes(), self.bdf)

    def test_changed_byte_rejected(self):
        altered = bytearray(self.data)
        altered[0] ^= 0x80
        with self.assertRaises(hzk.ConversionError):
            hzk.convert(bytes(altered))


if __name__ == "__main__":
    unittest.main()
