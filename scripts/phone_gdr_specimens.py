#!/usr/bin/env python3
"""Offline, SHA-locked P908/9210C native GDR decoder and fixed two-line previews.

No network access, firmware execution, embedded glyphs or complete-font output.
Only the approved four layers are returned; other GDR versions are not supported.
"""
import argparse
import hashlib
import json
import struct
import zlib
from collections import Counter
from pathlib import Path

CHINESE = '视野无限广，窗外有蓝天。 視野無限廣，窗外有藍天。'
ASCII = '0123456789 AaBb GgMm !?:+-.'
SOURCES = {
    'p908': {'sha256': 'debad6cef3b0b423fc53b32a923c87d0373671f929f520063d40117d6972cc4f',
             'size': 1821475, 'version': 40, 'faces': 15,
             'layers': {0x18be: ('sony_ericsson_p908_14', 16, 13, 16635)}},
    '9210c': {'sha256': '4cee557f8edb16c096e708d13cc24ecd7ae7461f25b27ae46e57c925aa5a69f4',
              'size': 2915114, 'version': 39, 'faces': 9,
              'layers': {0x100054f9: ('nokia_9210c_15', 16, 14, 22327),
                         0x10005504: ('nokia_9210c_17', 18, 16, 22327),
                         0x10005505: ('nokia_9210c_19', 20, 18, 22327)}}}
PD1_SHA = '52103c468cbd1ed6dae379965a6250fec78bfb90f8c3d8f0d04fb816b27c123d'
SFX_SHA = '6ccf1082e7194dcaeabd79c4b7f31d2a29973232771766c91b358d56420f7ee4'
PPM_SHA = 'bcda421d7fc490e141039d12bba9d1f430c4d7a830e745735102220422bea973'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def unpack(fmt, data, offset):
    require(0 <= offset <= len(data) - struct.calcsize(fmt), 'Record outside input')
    return struct.unpack_from(fmt, data, offset)

def source_bytes(path, device, container='gdr'):
    data = path.read_bytes()
    if container == 'pd1':
        require(device == 'p908' and sha(data) == PD1_SHA, 'Unexpected P908 PD1')
        require(len(data) == 27742212, 'Unexpected PD1 length')
        data = data[0x188c554:0x188c554 + SOURCES['p908']['size']]
    elif container in ('sfx', 'ppm'):
        require(device == '9210c', 'PPM/SFX is only supported for 9210C')
        if container == 'sfx':
            require(sha(data) == SFX_SHA, 'Unexpected 9210C SFX')
            # Read only the verified Chinese PPM local ZIP member. The broken MCU
            # and inconsistent central directory are neither repaired nor used.
            matches = []
            pos = 0
            while True:
                pos = data.find(b'PK\x03\x04', pos)
                if pos < 0:
                    break
                if pos + 30 <= len(data):
                    header = unpack('<4s5H3I2H', data, pos)
                    _, _, flags, method, _, _, crc, packed, size, nl, xl = header
                    name = data[pos + 30:pos + 30 + nl]
                    if name == b'RAE33036.0US':
                        require(not flags & 9 and method == 8, 'Unsupported ZIP member')
                        start = pos + 30 + nl + xl
                        require(start + packed <= len(data) and size == 5361145, 'ZIP bounds')
                        raw = zlib.decompress(data[start:start + packed], -15)
                        require(len(raw) == size and zlib.crc32(raw) == crc, 'ZIP CRC/length')
                        matches.append(raw)
                pos += 4
            require(len(matches) == 1, 'Expected one Chinese PPM member')
            data = matches[0]
        require(sha(data) == PPM_SHA and len(data) == 5361145, 'Unexpected Chinese PPM')
        records = []
        pos = 109
        while pos < len(data):
            require(pos + 10 <= len(data), 'Truncated transport header')
            h = data[pos:pos + 10]
            addr = int.from_bytes(h[1:5], 'big')
            length = int.from_bytes(h[6:9], 'big')
            raw = data[pos + 10:pos + 10 + length]
            require(h[0] == 0x14 and length > 0 and len(raw) == length, 'Transport bounds')
            require(sum(h[1:]) & 255 == 255 and (sum(raw) + h[5]) & 255 == 0, 'Transport checksum')
            records.append((addr, raw))
            pos += 10 + length
        require(pos == len(data) and len(records) == 654, 'Transport count')
        ordered = sorted(records)
        require(all(a + len(r) <= b for (a, r), (b, _) in zip(ordered, ordered[1:])), 'Overlapping transport')
        marker = 'Linda.gdr'.encode('utf-16-le')
        require(data.count(marker) == 1, 'Ambiguous ROM directory')
        at = data.index(marker)
        size, address, _, chars = unpack('<IIBB', data, at - 10)
        require((size, address, chars) == (2915114, 0x50a74780, 9), 'Unexpected ROM directory')
        address -= 0x4f800000
        out = bytearray()
        while len(out) < size:
            current = address + len(out)
            found = [(a, r) for a, r in records if a <= current < a + len(r)]
            require(len(found) == 1, 'ROM slice gap or overlap')
            a, raw = found[0]
            out.extend(raw[current - a:current - a + size - len(out)])
        data = bytes(out)
    spec = SOURCES[device]
    require(len(data) == spec['size'] and sha(data) == spec['sha256'], 'Unexpected GDR SHA/length')
    return data

