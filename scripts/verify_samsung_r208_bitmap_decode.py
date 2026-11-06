#!/usr/bin/env python3
"""Independent offline R208 validator; emits aggregate JSON only, never font data.

Reference pixels are populated one source bit at a time. The exporter is used
only as the implementation under test, never to generate reference pixels.
Full BDF exists only in memory. Firmware is read as data and never executed.
"""
import argparse
import ast
import binascii
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import zlib


def check(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def matrix(raw, width):
    check(len(raw) == width * 2, 'source extent')
    out = [[0] * width for _ in range(16)]
    for i, byte in enumerate(raw):
        page, x = divmod(i, width)
        for bit in range(8):
            out[page * 8 + bit][x] = (byte >> bit) & 1
    return out


def repack(pixels):
    width = len(pixels[0])
    out = bytearray(width * 2)
    for y, row in enumerate(pixels):
        for x, pixel in enumerate(row):
            if pixel:
                out[(y // 8) * width + x] |= 1 << (y % 8)
    return bytes(out)


def observed_pixels(g):
    return [[int(bool(row & (1 << (g['width'] - x - 1))))
             for x in range(g['width'])] for row in g['rows']]


def png_read(data):
    """Independent minimal PNG reader, CRC validation and all five filters."""
    check(data[:8] == b'\x89PNG\r\n\x1a\n', 'PNG signature')
    p, compressed, header = 8, bytearray(), None
    while p < len(data):
        n = int.from_bytes(data[p:p+4], 'big')
        kind, body = data[p+4:p+8], data[p+8:p+8+n]
        crc = int.from_bytes(data[p+8+n:p+12+n], 'big')
        check(len(body) == n and binascii.crc32(kind+body) & 0xffffffff == crc, 'PNG CRC')
        if kind == b'IHDR':
            header = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            compressed.extend(body)
        elif kind == b'IEND':
            break
        p += n + 12
    check(header is not None, 'PNG header')
    w, h, depth, color, compression, filtering, interlace = header
    check(depth == 8 and color in (0, 2) and (compression, filtering, interlace) == (0, 0, 0), 'PNG format')
    bpp = 1 if color == 0 else 3
    stride = w*bpp
    raw = zlib.decompress(compressed)
    check(len(raw) == h*(stride+1), 'PNG data length')
    prior, result = bytearray(stride), bytearray()
    for y in range(h):
        pos = y*(stride+1)
        mode, row = raw[pos], bytearray(raw[pos+1:pos+stride+1])
        check(mode in range(5), 'PNG filter')
        for x in range(stride):
            a, b, c = (row[x-bpp] if x >= bpp else 0), prior[x], (prior[x-bpp] if x >= bpp else 0)
            if mode == 0:
                predictor = 0
            elif mode == 1:
                predictor = a
            elif mode == 2:
                predictor = b
            elif mode == 3:
                predictor = (a+b)//2
            else:
                p0 = a+b-c
                ds = (abs(p0-a), abs(p0-b), abs(p0-c))
                predictor = (a,b,c)[ds.index(min(ds))]
            row[x] = (row[x]+predictor)&255
        for x in range(w):
            channels = row[x*bpp:(x+1)*bpp]
            check(len(set(channels)) == 1, 'Non-grayscale specimen pixel')
            result.append(channels[0])
        prior = row
    return w,h,bytes(result)


def verify(axf_path, ogm_path, exporter_path, old_png):
    axf, ogm, source = axf_path.read_bytes(), ogm_path.read_bytes(), exporter_path.read_bytes()
    check((len(axf), sha(axf)) == (1976056, '4c8d54f97d2c05f34b8cf9995fad1a4ba75fbb942c8dd8b49602fb70e931d521'), 'AXF identity')
    check((len(ogm), sha(ogm)) == (1178788, 'a7f2e4bd228b31937eb0ad47170592a1ec21b35801ae2086c00e9be686dab629'), 'OGM identity')
    tree = ast.parse(source)
    imports = sorted({n.name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for n in node.names})
    check(set(imports) <= {'argparse','binascii','hashlib','json','os','stat','struct','sys','zlib'}, 'Unexpected exporter import')
    check(all(node.module == 'pathlib' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)), 'Unexpected from import')
    check(not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {'eval','exec','compile','__import__'} for n in ast.walk(tree)), 'Dynamic code execution')
    check(not any(isinstance(n, ast.Constant) and isinstance(n.value, (str, bytes)) and len(n.value) > 2048 for n in ast.walk(tree)), 'Unexpected large embedded literal')
    spec = importlib.util.spec_from_file_location('r208_under_test', exporter_path)
    mod = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(mod)
    actual = mod.decode(axf, ogm)
    refs = {}
    codes = [int.from_bytes(ogm[p:p+2], 'little') for p in range(0xad7e,0x127ba,2)]
    check(len(codes) == 15646 and codes == sorted(set(codes)) and codes[-1] == 0x9fa6, 'Han index')
    for i, cp in enumerate(codes):
        raw = ogm[0x127ba+i*32:0x127ba+(i+1)*32]
        pixels = matrix(raw, 16)
        check(repack(pixels) == raw, 'Han round trip')
        check(observed_pixels(mod.decode_rows(raw,16)) == pixels, 'Han source slot decoder')
        if cp == 0x9fa6:
            check(not any(map(any,pixels)) and cp not in actual, 'Blank sentinel')
        else:
            check(0x4e00 <= cp <= 0x9fa5 and any(map(any,pixels)), 'Nonblank Han')
            refs[cp] = pixels
    gb = set()
    for hi in range(0xb0,0xf8):
        for lo in range(0xa1,0xff):
            try:
                gb.add(ord(bytes([hi,lo]).decode('gb2312')))
            except UnicodeDecodeError:
                pass
    check(len(gb) == 6763 and gb <= refs.keys(), 'GB2312 Han coverage')
    check(int.from_bytes(axf[0x1868d0:0x1868d4], 'little') == 0x17eec0, 'Index4 pointer')
    check(tuple(axf[o+4] for o in (0x158610,0x158604,0x15861c)) == (8,16,16), 'Index4 dimensions')
    for cp in range(32,127):
        raw = axf[0x17eec0+cp*16:0x17eec0+(cp+1)*16]
        refs[cp] = matrix(raw,8)
        check(repack(refs[cp]) == raw, 'ASCII round trip')
    check(not any(map(any,refs[32])) and all(any(map(any,refs[c])) for c in range(33,127)), 'ASCII blanks')
    punctuation = [int.from_bytes(ogm[p:p+2],'little') for p in range(0x8cb7a,0x8cb9a,2)]
    check(punctuation.index(0x3002) == 2, 'Period lookup')
    period_offset = 0x8cb7a+32+punctuation.index(0x3002)*32
    check(period_offset == 0x8cbda, 'Period bitmap address')
    raw = ogm[period_offset:period_offset+32]
    refs[0x3002] = matrix(raw,16)
    check(repack(refs[0x3002]) == raw, 'Period round trip')
    refs[0xff0c] = refs[44]
    check(refs.keys() == actual.keys() and len(refs) == 15742, 'Export keys')
    for cp,pixels in refs.items():
        check(actual[cp]['height'] == 16 and actual[cp]['width'] == len(pixels[0]) and observed_pixels(actual[cp]) == pixels, 'Export pixel mismatch')
    # Short, fixed raw Thumb instruction checks: no disassembler or firmware execution.
    paths = [
        (0x4041e,'ff231b029e4204db3006bd4b000ec01889e0','FFxx low byte plus literal A120; FF0C becomes A12C'),
        (0x405c8,'ff210420fff728fb','Select Western index 4 through setter at 0x3fc20'),
        (0x3fc20,'034aff2800d01071ff2900d01172f746','Setter writes font index at state+4'),
        (0x405dc,'a12a01d0a02a0ad16846001940780e990206120e0023381cfff726fb08e0','A1/A0 dispatch consumes low byte and calls Latin renderer 0x3fc44'),
        (0x3fcc8,'374909795e5c01ab1e70645c5c706c5c89005c80314c635801a94988514359180291','Selected index fetches width, height, stride and glyph base'),
        (0x3fd90,'01a8007803b0f0bd','Latin renderer returns stored width, 8 for index4'),
        (0x3fe20,'b0b503231b030f1cc11a0025ed430729634c1cd8102100f01df9','3000-range punctuation dispatch and lookup call')]
    evidence=[]
    for offset,expected,note in paths:
        check(axf[offset:offset+len(expected)//2].hex() == expected, 'Renderer instruction mismatch')
        evidence.append({'offset':hex(offset),'byteCount':len(expected)//2,'verified':True,'meaning':note})
    literals = {0x40720:0xa120,0x3fc30:0x1002180,0x3fda0:0x158610,0x3fd98:0x15861c,0x3fd9c:0x158604,0x3fda4:0x1868c0,0x3fda8:0x1002180,0x3ffc4:0x465b5}
    for offset,value in literals.items():
        check(int.from_bytes(axf[offset:offset+4],'little') == value, 'Renderer PC literal')
    pc_loads = {0x40428:0x40720,0x3fc20:0x3fc30,0x3fc50:0x3fda0,0x3fc52:0x3fd98,0x3fc54:0x3fd9c,0x3fcdc:0x3fda4,0x3fcc8:0x3fda8,0x3fe4e:0x3ffc4}
    for instruction, target in pc_loads.items():
        halfword = int.from_bytes(axf[instruction:instruction+2], 'little')
        check(halfword & 0xf800 == 0x4800, 'Thumb literal-load opcode')
        check(((instruction+4)&~3)+4*(halfword&255) == target, 'Thumb PC literal address')
    # Parse BDF from text independently, never write this complete font to disk.
    bdf = mod.bdf_bytes(actual).decode('ascii').splitlines()
    check('SIZE 16 75 75' in bdf and 'CHARS 15742' in bdf and bdf[-1] == 'ENDFONT', 'BDF global metrics')
    parsed={}
    i=0
    while i < len(bdf):
        if not bdf[i].startswith('STARTCHAR '):
            i+=1
            continue
        name=bdf[i].split()[1]
        fields={}
        i+=1
        while bdf[i] != 'BITMAP':
            key, value = bdf[i].split(' ',1)
            fields[key]=value
            i+=1
        cp=int(fields['ENCODING'])
        check(cp not in parsed and name == f'U{cp:04X}', 'BDF unique name')
        width=len(refs[cp][0])
        check(fields['BBX'] == f'{width} 16 0 0' and fields['DWIDTH'] == f'{width} 0' and fields['SWIDTH'] == ('960 0' if width == 16 else '480 0'), 'BDF glyph metrics')
        rows=bdf[i+1:i+17]
        check(bdf[i+17] == 'ENDCHAR' and all(len(r) == width//4 for r in rows), 'BDF row structure')
        parsed[cp]=[[int(bit) for bit in f'{int(row,16):0{width}b}'] for row in rows]
        check(parsed[cp] == refs[cp], 'BDF bitmap mismatch')
        i+=18
    check(parsed.keys() == refs.keys(), 'BDF exhaustive coverage')
    # Independently lay out fixed lines, margin and advance from native cells.
    lines=['视野无限广，窗外有蓝天。','0123456789 AaBb GgMm !?:+-.']
    widths=[sum(len(refs[ord(c)][0]) for c in line) for line in lines]
    check(widths == [184,216], 'Specimen line widths')
    expected=bytearray([255]*(224*44))
    for line_idx,line in enumerate(lines):
        x=4
        for c in line:
            pixels=refs[ord(c)]
            for y,row in enumerate(pixels):
                for dx,pixel in enumerate(row):
                    expected[(4+20*line_idx+y)*224+x+dx]=0 if pixel else 255
            x+=len(pixels[0])
    png=mod.png_bytes(*mod.specimen_pixels(actual))
    check(png_read(png) == (224,44,bytes(expected)), 'Generated PNG source pixel comparison')
    report=mod.make_report(axf,ogm,actual,png)
    check((report['specimen']['width'],report['specimen']['height'],report['specimen']['phraseWidth'],report['specimen']['asciiWidth']) == (224,44,184,216), 'Aggregate report dimensions')
    old=old_png.read_bytes()
    check(png_read(old) == (224,44,bytes(expected)), 'Research PNG source pixel comparison')
    return {'status':'PASS','method':'Independent source-bit matrices, source-byte repacking, BDF text parser, PNG filters and independently laid out source pixels. Complete font remains memory-only.',
            'exporterSha256':sha(source),'verifierSha256':sha(Path(__file__).read_bytes()),'axfSha256':sha(axf),'ogmSha256':sha(ogm),
            'checks':{'hanSourceSlots':15646,'nonblankHan':15645,'blankSentinel':'U+9FA6 excluded','gb2312Han':6763,'printableAscii':95,'periodSourceSlots':1,'sourceRoundTrips':15742,'exportedGlyphs':15742,'bdfParsedGlyphs':15742,'bdfSwidth':{'16':960,'8':480},'westernIndex':4,'westernBase':'0x17eec0','westernCell':[8,16],'ff0cAlias':'U+FF0C -> A12C -> native ASCII comma, width 8','periodLookupIndex':2,'periodOffset':'0x8cbda'},
            'rendererChecks':evidence,'pcLiterals':{hex(k):hex(v) for k,v in literals.items()},'pcRelativeLoads':{hex(k):hex(v) for k,v in pc_loads.items()},
            'specimen':{'width':224,'height':44,'lineWidths':widths,'outerMargin':4,'lineGap':4,'insertedCharacterGap':0,'all9856PixelsMatchSource':True,'researchNativePixelsMatch':True,'pngSha256':sha(png),'researchPngSha256':sha(old)},
            'safetyReview':{'exporterImports':imports,'noNetworkOrFirmwareExecutionObserved':True,'noEmbeddedGlyphDatasetObserved':True,'defaultOutput':'Fixed limited specimen and aggregate report only','completeBdf':'Explicit opt-in local-only; never created by this verifier','pathPolicy':'Exporter uses pinned directory descriptors, O_NOFOLLOW and exclusive new output creation; no overwrite. This verifier accepts trusted local paths and does not claim adversarial path safety.','limits':'Static source inspection is not a security proof. No legal permission or ownership conclusion.'}}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('axf',type=Path)
    p.add_argument('ogm',type=Path)
    p.add_argument('--exporter',type=Path,default=Path(__file__).with_name('samsung_r208_bitmap_export.py'))
    p.add_argument('--research-png',required=True,type=Path)
    p.add_argument('--audit',required=True,type=Path,help='New aggregate JSON file; existing file refused')
    a=p.parse_args()
    report=verify(a.axf,a.ogm,a.exporter,a.research_png)
    with a.audit.open('x',encoding='utf-8') as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print('PASS: independent source, renderer, BDF and PNG checks; aggregate audit written.')


if __name__ == '__main__':
    main()
