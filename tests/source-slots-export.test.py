#!/usr/bin/env python3
"""Synthetic tests by default; optional private inputs enable real round trips."""

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "source_slots_to_bdf", ROOT / "scripts" / "source_slots_to_bdf.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def parse_bdf(data, width, height):
    """Independent, deliberately small parser for the emitted BDF subset."""
    lines = data.decode("ascii").splitlines()
    assert lines[0] == "STARTFONT 2.1" and lines[-1] == "ENDFONT"
    assert 'CHARSET_REGISTRY "SOURCE.SLOT"' in lines
    assert 'CHARSET_ENCODING "0"' in lines
    assert "ISO10646" not in data.decode("ascii")
    assert "FONTBOUNDINGBOX %s %s 0 0" % (width, height) in lines
    assert "FONT_ASCENT %s" % height in lines
    assert "FONT_DESCENT 0" in lines
    properties = next(i for i, line in enumerate(lines) if line.startswith("STARTPROPERTIES "))
    count = int(lines[properties].split()[1])
    assert lines[properties + count + 1] == "ENDPROPERTIES"
    chars = next(i for i, line in enumerate(lines) if line.startswith("CHARS "))
    expected = int(lines[chars].split()[1])
    position = chars + 1
    result = []
    row_digits = ((width + 7) // 8) * 2
    while lines[position] != "ENDFONT":
        slot = len(result)
        assert lines[position] == "STARTCHAR slot%05d" % slot
        assert lines[position + 1] == "ENCODING %s" % slot
        assert lines[position + 2] == "SWIDTH %s 0" % (width * 1000 // height)
        assert lines[position + 3] == "DWIDTH %s 0" % width
        assert lines[position + 4] == "BBX %s %s 0 0" % (width, height)
        assert lines[position + 5] == "BITMAP"
        rows = lines[position + 6:position + 6 + height]
        assert len(rows) == height and all(len(row) == row_digits for row in rows)
        assert lines[position + 6 + height] == "ENDCHAR"
        result.append(bytes.fromhex("".join(rows)))
        position += 7 + height
    assert len(result) == expected
    assert position == len(lines) - 1
    return result


def srecord(kind, address=0, payload=b""):
    width = MODULE.ADDRESS_WIDTHS[kind]
    body = bytes([width + len(payload) + 1]) + address.to_bytes(width, "big") + payload
    return ("S" + kind + (body + bytes([(~sum(body)) & 255])).hex().upper() + "\n").encode("ascii")


def reference_sony(image, foreground):
    """Per-pixel oracle, avoiding the converter's integer shift rule."""
    result = []
    for page in range(32):
        for column in range(128):
            output = bytearray()
            for y in range(32):
                bit_string = "".join(format(image[page * 16384 + plane * 4096 + column * 32 + y], "08b")
                                     for plane in range(3))
                if foreground:
                    previous = "0" + bit_string[:-1]
                    bit_string = "".join("1" if a == b == "1" else "0"
                                         for a, b in zip(bit_string, previous))
                output.extend(int(bit_string, 2).to_bytes(3, "big"))
            result.append(bytes(output))
    return result


def assert_raw_bank_roundtrip(testcase, image, slots):
    rebuilt = bytearray(len(image))
    for index, bitmap in enumerate(slots):
        page, column = divmod(index, 128)
        for y in range(32):
            for plane in range(3):
                rebuilt[page * 16384 + plane * 4096 + column * 32 + y] = bitmap[y * 3 + plane]
    for page in range(32):
        start = page * 16384
        testcase.assertEqual(rebuilt[start:start + 12288], image[start:start + 12288])
    # Intentionally do not claim fourth banks can be reconstructed from BDF.


class SyntheticTests(unittest.TestCase):
    def test_hzk_full_slot_and_pixel_roundtrip(self):
        data = bytes((index * 37 ^ index >> 3) & 255
                     for index in range(MODULE.SOURCES["hzk16f"]["size"]))
        slots = MODULE.hzk_slots(data)
        parsed = parse_bdf(MODULE.make_bdf("hzk16f", slots), 16, 16)
        self.assertEqual(len(parsed), 8368)
        self.assertEqual(b"".join(parsed), data)

    def test_blank_slots_retained(self):
        slots = [bytes(32)] * 8368
        parsed = parse_bdf(MODULE.make_bdf("hzk16f", slots), 16, 16)
        self.assertEqual(parsed, slots)

    def test_hzk_rejects_incomplete_cell(self):
        for data in (b"", b"\x00" * 31, b"\x00" * 33):
            with self.assertRaises(ValueError):
                MODULE.hzk_slots(data)

    def test_sony_all_banks_and_views(self):
        image = bytes((index * 13 ^ index >> 4 ^ index >> 13) & 255
                      for index in range(MODULE.SONY_IMAGE_SIZE))
        for view in ("raw", "foreground"):
            with self.subTest(view=view):
                parsed = parse_bdf(MODULE.make_bdf("sony-g90", MODULE.sony_slots(image, view), view), 24, 32)
                self.assertEqual(len(parsed), 4096)
                self.assertEqual(parsed, reference_sony(image, view == "foreground"))
                if view == "raw":
                    assert_raw_bank_roundtrip(self, image, parsed)

    def test_foreground_truth_table_and_left_boundary(self):
        image = bytearray(MODULE.SONY_IMAGE_SIZE)
        patterns = [0b001000110000 << 12, 0xC00000, 0x018000, 0xFFFFFF]
        expected = [0b000000010000 << 12, 0x400000, 0x008000, 0x7FFFFF]
        for y, pattern in enumerate(patterns):
            for plane, value in enumerate(pattern.to_bytes(3, "big")):
                image[plane * 4096 + y] = value
        first = MODULE.sony_slots(image, "foreground")[0]
        self.assertEqual([int.from_bytes(first[y * 3:y * 3 + 3], "big") for y in range(4)], expected)

    def test_sony_rejects_wrong_buffer_or_view(self):
        with self.assertRaises(ValueError):
            MODULE.sony_slots(bytes(32))
        with self.assertRaises(ValueError):
            MODULE.sony_slots(bytes(MODULE.SONY_IMAGE_SIZE), "guess")

    def test_srecord_valid_types_counts_and_zero_fill(self):
        data = (srecord("0", payload=b"synthetic") + srecord("1", 1, b"\x80") +
                srecord("2", 3, b"\x01\x02") + srecord("3", 7, b"\xFF") +
                srecord("5", 3) + srecord("6", 3) + srecord("7") +
                srecord("8") + srecord("9"))
        self.assertEqual(MODULE.decode_srecords(data, 10), b"\x00\x80\x00\x01\x02\x00\x00\xFF\x00\x00")

    def test_srecord_rejects_checksum_count_overlap_and_range(self):
        valid = srecord("3", 0, b"\x80")
        bad_checksum = valid[:-3] + b"00\n"
        bad_count = valid[:2] + b"04" + valid[4:]
        cases = [bad_checksum, bad_count, valid + valid,
                 srecord("3", 9, b"\x01\x02"), valid + srecord("5", 2),
                 valid + srecord("7", payload=b"\x00"), b"S4030000FC\n",
                 b"\xFF", b"", b"S3\n", b"S30 500000000FA\n"]
        for data in cases:
            with self.subTest(data=data[:32]):
                with self.assertRaises(ValueError):
                    MODULE.decode_srecords(data, 10)

    def test_strict_source_size_and_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input"
            path.write_bytes(b"wrong version")
            with self.assertRaisesRegex(ValueError, "大小"):
                MODULE.read_verified(path, "hzk16f")
            path.write_bytes(bytes(MODULE.SOURCES["hzk16f"]["size"]))
            with self.assertRaisesRegex(ValueError, "SHA256"):
                MODULE.read_verified(path, "hzk16f")

    def test_export_exclusive_and_symlink_safe(self):
        synthetic = bytes(MODULE.SOURCES["hzk16f"]["size"])
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(MODULE, "read_verified", return_value=synthetic):
            output = Path(folder) / "font.bdf"
            output.write_bytes(b"keep existing file")
            with self.assertRaises(FileExistsError):
                MODULE.export("hzk16f", Path("synthetic"), output)
            link = Path(folder) / "link.bdf"
            link.symlink_to(output)
            with self.assertRaises(FileExistsError):
                MODULE.export("hzk16f", Path("synthetic"), link)
            self.assertEqual(output.read_bytes(), b"keep existing file")

    def test_export_report_and_no_accidental_unicode(self):
        synthetic = bytes(MODULE.SOURCES["hzk16f"]["size"])
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(MODULE, "read_verified", return_value=synthetic):
            output = Path(folder) / "font.bdf"
            report = MODULE.export("hzk16f", Path("synthetic"), output)
            self.assertEqual(report["slots"], 8368)
            self.assertEqual(report["blank_slots"], 8368)
            self.assertEqual(report["charset_registry"], "SOURCE.SLOT")
            self.assertEqual(report["output_sha256"], MODULE.sha256(output.read_bytes()))
            parse_bdf(output.read_bytes(), 16, 16)

    def test_reject_wrong_slot_count_and_shape(self):
        for slots in ([bytes(32)] * 8367, [bytes(31)] * 8368):
            with self.assertRaises(ValueError):
                MODULE.make_bdf("hzk16f", slots)


class RealInputTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("SOURCE_SLOT_HZK16F_INPUT"), "未提供私有 HZK16F 输入")
    def test_real_hzk_complete_roundtrip(self):
        path = Path(os.environ["SOURCE_SLOT_HZK16F_INPUT"])
        original = MODULE.read_verified(path, "hzk16f")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "hzk.bdf"
            report = MODULE.export("hzk16f", path, output)
            parsed = parse_bdf(output.read_bytes(), 16, 16)
            self.assertEqual(b"".join(parsed), original)
            self.assertEqual(report["source_sha256"], MODULE.SOURCES["hzk16f"]["sha256"])
            with self.assertRaises(FileExistsError):
                MODULE.export("hzk16f", path, output)
            self.assertEqual(MODULE.sha256(output.read_bytes()), report["output_sha256"])
            # Input=output, output symlink to input, and symlinked input aliases
            # must all fail without modifying the original private input.
            alias = Path(folder) / "input-alias"
            alias.symlink_to(path.resolve())
            for input_path, output_path in ((path, path), (path, alias),
                                             (alias, path), (alias, alias)):
                with self.subTest(input=str(input_path), output=str(output_path)):
                    with self.assertRaises(FileExistsError):
                        MODULE.export("hzk16f", input_path, output_path)
            self.assertEqual(path.read_bytes(), original)

    @unittest.skipUnless(os.environ.get("SOURCE_SLOT_SONY_INPUT"), "未提供私有 Sony 输入")
    def test_real_sony_complete_slot_roundtrip(self):
        path = Path(os.environ["SOURCE_SLOT_SONY_INPUT"])
        original = MODULE.read_verified(path, "sony-g90")
        image = MODULE.decode_srecords(original)
        self.assertEqual(MODULE.sha256(image), MODULE.SONY_IMAGE_SHA256)
        with tempfile.TemporaryDirectory() as folder:
            for view in ("raw", "foreground"):
                output = Path(folder) / (view + ".bdf")
                report = MODULE.export("sony-g90", path, output, view)
                parsed = parse_bdf(output.read_bytes(), 24, 32)
                self.assertEqual(parsed, reference_sony(image, view == "foreground"))
                if view == "raw":
                    assert_raw_bank_roundtrip(self, image, parsed)
                self.assertEqual(report["slots"], 4096)


if __name__ == "__main__":
    unittest.main()
