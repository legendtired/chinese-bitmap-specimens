#!/usr/bin/env python3
"""Export the audited CNS40 plane-1 HBF/BIN set to source-encoded BDF.

This intentionally is not a general HBF converter or Unicode remapper.
Only the three audited source hashes are accepted. No fonts are downloaded.
"""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = {
    'cns40-1.hbf': 'c3139c265646ba49fdaf427f6ae3d121f0929ebabc6a816b1d61180a9de147c1',
    '4040w0.bin': '9077666c6a93d69a41aa1b2f2ef05057b7448b21deacdb6816996f7096832cde',
    '4040w1.bin': '611d2bb7c0fb6e5a6bf942cf7fa910edb4becbaae52923e9922f4016a9f16c67',
}


def convert(hbf, output, report):
    hbf = Path(hbf)
    output, report = Path(output), Path(report)
    if output.resolve() == report.resolve():
        raise ValueError('The BDF and report must be different files.')
    if any(p.exists() or p.is_symlink() for p in (output, report)):
        raise ValueError('Refusing to overwrite an existing BDF or report.')
    if not output.parent.is_dir() or not report.parent.is_dir():
        raise ValueError('BDF and report parent directories must already exist.')
    paths = {'cns40-1.hbf': hbf, **{n: hbf.parent / n for n in EXPECTED if n != 'cns40-1.hbf'}}
    data = {name: path.read_bytes() for name, path in paths.items()}
    hashes = {name: hashlib.sha256(value).hexdigest() for name, value in data.items()}
    for name, expected in EXPECTED.items():
        if hashes[name] != expected:
            raise ValueError(f'{name}: source hash does not match the audited CNS40 input.')
    lines = data['cns40-1.hbf'].decode('ascii').splitlines()
    properties = []
    in_properties = False
    glyphs = []
    for line in lines:
        key, _, value = line.partition(' ')
        if key == 'STARTPROPERTIES':
            in_properties = True
        elif key == 'ENDPROPERTIES':
            in_properties = False
        elif in_properties:
            if key == 'DEFAULT_CHAR':
                value = str(int(value, 0))
            properties.append((key, value))
        elif key == 'HBF_CODE_RANGE':
            codes, name, start = value.split()
            first, last = (int(n, 0) for n in codes.split('-'))
            offset = int(start, 0)
            for code in range(first, last + 1):
                if not 0x21 <= (code & 255) <= 0x7e:
                    continue
                bitmap = data[name][offset:offset+200]
                if len(bitmap) != 200:
                    raise ValueError('Truncated bitmap input.')
                glyphs.append((code, bitmap))
                offset += 200
    assert len(glyphs) == 6085 and len({c for c, _ in glyphs}) == 6085
    result = [
        'STARTFONT 2.1',
        'COMMENT Source encoding is CNS11643-92 plane 1, not Unicode.',
        'COMMENT Original HBF SIZE is 40 150 150; resolution properties remain 75 as in the source.',
        'COMMENT SWIDTH 480 is derived from DWIDTH 40 and original SIZE; no outlines are generated.',
    ]
    result.extend(line for line in lines if line == 'COMMENT' or line.startswith('COMMENT ' ) or line.startswith('COMMENT\t'))
    result += ['FONT cns40st-1', 'SIZE 40 150 150', 'FONTBOUNDINGBOX 40 40 0 -6', f'STARTPROPERTIES {len(properties)}']
    result += [f'{k} {v}' for k,v in properties]
    result += ['ENDPROPERTIES', f'CHARS {len(glyphs)}']
    for code, bitmap in glyphs:
        result += [f'STARTCHAR CNS1_{code:04X}', f'ENCODING {code}', 'SWIDTH 480 0', 'DWIDTH 40 0', 'BBX 40 40 0 -6', 'BITMAP']
        result.extend(bitmap[i:i+5].hex().upper() for i in range(0, 200, 5))
        result += ['ENDCHAR']
    result += ['ENDFONT']
    rendered = ('\n'.join(result)+'\n').encode('ascii')
    details = {
        'format': 'source-encoded BDF 2.1',
        'source_encoding': 'CNS11643-92p1',
        'unicode_remapped': False,
        'glyphs': len(glyphs),
        'source_sha256': hashes,
        'bdf_sha256': hashlib.sha256(rendered).hexdigest(),
        'metrics': {'width':40, 'height':40, 'x_offset':0, 'y_offset':-6, 'advance':40, 'font_ascent':34, 'font_descent':6},
        'source_inconsistency_preserved': 'SIZE uses 150 dpi, while RESOLUTION_X/Y properties use 75 dpi.',
        'derived_field': 'SWIDTH=480, derived from original SIZE and pixel advance; not original outline data.',
        'license_notice': 'The HBF header public-domain notice does not itself authorize redistribution of the bitmap files.',
    }
    with output.open('xb') as f:
        f.write(rendered)
    with report.open('x', encoding='utf-8') as f:
        json.dump(details, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hbf', help='Audited cns40-1.hbf, alongside 4040w0.bin and 4040w1.bin')
    parser.add_argument('output', help='New BDF path (source CNS codes, not Unicode)')
    parser.add_argument('--report', required=True, help='New JSON report path')
    args = parser.parse_args()
    try:
        details = convert(args.hbf, args.output, args.report)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    print(f"Exported {details['glyphs']} original CNS plane-1 glyphs; no Unicode remapping.")

if __name__ == '__main__':
    main()
