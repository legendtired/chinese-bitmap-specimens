#!/usr/bin/env python3
"""Convert eight verified aguegu/BitmapFont HZK files to Unicode BDF.

Python 3.9+; standard library only. No downloads, embedded glyph data, guessed
layouts, ASCII aliases, or overwrite option. See docs/hzk-export.md for the boundary.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import List, Tuple

SOURCE = "https://github.com/aguegu/BitmapFont/tree/master/font"


@dataclass(frozen=True)
class Profile:
    name: str
    pixels: int
    size: int
    sha256: str
    git_blob: str

    @property
    def row_bytes(self) -> int:
        return (self.pixels + 7) // 8

    @property
    def stride(self) -> int:
        return self.row_bytes * self.pixels


PROFILES = (
    Profile("HZK12", 12, 196272, "d83b7f1603e87dd68bebc3a6a159c57909779684188cba790146f59424c28a02", "877acf27cf08376ec3635c9f9603554d70d67734"),
    Profile("HZK14", 14, 228984, "aa393fb0402103e332b5a208b0207e310fdd29a90b99ec96c243d8ef22715848", "f71039c8d353431c25f99aa0a598e4e7ee18e14a"),
    Profile("HZK16", 16, 267616, "0a757c641b211419868af188f4a90b2010fcd7620373073a8bc7c1dd848eefdf", "8661219da1c56b74e7151fe78789121816537027"),
    Profile("HZK16S", 16, 261696, "c23b84cb16e7a2b3973b9034082c5f66950663c6490d7bb51df16232c9a08dea", "4101214b42edbcaf052d7a6da573cc28dc3957aa"),
    Profile("HZK24F", 24, 600048, "f20d9d3b84dd54dd4e8c21a65b21c8fee48027671379939212bd314945501073", "41022700c4d5d75cba0d00de1423c8bc338331f0"),
    Profile("HZK24H", 24, 600048, "4ba303f31a483739535e74b0ce5599f8701e85e044492a245ae7581d4c647750", "5e3382eea72a6367376365af7b2ada37a8503719"),
    Profile("HZK24K", 24, 600048, "49b073be075cc6c5f11cc4f00c837ba607cfe52c3ebd06fb37708c9785bdb9c9", "a2be03b8f7b01c6422134beaf7bc27051135b209"),
    Profile("HZK24S", 24, 600048, "5e655cc1cb2b6d2250906b1bfd9c9f1005e8f82a9393fc4dd383b2c9953b9f27", "56e4a83ea06f4c5aff046ae480fe40350b0c8461"),
)
HZK16F_SHA256 = "e94400a4ac1a80f8681169324d45d39b360c7260d3157876500812c81010642b"


class ConversionError(ValueError):
    """Unsupported or structurally inconsistent input."""


def identify(data: bytes) -> Profile:
    digest = hashlib.sha256(data).hexdigest()
    if digest == HZK16F_SHA256:
        raise ConversionError("HZK16F 在 GB2312 槽位存繁体字形，不能安全地直接映射 Unicode；本脚本不支持。")
    for profile in PROFILES:
        if digest == profile.sha256 and len(data) == profile.size:
            return profile
    raise ConversionError(
        f"输入不是已核验版本（大小 {len(data)}，SHA-256 {digest}）。"
        "不会仅凭文件名或大小猜测字模格式。"
    )


def read_source(path: Path) -> Tuple[bytes, Profile]:
    # Bound memory even for an accidentally supplied image/ROM/archive.
    limit = max(p.size for p in PROFILES)
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ConversionError(f"输入超过已支持文件的最大大小 {limit} 字节。")
    return data, identify(data)


def gb_slot(index: int) -> bytes:
    if not 0 <= index < 94 * 94:
        raise ConversionError(f"HZK 槽位越界：{index}")
    return bytes((0xA1 + index // 94, 0xA1 + index % 94))


def unicode_for_slot(index: int):
    code = gb_slot(index)
    try:
        text = code.decode("gb2312", errors="strict")
    except UnicodeDecodeError:
        return None
    if len(text) != 1 or text.encode("gb2312", errors="strict") != code:
        raise ConversionError(f"GB2312 码位不能往返核对：{code.hex().upper()}")
    return ord(text)


def bitmap_rows(raw: bytes, profile: Profile) -> Tuple[bytes, ...]:
    if len(raw) != profile.stride:
        raise ConversionError("字模记录长度不完整。")
    rows = tuple(raw[i:i + profile.row_bytes] for i in range(0, len(raw), profile.row_bytes))
    padding = profile.row_bytes * 8 - profile.pixels
    if padding and any(row[-1] & ((1 << padding) - 1) for row in rows):
        raise ConversionError("字框右侧填充位非零，不能无损导出已声明的字宽。")
    return rows


def collect_glyphs(data: bytes, profile: Profile):
    if len(data) != profile.size or len(data) % profile.stride:
        raise ConversionError("文件大小与字模记录长度不符。")
    count = len(data) // profile.stride
    if count > 94 * 94:
        raise ConversionError("记录数量超过 GB2312 区位表范围。")
    glyphs = []
    empty = []
    unmapped_nonempty = []
    unmapped_count = 0
    seen = set()
    for index in range(count):
        raw = data[index * profile.stride:(index + 1) * profile.stride]
        rows = bitmap_rows(raw, profile)
        codepoint = unicode_for_slot(index)
        slot = gb_slot(index).hex().upper()
        if codepoint is None:
            unmapped_count += 1
            if any(raw):
                unmapped_nonempty.append(slot)
            continue
        if codepoint in seen:
            raise ConversionError(f"重复 Unicode 码位：U+{codepoint:04X}")
        seen.add(codepoint)
        # Keep the source ideographic space, but never invent blank missing glyphs.
        if not any(raw) and codepoint != 0x3000:
            empty.append({"unicode": f"U+{codepoint:04X}", "gb2312": slot})
            continue
        glyphs.append((codepoint, slot, rows))
    glyphs.sort(key=lambda glyph: glyph[0])
    report = {
        "profile": profile.name,
        "source_page": SOURCE,
        "source_bytes": len(data),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "source_git_blob": profile.git_blob,
        "cell_width": profile.pixels,
        "cell_height": profile.pixels,
        "storage": "row-major, top-to-bottom, left-to-right, MSB-first; zero right padding",
        "source_slots": count,
        "exported_glyphs": len(glyphs),
        "encoding": "Unicode via Python strict GB2312; no ASCII or traditional aliases",
        "empty_assigned_slots_skipped": empty,
        "unmapped_slots_skipped": unmapped_count,
        "unmapped_nonempty_slots_skipped": unmapped_nonempty,
        "metrics": "fixed cell; DWIDTH=cell_width; BBX offset 0,0; ascent=height; descent=0; no source baseline supplied",
        "license_notice": "格式转换不授予历史字模的使用或再分发权；原仓库工具代码许可不等于字模授权。",
    }
    return glyphs, report


def make_bdf(profile: Profile, glyphs) -> bytes:
    n = profile.pixels
    lines = [
        "STARTFONT 2.1",
        "COMMENT Pixel-preserving export; source rights are unchanged",
        f"COMMENT SOURCE_SHA256 {profile.sha256}",
        "COMMENT Baseline at cell bottom is an export convention, not recovered metadata",
        f"FONT -archive-{profile.name.lower()}-medium-r-normal--{n}-{n * 10}-72-72-c-{n * 10}-iso10646-1",
        f"SIZE {n} 72 72",
        f"FONTBOUNDINGBOX {n} {n} 0 0",
        "STARTPROPERTIES 6",
        f"FONT_ASCENT {n}",
        "FONT_DESCENT 0",
        'CHARSET_REGISTRY "ISO10646"',
        'CHARSET_ENCODING "1"',
        'SPACING "C"',
        f'FAMILY_NAME "{profile.name}"',
        "ENDPROPERTIES",
        f"CHARS {len(glyphs)}",
    ]
    for codepoint, slot, rows in glyphs:
        lines.extend((
            f"STARTCHAR U{codepoint:04X}_GB{slot}",
            f"ENCODING {codepoint}",
            "SWIDTH 1000 0",
            f"DWIDTH {n} 0",
            f"BBX {n} {n} 0 0",
            "BITMAP",
        ))
        lines.extend(row.hex().upper() for row in rows)
        lines.append("ENDCHAR")
    lines.append("ENDFONT")
    return ("\n".join(lines) + "\n").encode("ascii")


def write_new_files(files: List[Tuple[Path, bytes]]) -> None:
    """Exclusive creates also reject symlinks; clean only files this call created."""
    canonical = [path.resolve() for path, _ in files]
    if len(set(canonical)) != len(canonical):
        raise ConversionError("BDF 与报告必须是不同的文件。")
    for path, _ in files:
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"拒绝覆盖已有路径：{path}")
        if not path.parent.is_dir():
            raise FileNotFoundError(f"输出目录不存在，请先创建：{path.parent}")
    created = []
    handles = []
    try:
        # Reserve every name before writing any bytes. O_EXCL makes the check race-safe.
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
    parser.add_argument("--input", type=Path, help="自行取得的原 HZK 文件")
    parser.add_argument("--output", type=Path, help="新 BDF 文件；拒绝覆盖")
    parser.add_argument("--report", type=Path, help="新 JSON 报告，默认 BDF 路径加 .json")
    parser.add_argument("--list", action="store_true", help="列出支持的精确版本")
    args = parser.parse_args(argv)
    if args.list:
        for p in PROFILES:
            print(f"{p.name}\t{p.pixels}x{p.pixels}\t{p.size}\t{p.sha256}")
        return 0
    if args.input is None or args.output is None:
        parser.error("需要 --input 与 --output；或单独使用 --list")
    report_path = args.report or Path(str(args.output) + ".json")
    try:
        if args.input.resolve() in (args.output.resolve(), report_path.resolve()):
            raise ConversionError("不能把输入路径用作输出。")
        data, profile = read_source(args.input)
        glyphs, report = collect_glyphs(data, profile)
        bdf = make_bdf(profile, glyphs)
        report["bdf_sha256"] = hashlib.sha256(bdf).hexdigest()
        report["bdf_bytes"] = len(bdf)
        report_bytes = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        write_new_files([(args.output, bdf), (report_path, report_bytes)])
    except (OSError, ConversionError) as exc:
        print(f"转换失败：{exc}", file=sys.stderr)
        return 1
    print(f"{profile.name}：已导出 {len(glyphs)} 个 Unicode 字形。")
    print(f"BDF：{args.output}\n报告：{report_path}")
    print("未映射扩展槽位与缺字已记录；不生成普通 ASCII 别名。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
