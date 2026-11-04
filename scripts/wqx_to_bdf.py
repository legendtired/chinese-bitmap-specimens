#!/usr/bin/env python3
"""Recover a 12px BDF from a separately obtained, hash-verified NC1020 emulator ROM.
No font data is embedded. Python 3 standard library only. No network access.
This does not grant rights to the ROM or the recovered font.
"""
import argparse, hashlib, pathlib, sys
EXPECTED = 'd3bdc7847f3de1f7b58f12a07e51b3ca7f6d136d5f00ba626e39c591ea246c97'
BASE = 0x50C800

def recover(data):
    glyphs = []
    for high in range(0xA1, 0xF8):
        for low in range(0xA1, 0xFF):
            code = bytes((high, low))
            try:
                char = code.decode('gb2312', errors='strict')
            except UnicodeDecodeError:
                continue
            assert len(char) == 1 and char.encode('gb2312') == code
            addr = BASE + ((high - 0xA1) * 94 + low - 0xA1) * 18
            packed = bytes(data[(addr + j) ^ 0x4000] for j in range(18))
            bits = int.from_bytes(packed, 'big')
            rows = [((bits >> ((11 - y) * 12)) & 0xFFF) << 4 for y in range(12)]
            glyphs.append((ord(char), high * 256 + low, rows))
    assert len(glyphs) == 7445
    assert len({u for u, _, _ in glyphs}) == 7445
    assert sum(0xB0A1 <= gb <= 0xF7FE for _, gb, _ in glyphs) == 6763
    empty = [u for u, _, rows in glyphs if not any(rows)]
    assert empty == [0x3000], ('Unexpected blank glyphs', empty)
    assert not any(all(row == 0xFFF0 for row in rows) for _, _, rows in glyphs)
    return glyphs

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=pathlib.Path, help='Separately downloaded obj_lu.bin')
    parser.add_argument('output', type=pathlib.Path, help='New output .bdf file (will not overwrite)')
    args = parser.parse_args()
    data = args.rom.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != 25165824 or digest != EXPECTED:
        sys.exit('ROM does not match the verified image. Refusing to apply unverified offsets.\nSHA256: ' + digest)
    glyphs = recover(data)
    lines = [
        'STARTFONT 2.1',
        'COMMENT Recovered from a separately supplied NC1020 emulator image; rights not determined.',
        'COMMENT Source image SHA256 ' + EXPECTED,
        'COMMENT No verified font designer or redistribution license is asserted.',
        'FONT -Recovered-NC1020-Medium-R-Normal--12-120-75-75-C-120-ISO10646-1',
        'SIZE 12 75 75', 'FONTBOUNDINGBOX 12 12 0 0',
        'STARTPROPERTIES 4', 'FONT_ASCENT 12', 'FONT_DESCENT 0',
        'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"', 'ENDPROPERTIES',
        'CHARS ' + str(len(glyphs))]
    for unicode, gb, rows in glyphs:
        lines.extend([f'STARTCHAR uni{unicode:04X}', f'COMMENT GB2312 {gb:04X}',
                      'ENCODING ' + str(unicode), 'SWIDTH 1000 0', 'DWIDTH 12 0',
                      'BBX 12 12 0 0', 'BITMAP'])
        lines.extend(f'{row:04X}' for row in rows)
        lines.append('ENDCHAR')
    lines.append('ENDFONT')
    with args.output.open('x', encoding='ascii', newline='\n') as output:
        output.write('\n'.join(lines) + '\n')
    print(f'Wrote {len(glyphs)} Unicode-mapped glyphs, including 6763 Chinese characters, to {args.output}')
    print('This local conversion does not establish permission to redistribute the font.')

if __name__ == '__main__':
    main()
