#!/usr/bin/env python3
"""Export verified HZK11US Han records to Unicode BDF (Python 3.9+, stdlib).

Only the pinned tomzbj source is supported. Non-Han records are deliberately
excluded because their mapping is unreliable. No network, embedded glyphs,
fallback fonts, ASCII aliases, or overwrite option. See docs/hzk11us-export.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

SOURCE_PAGE = "https://github.com/tomzbj/unicode_hzk_smlib_gen"
SOURCE_BYTES = 163790
SOURCE_SHA256 = "9caa46ecd8371415edd34b4eb7cd8645ffc93e562590b99932d67cf2cffc1f43"
SOURCE_GIT_BLOB = "30227a3aeb1ab5814f2fb67e0de8e1d6e0950123"
MAPPING_SOURCE_GIT_BLOB = "3231bd7f9e3b16e254a5e36fe9721f7b0fa61ca6"
MAPPING_SOURCE_SHA256 = "09fbf837c2bbf9dd07d45c209776aaba988fb74139ea6d3909eff9646335770f"
# Sorted Unicode scalars serialized as unsigned 16-bit big-endian integers.
MAPPING_SHA256 = "b70dd9679c0073fc2847afb0f4f328db2e5f7b95eb5b5df4c102e6affe878432"
SOURCE_RECORDS = 7445
HAN_RECORDS = 6763
WIDTH = HEIGHT = 11
ROW_BYTES = 2
STRIDE = HEIGHT * ROW_BYTES


class ConversionError(ValueError):
    """Unsupported source or inconsistent mapping/bitmap."""


def identify(data: bytes) -> None:
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != SOURCE_BYTES or digest != SOURCE_SHA256:
        raise ConversionError(
            f"输入不是已核验的 HZK11US（大小 {len(data)}，SHA-256 {digest}）。"
            "不会仅凭文件名或大小猜测格式；不支持其他 HZK11 或 HZK 文件。"
        )


def read_source(path: Path) -> bytes:
    if not path.is_file():
        raise ConversionError("输入必须是可读的本地普通文件。")
    with path.open("rb") as handle:
        data = handle.read(SOURCE_BYTES + 1)
    if len(data) > SOURCE_BYTES:
        raise ConversionError(f"输入超过已支持文件的大小 {SOURCE_BYTES} 字节。")
    identify(data)
    return data


def unicode_table():
    """Reconstruct, then pin, the author's complete sorted GB2312 mapping.

    HZK11US is NOT in GB2312 slot order. All 7445 mapped double-byte GB2312
    scalars must be sorted before looking up the 22-byte record index.
    """
    points = []
    for lead in range(0xA1, 0xFF):
        for trail in range(0xA1, 0xFF):
            code = bytes((lead, trail))
            try:
                text = code.decode("gb2312", errors="strict")
            except UnicodeDecodeError:
                continue
            if len(text) != 1 or text.encode("gb2312", errors="strict") != code:
                raise ConversionError("本机 GB2312 编码表不能严格往返核对。")
            points.append(ord(text))
    points.sort()
    if (len(points) != SOURCE_RECORDS or len(set(points)) != SOURCE_RECORDS
            or any(point > 0xFFFF for point in points)):
        raise ConversionError("本机 GB2312 映射数量或码位不符合已核验版本。")
    digest = hashlib.sha256(b"".join(point.to_bytes(2, "big") for point in points)).hexdigest()
    if digest != MAPPING_SHA256:
        raise ConversionError("本机 GB2312 映射与作者 unicode_tab 不一致，拒绝猜测索引。")
    return tuple(points)


def is_han(point: int) -> bool:
    return 0x4E00 <= point <= 0x9FFF


def bitmap_rows(raw: bytes):
    if len(raw) != STRIDE:
        raise ConversionError("字模记录必须恰为 22 字节。")
    rows = tuple(raw[offset:offset + ROW_BYTES] for offset in range(0, STRIDE, ROW_BYTES))
    if any(row[-1] & 0x1F for row in rows):
        raise ConversionError("11像素字框右侧的5个填充位非零，拒绝截断原像素。")
    return rows


def collect_glyphs(data: bytes):
    """Decode fixed-size records; the public conversion entry also pins identity."""
    if len(data) != SOURCE_BYTES:
        raise ConversionError("文件大小与已核验的7445条记录不符。")
    table = unicode_table()
    glyphs = []
    excluded_nonempty = 0
    for index, point in enumerate(table):
        raw = data[index * STRIDE:(index + 1) * STRIDE]
        if not is_han(point):
            # Do not interpret pixels or infer coverage from unreliable symbols.
            excluded_nonempty += bool(any(raw))
            continue
        rows = bitmap_rows(raw)
        if not any(raw):
            raise ConversionError(f"已核验汉字 U+{point:04X} 的记录为空，拒绝生成伪缺字。")
        glyphs.append((point, index, rows))
    if len(glyphs) != HAN_RECORDS:
        raise ConversionError("可导出汉字数量不是已核验的6763个。")
    return glyphs, excluded_nonempty


def make_bdf(glyphs) -> bytes:
    lines = [
        "STARTFONT 2.1",
        "COMMENT Han-only export; non-Han source mapping is not trusted",
        "COMMENT Original pixels preserved; source rights are unchanged",
        f"COMMENT SOURCE_SHA256 {SOURCE_SHA256}",
        "COMMENT Baseline at cell bottom is an export convention, not recovered metadata",
        "FONT -archive-hzk11ushan-medium-r-normal--11-110-72-72-c-110-iso10646-1",
        "SIZE 11 72 72",
        "FONTBOUNDINGBOX 11 11 0 0",
        "STARTPROPERTIES 6",
        "FONT_ASCENT 11",
        "FONT_DESCENT 0",
        'CHARSET_REGISTRY "ISO10646"',
        'CHARSET_ENCODING "1"',
        'SPACING "C"',
        'FAMILY_NAME "HZK11US Han"',
        "ENDPROPERTIES",
        f"CHARS {len(glyphs)}",
    ]
    for point, index, rows in glyphs:
        lines.extend((
            f"STARTCHAR U{point:04X}_IDX{index:05d}",
            f"ENCODING {point}",
            "SWIDTH 1000 0",
            "DWIDTH 11 0",
            "BBX 11 11 0 0",
            "BITMAP",
        ))
        lines.extend(row.hex().upper() for row in rows)
        lines.append("ENDCHAR")
    lines.append("ENDFONT")
    return ("\n".join(lines) + "\n").encode("ascii")


def verify_roundtrip(bdf: bytes, data: bytes, table):
    """Read every serialized glyph back and compare to its exact source record."""
    blocks = bdf.decode("ascii").split("STARTCHAR ")[1:]
    expected = [(point, index) for index, point in enumerate(table) if is_han(point)]
    if len(blocks) != len(expected):
        raise ConversionError("BDF往返核对：字符数量不一致。")
    restored = bytearray()
    try:
        for block, (point, index) in zip(blocks, expected):
            lines = block.splitlines()
            if (lines[0] != f"U{point:04X}_IDX{index:05d}"
                    or lines[1] != f"ENCODING {point}"
                    or lines[3] != "DWIDTH 11 0" or lines[4] != "BBX 11 11 0 0"):
                raise ConversionError("BDF往返核对：Unicode、记录索引或字框不一致。")
            start = lines.index("BITMAP") + 1
            rows = lines[start:start + HEIGHT]
            if any(len(row) != ROW_BYTES * 2 for row in rows) or lines[start + HEIGHT] != "ENDCHAR":
                raise ConversionError("BDF往返核对：位图行结构不一致。")
            raw = bytes.fromhex("".join(rows))
            if raw != data[index * STRIDE:(index + 1) * STRIDE]:
                raise ConversionError(f"BDF往返核对：U+{point:04X} 原字节未保留。")
            restored.extend(raw)
    except (IndexError, ValueError) as exc:
        raise ConversionError(f"BDF往返核对失败：{exc}") from exc
    return {
        "verified_glyphs": len(blocks),
        "verified_source_bytes": len(restored),
        "exported_records_sha256": hashlib.sha256(restored).hexdigest(),
        "method": "Read every BDF BITMAP back; compare all 22 bytes with its indexed source record",
    }


def convert(data: bytes):
    identify(data)
    glyphs, excluded_nonempty = collect_glyphs(data)
    bdf = make_bdf(glyphs)
    verification = verify_roundtrip(bdf, data, unicode_table())
    report = {
        "profile": "HZK11US-Han",
        "source_page": SOURCE_PAGE,
        "source_filename": "HZK11US",
        "source_bytes": len(data),
        "source_sha256": SOURCE_SHA256,
        "source_git_blob": SOURCE_GIT_BLOB,
        "mapping_source": "gen_smlib.py: unicode_tab",
        "mapping_source_git_blob": MAPPING_SOURCE_GIT_BLOB,
        "mapping_source_sha256": MAPPING_SOURCE_SHA256,
        "mapping_sha256": MAPPING_SHA256,
        "mapping_serialization": "7445 sorted Unicode scalars, unsigned 16-bit big-endian",
        "mapping": "Author table reconstructed from Python strict double-byte GB2312, then sorted and hash-checked",
        "cell_width": WIDTH,
        "cell_height": HEIGHT,
        "storage": "22 bytes per record; 11 top-to-bottom rows; 2 bytes per row, MSB-first; 5 zero right padding bits",
        "source_records": SOURCE_RECORDS,
        "exported_glyphs": len(glyphs),
        "exported_scope": "Only mapped Han within U+4E00..U+9FFF; actual range U+4E00..U+9FA0",
        "excluded_non_han_records": SOURCE_RECORDS - len(glyphs),
        "excluded_non_han_nonempty_records": excluded_nonempty,
        "exclusion_reason": "Non-Han mapping unreliable; omitted even when the record has ink; no punctuation, kana, symbols or ASCII aliases",
        "metrics": "DWIDTH=11; BBX=11,11,0,0; ascent=11; descent=0; baseline at cell bottom is an export convention, not source metadata",
        "verification": verification,
        "bdf_bytes": len(bdf),
        "bdf_sha256": hashlib.sha256(bdf).hexdigest(),
        "license_notice": "格式转换不授予原字模的使用或再分发权；来源仓库未明确提供字模授权。",
    }
    return bdf, report


def write_new_files(files) -> None:
    """Reserve every destination exclusively; never overwrite files or symlinks."""
    canonical = [path.resolve() for path, _ in files]
    if len(set(canonical)) != len(canonical):
        raise ConversionError("BDF与报告必须是不同的文件。")
    for path, _ in files:
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"拒绝覆盖已有路径：{path}")
        if not path.parent.is_dir():
            raise FileNotFoundError(f"输出目录不存在，请先创建：{path.parent}")
    created = []
    handles = []
    try:
        for path, _ in files:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created.append(path)
            handles.append(os.fdopen(fd, "wb"))
        for handle, (_, content) in zip(handles, files):
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        for handle in handles:
            handle.close()
    except BaseException:
        for handle in handles:
            handle.close()
        for path in created:
            path.unlink()
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="自行取得的已核验 HZK11US 原文件")
    parser.add_argument("--output", type=Path, help="新的 Han-only BDF；拒绝覆盖")
    parser.add_argument("--report", type=Path, help="新的 JSON 报告；默认 BDF 路径加 .json")
    parser.add_argument("--list", action="store_true", help="显示唯一支持的源文件身份")
    args = parser.parse_args(argv)
    if args.list:
        print(f"HZK11US\t11x11\tHan-only {HAN_RECORDS}\t{SOURCE_BYTES}\t{SOURCE_SHA256}")
        return 0
    if args.input is None or args.output is None:
        parser.error("需要 --input 与 --output；或单独使用 --list")
    report_path = args.report or Path(str(args.output) + ".json")
    try:
        if args.input.resolve() in (args.output.resolve(), report_path.resolve()):
            raise ConversionError("不能把输入路径用作输出。")
        bdf, report = convert(read_source(args.input))
        report_bytes = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        write_new_files([(args.output, bdf), (report_path, report_bytes)])
    except (OSError, ConversionError) as exc:
        print(f"转换失败：{exc}", file=sys.stderr)
        return 1
    print(f"已导出并逐字节核对 {report['exported_glyphs']} 个11点阵汉字。")
    print(f"BDF：{args.output}\n报告：{report_path}")
    print("仅导出汉字；全部非汉字记录均被排除，不生成ASCII或标点替代。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
