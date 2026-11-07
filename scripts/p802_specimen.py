#!/usr/bin/env python3
"""Offline, SHA-locked P802 small GDR decoder and fixed two-line preview.

No network, firmware execution, embedded glyphs or complete-font output.
The existing phone decoder is reused only for this verified version-40 structure.
"""
import argparse
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import phone_gdr_specimens as gdr

CHINESE, ASCII = gdr.CHINESE, gdr.ASCII
SPEC = {'sha256': 'b830cc56393523e399fcdc349f865d57fe02b4ead0fc64139eb76e035e538961',
        'size': 1277578, 'version': 40, 'faces': 15,
        'layers': {0x4823: ('sony_ericsson_p802_12', 14, 11, 10406)}}
ZIP_SHA = '7d52140ed807ed92cd093281e6a8f60dca62b68f3c8b1ac8422c4c4ff435d328'
PD2_SHA = 'b7e4a9cb7395ea6436e660cce86367466fb27d0161b8e537d0d129648d6cba96'
require, sha = gdr.require, gdr.sha


def source_bytes(path, container='gdr'):
    data = path.read_bytes()
    if container == 'zip':
        require(len(data) == 4403425 and sha(data) == ZIP_SHA, 'Unexpected P802 PD2 ZIP')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            require(archive.namelist() == ['p802_r2a07_cxc16209.pd2'], 'Unexpected ZIP members')
            require(archive.testzip() is None, 'ZIP CRC mismatch')
            data = archive.read('p802_r2a07_cxc16209.pd2')
        container = 'pd2'
    if container == 'pd2':
        require(len(data) == 7337220 and sha(data) == PD2_SHA, 'Unexpected P802 PD2')
        require(data[4:8] == b'ROLF', 'Missing ROFS signature')
        marker = 'Linnea.gdr'.encode('utf-16-le')
        require(data.count(marker) == 1 and data.index(marker) == 0xde2, 'Unexpected ROFS filename')
        size, address, _, chars = gdr.unpack('<IIBB', data, 0xde2 - 10)
        require((size, address, chars) == (SPEC['size'], 0x480f38, 10), 'Changed ROFS directory')
        data = data[address + 4:address + 4 + size]
    require(len(data) == SPEC['size'] and sha(data) == SPEC['sha256'], 'Unexpected P802 GDR')
    return data


def decode(data):
    # Register only while decoding. Do not change the P908/9210C configuration.
    require('p802' not in gdr.SOURCES, 'Unexpected decoder configuration')
    gdr.SOURCES['p802'] = SPEC
    try:
        faces = gdr.decode(data, 'p802')
    finally:
        del gdr.SOURCES['p802']
    require(len(faces) == 1 and faces[0]['maxWidth'] == 15, 'Unexpected P802 layer')
    return faces[0]


def coverage(face):
    glyphs = face['glyphs']
    nonblank = {cp for cp, glyph in glyphs.items() if any(any(row) for row in glyph['rows'])}
    report = {key: value for key, value in face.items() if key != 'glyphs'}
    report['mappedCharacters'] = len(glyphs)
    report['cjkU3400U9fff'] = sum(0x3400 <= cp <= 0x9fff for cp in glyphs)
    report['nonblankCjkU3400U9fff'] = sum(0x3400 <= cp <= 0x9fff for cp in nonblank)
    for codec, count in [('gb2312', 6763), ('big5', 6998)]:
        expected = gdr.repertoire(codec)
        report[codec] = {'expectedHan': len(expected), 'presentHan': len(expected & glyphs.keys()),
                         'nonblankHan': len(expected & nonblank)}
        require(report[codec]['presentHan'] == report[codec]['nonblankHan'] == count, 'Changed Han coverage')
    require(report['mappedCharacters'] == 10406 and report['cjkU3400U9fff'] == report['nonblankCjkU3400U9fff'] == 9587, 'Changed CJK coverage')
    report['printableAscii'] = len(set(range(32, 127)) & glyphs.keys())
    report['blankAscii'] = [chr(cp) for cp in range(32, 127) if cp in glyphs and cp not in nonblank]
    require(report['printableAscii'] == 95 and report['blankAscii'] == [' '], 'Changed ASCII coverage')
    report['hanAdvances'] = dict(sorted(Counter(g['metrics'][3] for cp, g in glyphs.items() if 0x4e00 <= cp <= 0x9fff).items()))
    require(report['hanAdvances'] == {12: 9587}, 'Changed Han advances')
    report['fixedSampleMissing'] = [c for c in CHINESE + ASCII if ord(c) not in glyphs]
    require(not report['fixedSampleMissing'], 'Missing fixed sample character')
    return report


def render(face):
    return gdr.render(face)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--container', choices=['gdr', 'pd2', 'zip'], default='gdr')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must not already exist')
    face = decode(source_bytes(args.source, args.container))
    report, image = coverage(face), render(face)
    args.output.mkdir(parents=True)
    image.save(args.output / (face['id'] + '.png'))
    (args.output / 'coverage.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
