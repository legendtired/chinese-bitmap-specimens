#!/usr/bin/env python3
"""Export verified Sony G90 / HZK16F inputs as non-Unicode source-slot BDF.

Standard library only. No font data is bundled, downloaded, or supplemented.
See docs/source-slot-export.md for acquisition, layout, and interpretation limits.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


SOURCES = {
    "sony-g90": {
        "filename": "Tg1f0110.mot",
        "size": 1180052,
        "sha256": "1db369769fb411e50ddd0087eefe24dfe9713579ca42a2ed510f7e13a0674800",
        "width": 24,
        "height": 32,
        "slots": 4096,
    },
    "hzk16f": {
        "filename": "HZK16F",
        "size": 267776,
        "sha256": "e94400a4ac1a80f8681169324d45d39b360c7260d3157876500812c81010642b",
        "width": 16,
        "height": 16,
        "slots": 8368,
    },
}
SONY_IMAGE_SIZE = 0x80000
SONY_IMAGE_SHA256 = "def4df180acbd6f1c5c1b6886500e6c5cf9ed5cbee4cd34d7d4687be9a2faef7"
REGISTRY = "SOURCE.SLOT"
ADDRESS_WIDTHS = {"0": 2, "1": 2, "2": 3, "3": 4, "5": 2, "6": 3,
                  "7": 4, "8": 3, "9": 2}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_verified(path, kind):
    """Reject every input version other than the exact documented file."""
    source = SOURCES[kind]
    if path.stat().st_size != source["size"]:
        raise ValueError("输入大小不匹配：%s 应为 %s 字节" %
                         (source["filename"], source["size"]))
    with path.open("rb") as handle:
        data = handle.read(source["size"] + 1)
    if len(data) != source["size"] or sha256(data) != source["sha256"]:
        raise ValueError("输入 SHA256 不匹配；停止，不尝试猜测其他版本")
    return data


def decode_srecords(data, image_size=SONY_IMAGE_SIZE):
    """Validate records; zero-fill addresses absent from the S-record stream.

    Both S7 and S9 occur in the verified source, so multiple termination
    records are accepted. Conflicting or duplicate data addresses are not.
    """
    image = bytearray(image_size)
    occupied = bytearray(image_size)
    records = 0
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("S-record 必须是 ASCII 文本") from exc
    for number, line in enumerate(lines, 1):
        if (len(line) < 4 or line[0] != "S" or
                line[1] not in ADDRESS_WIDTHS or
                re.fullmatch(r"[0-9A-Fa-f]+", line[2:]) is None or
                len(line[2:]) % 2):
            raise ValueError("第 %s 行不是支持的 S-record" % number)
        record_type = line[1]
        record = bytes.fromhex(line[2:])
        width = ADDRESS_WIDTHS[record_type]
        if record[0] != len(record) - 1 or len(record) < width + 2:
            raise ValueError("第 %s 行的计数或长度不正确" % number)
        if sum(record) & 0xFF != 0xFF:
            raise ValueError("第 %s 行的 S-record 校验和不正确" % number)
        address = int.from_bytes(record[1:1 + width], "big")
        payload = record[1 + width:-1]
        if record_type in "123":
            end = address + len(payload)
            if address >= image_size or end > image_size:
                raise ValueError("第 %s 行的数据地址超出字模缓冲区" % number)
            if any(occupied[address:end]):
                raise ValueError("第 %s 行重复写入了已有数据地址" % number)
            image[address:end] = payload
            occupied[address:end] = b"\x01" * len(payload)
            records += 1
        elif record_type in "56789":
            if payload:
                raise ValueError("第 %s 行的计数/结束记录含多余数据" % number)
            if record_type in "56" and address != records:
                raise ValueError("第 %s 行的数据记录总数不一致" % number)
    if not records:
        raise ValueError("没有 S-record 数据记录")
    return bytes(image)


def sony_slots(image, view="foreground"):
    """Return all 4096 24x32 cells, row-major, MSB-first, without cropping."""
    if len(image) != SONY_IMAGE_SIZE:
        raise ValueError("Sony 字模缓冲区必须为 512 KiB")
    if view not in ("foreground", "raw"):
        raise ValueError("未知 Sony 视图")
    slots = []
    for index in range(SOURCES["sony-g90"]["slots"]):
        base = (index >> 7) * 0x4000 + (index & 127) * 32
        bitmap = bytearray()
        for y in range(32):
            row = int.from_bytes(bytes(image[base + bank * 0x1000 + y]
                                       for bank in range(3)), "big")
            if view == "foreground":
                # Inferred from MB90092, NOT measured on G90 hardware.
                # The isolated cell has a zero-valued left neighbour.
                row = row & (row >> 1)
            bitmap.extend(row.to_bytes(3, "big"))
        slots.append(bytes(bitmap))
    return slots


def hzk_slots(data):
    """Fixed 32-byte cells: 16 rows, 2 bytes/row, MSB-first."""
    if not data or len(data) % 32:
        raise ValueError("HZK16F 数据必须是非空的 32 字节槽位序列")
    return [data[offset:offset + 32] for offset in range(0, len(data), 32)]


def make_bdf(kind, slots, view="foreground"):
    source = SOURCES[kind]
    width, height = source["width"], source["height"]
    stride = (width + 7) // 8
    if len(slots) != source["slots"]:
        raise ValueError("槽位数量与所选版本不一致")
    if any(len(bitmap) != stride * height for bitmap in slots):
        raise ValueError("字模尺寸不一致")
    family = "sony_g90_" + view if kind == "sony-g90" else "hzk16f"
    lines = [
        "STARTFONT 2.1",
        "COMMENT Local source-slot export; NOT Unicode and NOT an installable TTF.",
        "COMMENT ENCODING is the zero-based source slot, not a character code.",
        "COMMENT Source file: " + source["filename"],
        "COMMENT Source SHA256: " + source["sha256"],
        "COMMENT All slots, blank cells, and full cell dimensions are retained.",
        "COMMENT Baseline is a container convention: full cell above baseline.",
        "COMMENT Original device baseline and advance metrics are not established.",
    ]
    if kind == "sony-g90":
        if view == "foreground":
            lines += [
                "COMMENT INFERRED foreground: current bit AND preceding bit; zero left neighbour.",
                "COMMENT Based on sibling MB90092, not independently hardware-verified for G90.",
                "COMMENT This view discards encoded outline/background information.",
            ]
        else:
            lines.append("COMMENT Raw pattern bits, NOT the decoded visible foreground.")
        lines += [
            "COMMENT Fourth byte banks outside the 24-pixel cells are not exported.",
            "COMMENT This BDF is not a reversible firmware backup or device-flashing image.",
        ]
    else:
        lines.append("COMMENT Traditional glyph forms occupy legacy simplified GB slots; no Unicode map assumed.")
    lines += [
        "FONT -local-%s-medium-r-normal--%s-%s-72-72-c-%s-%s-0" %
        (family, height, height * 10, width * 10, REGISTRY),
        "SIZE %s 72 72" % height,
        "FONTBOUNDINGBOX %s %s 0 0" % (width, height),
        "STARTPROPERTIES 8",
        "FONT_ASCENT %s" % height,
        "FONT_DESCENT 0",
        "PIXEL_SIZE %s" % height,
        "POINT_SIZE %s" % (height * 10),
        "RESOLUTION_X 72",
        "RESOLUTION_Y 72",
        'CHARSET_REGISTRY "%s"' % REGISTRY,
        'CHARSET_ENCODING "0"',
        "ENDPROPERTIES",
        "CHARS %s" % len(slots),
    ]
    for index, bitmap in enumerate(slots):
        lines += [
            "STARTCHAR slot%05d" % index,
            "ENCODING %s" % index,
            "SWIDTH %s 0" % (width * 1000 // height),
            "DWIDTH %s 0" % width,
            "BBX %s %s 0 0" % (width, height),
            "BITMAP",
        ]
        lines.extend(bitmap[y * stride:(y + 1) * stride].hex().upper()
                     for y in range(height))
        lines.append("ENDCHAR")
    lines.append("ENDFONT")
    return ("\n".join(lines) + "\n").encode("ascii")


def export(kind, input_path, output_path, sony_view="foreground"):
    if kind != "sony-g90" and sony_view != "foreground":
        raise ValueError("--sony-view 只适用于 sony-g90")
    data = read_verified(input_path, kind)
    if kind == "sony-g90":
        image = decode_srecords(data)
        if sha256(image) != SONY_IMAGE_SHA256:
            raise ValueError("Sony 解码缓冲区 SHA256 不匹配")
        slots = sony_slots(image, sony_view)
    else:
        slots = hzk_slots(data)
    bdf = make_bdf(kind, slots, sony_view)
    # Exclusive creation also rejects existing symlinks and input=output.
    # No force/overwrite or hash-bypass option is intentionally provided.
    with output_path.open("xb") as handle:
        handle.write(bdf)
    return {
        "kind": kind,
        "source_sha256": sha256(data),
        "output": str(output_path),
        "output_sha256": sha256(bdf),
        "charset_registry": REGISTRY,
        "charset_encoding": "0",
        "encoding_meaning": "zero-based source slot; not Unicode",
        "slots": len(slots),
        "blank_slots": sum(not any(bitmap) for bitmap in slots),
        "width": SOURCES[kind]["width"],
        "height": SOURCES[kind]["height"],
        "sony_view": sony_view if kind == "sony-g90" else None,
        "baseline": "synthetic full-cell ascent, zero descent; not a device metric",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=(
        "将已校验 Sony G90 / HZK16F 导出为 SOURCE.SLOT BDF；不是 Unicode 字库。"))
    parser.add_argument("--kind", required=True, choices=sorted(SOURCES))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sony-view", choices=("foreground", "raw"), default="foreground",
                        help="Sony: 默认 foreground 是推断前景；raw 保留原始编码图案位")
    args = parser.parse_args(argv)
    try:
        report = export(args.kind, args.input, args.output, args.sony_view)
    except (OSError, ValueError) as exc:
        print("导出失败：%s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
