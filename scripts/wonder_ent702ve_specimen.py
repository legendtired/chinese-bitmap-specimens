#!/usr/bin/env python3
"""Rebuild only the two fixed Wonder ENT-702VE(R) specimen lines."""
import argparse
import hashlib
import os
from pathlib import Path
import stat

from PIL import Image

SOURCE_BYTES = 9_155_584
SOURCE_SHA256 = "66976ad42a869df4e424d5ffd0c78d50717edacccafa5c407ec639e1f34b3de6"
LINES = ("山东省视频信号输入菜单片永", "山東省視頻信號輸入選單片永")
# Absolute bitmap and Unicode table offsets in this precise vendor image only.
LAYERS = ((0x64C00, 243_712, 0x19C400), (0xA0400, 472_576, 0x1BC400))


def checked_source(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != SOURCE_BYTES:
            raise ValueError("Expected the exact local firmware file")
        data = stream.read(SOURCE_BYTES + 1)
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("Firmware size or SHA-256 mismatch")
    return data


def fixed_image(data):
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("Firmware size or SHA-256 mismatch")
    image = Image.new("RGBA", (16 * max(map(len, LINES)), 36))
    for row, (line, (start, size, table)) in enumerate(zip(LINES, LAYERS)):
        for col, char in enumerate(line):
            key = table + 2 * ord(char)
            code = data[key:key + 2]
            if code != char.encode(("gb2312", "big5")[row]):
                raise ValueError(f"Unexpected mapping for U+{ord(char):04X}")
            lead, trail = code
            if row == 0:
                slot = (lead - 0xA7) * 94 + trail - 0xA1
            else:
                slot = (lead - 0xA1) * 157 + (trail - 0x40 if trail < 0x7F else trail - 0xA1 + 63)
            if not 0 <= slot < size // 32:
                raise ValueError("Fixed glyph slot outside its layer")
            cell = data[start + slot * 32:start + (slot + 1) * 32]
            if not any(cell):
                raise ValueError(f"Missing fixed glyph U+{ord(char):04X}")
            for ypos in range(16):
                for xpos in range(16):
                    if cell[(ypos // 8) * 16 + xpos] & (0x80 >> (ypos % 8)):
                        image.putpixel((col * 16 + xpos, row * 20 + ypos), (0, 0, 0, 255))
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware", type=Path)
    parser.add_argument("output", type=Path, help="New PNG path")
    args = parser.parse_args()
    if args.output.suffix.lower() != ".png":
        parser.error("Output must end in .png")
    image = fixed_image(checked_source(args.firmware))
    with args.output.open("xb") as stream:
        image.save(stream, format="PNG")


if __name__ == "__main__":
    main()