def decode(data, device):
    spec = SOURCES[device]
    require(len(data) == spec['size'] and sha(data) == spec['sha256'], 'Unexpected GDR SHA/length')
    require(data[:16] == bytes.fromhex('37000010390000100000000053383947'), 'GDR signature')
    require(unpack('<I', data, 20)[0] == spec['version'], 'GDR version')
    pos = unpack('<I', data, 32)[0]
    count = unpack('<I', data, pos)[0]
    require(count == spec['faces'], 'GDR face count')
    pos += 4
    faces = []
    for _ in range(count):
        uid, posture, weight, prop, height, ascent, maxwidth, normal, enc, sections = unpack('<I7B2I', data, pos)
        pos += 19
        require(0 < sections <= 65536, 'Invalid section count')
        entries = [unpack('<HHII', data, pos + i * 12) for i in range(sections)]
        pos += sections * 12
        if uid in spec['layers']:
            ident, expected_height, expected_ascent, expected_count = spec['layers'][uid]
            require((height, ascent) == (expected_height, expected_ascent), 'Changed layer metrics')
            faces.append({'id': ident, 'uid': hex(uid), 'cellHeight': height, 'ascent': ascent,
                          'maxWidth': maxwidth, 'expectedCount': expected_count, 'sections': entries})
    require(len(faces) == len(spec['layers']), 'Missing/duplicate approved layer')
    for face in faces:
        glyphs = {}
        for first, last, record, bitmap in face.pop('sections'):
            count = unpack('<I', data, record)[0]
            require(first <= last and count == last - first + 1, 'Section count')
            require(record + 4 + count * 8 == bitmap, 'Inline eight-byte record boundary')
            length = unpack('<I', data, bitmap)[0]
            require(bitmap + 4 + length <= len(data), 'Bitmap outside GDR')
            packed = data[bitmap + 4:bitmap + 4 + length]
            for index, cp in enumerate(range(first, last + 1)):
                offset, ascent, height, left, advance, right, pad = unpack('<H5bB', data, record + 4 + index * 8)
                if offset == 65535:
                    continue
                width = advance - left - right
                require(0 <= width <= 64 and 0 <= height <= 64 and advance >= 0, 'Invalid glyph metrics')
                require(offset < len(packed) and cp not in glyphs, 'Offset/Unicode overlap')
                bit = offset * 8
                def take(n):
                    nonlocal bit
                    require(bit + n <= len(packed) * 8, 'Truncated bitmap run')
                    value = sum(((packed[(bit + k) // 8] >> ((bit + k) % 8)) & 1) << k for k in range(n))
                    bit += n
                    return value
                rows = []
                while len(rows) < height:
                    literal, repeat = take(1), take(4)
                    require(0 < repeat <= height - len(rows), 'Invalid row run')
                    if literal:
                        rows.extend(tuple(take(1) for _ in range(width)) for _ in range(repeat))
                    else:
                        row = tuple(take(1) for _ in range(width))
                        rows.extend([row] * repeat)
                glyphs[cp] = {'metrics': (ascent, height, left, advance, right), 'rows': tuple(rows)}
        require(len(glyphs) == face.pop('expectedCount'), 'Changed Unicode coverage')
        face['glyphs'] = glyphs
    return faces

def repertoire(codec):
    result = set()
    for a in range(0x81, 0xff):
        for b in range(0x40, 0xff):
            try:
                text = bytes([a, b]).decode(codec)
            except UnicodeDecodeError:
                continue
            if len(text) == 1 and 0x4e00 <= ord(text) <= 0x9fff:
                result.add(ord(text))
    return result

def coverage(face):
    glyphs = face['glyphs']
    nonblank = {cp for cp, g in glyphs.items() if any(any(row) for row in g['rows'])}
    report = {k: v for k, v in face.items() if k != 'glyphs'}
    report['mappedCharacters'] = len(glyphs)
    report['cjkU3400U9fff'] = sum(0x3400 <= cp <= 0x9fff for cp in glyphs)
    report['nonblankCjkU3400U9fff'] = sum(0x3400 <= cp <= 0x9fff for cp in nonblank)
    for codec in ('gb2312', 'big5'):
        expected = repertoire(codec)
        report[codec] = {'expectedHan': len(expected), 'presentHan': len(expected & glyphs.keys()),
                         'nonblankHan': len(expected & nonblank)}
    report['printableAscii'] = len(set(range(32, 127)) & glyphs.keys())
    report['blankAscii'] = [chr(cp) for cp in range(32, 127) if cp in glyphs and cp not in nonblank]
    require(report['gb2312']['nonblankHan'] == 6763 and report['big5']['nonblankHan'] == 13061, 'Incomplete Han')
    require(report['printableAscii'] == 95 and report['blankAscii'] == [' '], 'Unexpected ASCII')
    han = [g for cp, g in glyphs.items() if 0x4e00 <= cp <= 0x9fff]
    report['hanAdvances'] = dict(sorted(Counter(g['metrics'][3] for g in han).items()))
    return report

def render(face):
    from PIL import Image
    lines = [CHINESE, ASCII]
    glyphs = face['glyphs']
    require(all(ord(c) in glyphs for line in lines for c in line), 'Missing fixed sample character')
    # Keep the full native line cell. Include any bearing overhang, never crop ink.
    xmin, xmax = 0, 0
    for line in lines:
        pen = 0
        for c in line:
            a, h, left, advance, right = glyphs[ord(c)]['metrics']
            width = advance - left - right
            require(0 <= face['ascent'] - a and face['ascent'] - a + h <= face['cellHeight'], 'Sample exceeds native cell')
            xmin, xmax = min(xmin, pen + left), max(xmax, pen + left + width, pen + advance)
            pen += advance
    out = Image.new('RGBA', (xmax - xmin + 8, face['cellHeight'] * 2 + 12), (255, 255, 255, 0))
    for line_no, line in enumerate(lines):
        pen = 4 - xmin
        top = 4 + line_no * (face['cellHeight'] + 4)
        for c in line:
            g = glyphs[ord(c)]
            a, h, left, advance, right = g['metrics']
            for y, row in enumerate(g['rows']):
                for x, value in enumerate(row):
                    if value:
                        out.putpixel((pen + left + x, top + face['ascent'] - a + y), (28, 31, 33, 255))
            pen += advance
    return out

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--device', choices=SOURCES, required=True)
    parser.add_argument('--container', choices=['gdr', 'pd1', 'ppm', 'sfx'], default='gdr')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must not already exist')
    faces = decode(source_bytes(args.source, args.device, args.container), args.device)
    results = []
    images = []
    for face in faces:
        report = coverage(face)
        image = render(face)
        images.append((face['id'], image))
        results.append(report)
    args.output.mkdir(parents=True)
    for ident, image in images:
        image.save(args.output / (ident + '.png'))
    (args.output / 'coverage.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')

if __name__ == '__main__':
    main()
