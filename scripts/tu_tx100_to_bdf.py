#!/usr/bin/env python3
"""Read a user-supplied, pinned teletext_rescue font table; never downloads fonts."""
import argparse, hashlib, pathlib, re
SHA256 = '6abba27355bbb968efd92af9bc4563d984c175801e0f84e139d963aae6093f82'

def read_font(path):
    data = pathlib.Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('Unexpected source SHA256; use the documented revision')
    text = data.decode('utf-8')
    def array(name):
        m = re.search(r'\b' + name + r'\s*\[[^=]+?=\s*\{(.*?)\};', text, re.S)
        if not m: raise ValueError('Missing table ' + name)
        return [int(x, 0) for x in re.findall(r'0x[0-9a-fA-F]+|[0-9]+', m[1])]
    codes, bits, unicode = array('jtFullCode'), array('jtFullBits'), array('jtJisUni')
    if len(codes) != 3670 or len(bits) != 3670*48 or len(unicode) != 8836:
        raise ValueError('Unexpected table dimensions')
    glyphs = {}
    for i, jis in enumerate(codes):
        row, col = jis >> 8, jis & 255
        if not (0x21 <= row <= 0x7e and 0x21 <= col <= 0x7e): continue
        cp = unicode[(row-0x21)*94+col-0x21]
        if cp in (0, 0xfffd): continue
        rows = tuple((bits[i*48+j*2]<<8)|bits[i*48+j*2+1] for j in range(24))
        if cp in glyphs and glyphs[cp] != rows: raise ValueError('Conflicting Unicode mapping')
        glyphs[cp] = rows
    return glyphs

def write_bdf(glyphs, output):
    lines=['STARTFONT 2.1','FONT -research-tu-tx100-medium-r-normal--24-240-75-75-c-160-iso10646-1','SIZE 24 75 75','FONTBOUNDINGBOX 16 24 0 0','STARTPROPERTIES 2','FONT_ASCENT 24','FONT_DESCENT 0','ENDPROPERTIES',f'CHARS {len(glyphs)}']
    for cp, rows in sorted(glyphs.items()):
        lines += [f'STARTCHAR U{cp:04X}',f'ENCODING {cp}','SWIDTH 667 0','DWIDTH 16 0','BBX 16 24 0 0','BITMAP'] + [f'{row:04X}' for row in rows] + ['ENDCHAR']
    lines += ['ENDFONT']
    with pathlib.Path(output).open('x', encoding='ascii') as out: out.write('\n'.join(lines)+'\n')

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input'); p.add_argument('output')
    a=p.parse_args()
    write_bdf(read_font(a.input), a.output)
