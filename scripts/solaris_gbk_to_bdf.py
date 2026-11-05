#!/usr/bin/env python3
"""Offline, standard-library conversion of five verified Solaris GBK Song PCFs.

Only local decompressed PCFs are accepted. No downloads or programs are run.
Unicode mode explicitly omits 95 unresolved historical GBK codes; use --encoding
native-gbk to retain all original codes. Pixels and original metrics are retained.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys

SOURCES = {
 '3c092318acb711fed39f11ad00c356e13a454ef0abf213916a74bc74299f7db6': {'name':'gbksong12','size':1696464,'cell':12,'ascent':12,'descent':2},
 '975ac1cf10c384db0902283468f3d373761ac46d9e5992e20fe2a8e7aa7db309': {'name':'gbksong14','size':1872304,'cell':14,'ascent':13,'descent':3},
 '07de4bec37ba0d0354f06ca1c101c46518e4eabd18fff6a8e9953bf676f57c65': {'name':'gbksong16','size':2048144,'cell':16,'ascent':15,'descent':3},
 '63d229d64536be3a8548dd1605879ffeb6911cae09d3dc0814d4c0142006eb8a': {'name':'gbksong20','size':2399824,'cell':20,'ascent':19,'descent':3},
 '171d73f44ef1d23d0e5d0e29b3b70057bef6e3574af6dce9ccd67c2879c9528e': {'name':'gbksong24','size':2751504,'cell':24,'ascent':22,'descent':4},
}
MAPPING_SHA256 = '94416a1bdf936ecdc613263e631b2a17f602afb2334a1244305c886c0d5223d5'
UNMAPPED_SHA256 = 'a482b585a942aa1d8a7617e486063b30728a718bd16f218f5cd58b3d43cb4cf4'
SAFE_DIR_FD = (hasattr(os,'O_NOFOLLOW') and hasattr(os,'O_DIRECTORY')
               and os.open in os.supports_dir_fd and os.mkdir in os.supports_dir_fd)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def require_safe_platform():
    if not SAFE_DIR_FD:
        raise ValueError('Safe file handling requires POSIX O_NOFOLLOW and dir_fd support')


def _absolute_parts(path):
    path = Path(path)
    if '..' in path.parts:
        raise ValueError('Parent traversal components are not accepted')
    return Path(os.path.abspath(path)).parts[1:]


def load_font(path):
    """Read a bounded regular file using no-follow directory-relative opens."""
    require_safe_platform()
    parts = _absolute_parts(path)
    if not parts:
        raise ValueError('Input must name a regular file')
    dflags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open('/', dflags)
    try:
        for part in parts[:-1]:
            child = os.open(part, dflags, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd,'rb') as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('Input must be a regular file, not a device, FIFO or directory')
            if Path(path).suffix.lower() == '.z':
                raise ValueError('Compressed .Z input is not accepted; first decode locally with uncompress -c into a new .pcf')
            if info.st_size not in {s['size'] for s in SOURCES.values()}:
                raise ValueError('Unsupported PCF size')
            data = handle.read(max(s['size'] for s in SOURCES.values()) + 1)
    finally:
        os.close(parent)
    source = SOURCES.get(sha256(data))
    if source is None or len(data) != source['size']:
        raise ValueError('SHA-256 mismatch: modified or unsupported PCF')
    return data, source


@dataclass(frozen=True)
class Glyph:
    width: int
    height: int
    xoff: int
    yoff: int
    advance: int
    swidth: int
    rows: tuple


class Reader:
    def __init__(self, data, endian='<'):
        self.data, self.endian = data, endian

    def take(self, offset, length):
        if offset < 0 or length < 0 or offset + length > len(self.data):
            raise ValueError('Truncated PCF table')
        return self.data[offset:offset+length]

    def unpack(self, fmt, offset):
        fmt = self.endian + fmt
        return struct.unpack(fmt, self.take(offset, struct.calcsize(fmt)))


def decode_pcf(data):
    """Bounded PCF decoder; CLI additionally requires a known complete source SHA.

    Synthetic fixtures may call this directly. No arbitrary source is accepted by
    the public CLI. Some original accelerator table directory sizes overstate the
    serialized payload: tables are bounded by their next offset and EOF as well.
    """
    base = Reader(data)
    if base.take(0,4) != b'\x01fcp':
        raise ValueError('Not a PCF font')
    count, = base.unpack('I',4)
    if not 1 <= count <= 32:
        raise ValueError('Invalid PCF table count')
    descriptors = [base.unpack('4I',8+i*16) for i in range(count)]
    if len({x[0] for x in descriptors}) != count:
        raise ValueError('Duplicate PCF table type')
    if len({x[3] for x in descriptors}) != count:
        raise ValueError('Overlapping PCF table offsets')
    starts = sorted([x[3] for x in descriptors] + [len(data)])
    tables = {}
    for kind, fmt, size, off in descriptors:
        if off < 8+count*16 or off >= len(data) or size < 4:
            raise ValueError('Invalid PCF table extent')
        end = min(off+size, starts[starts.index(off)+1], len(data))
        table = base.take(off,end-off)
        if Reader(table).unpack('I',0)[0] != fmt:
            raise ValueError('PCF table format disagrees with directory')
        tables[kind] = (fmt, Reader(table,'>' if fmt & 4 else '<'))
    if not {1,2,4,8,32,64}.issubset(tables):
        raise ValueError('Missing required PCF table')
    fmt, r = tables[1]
    if fmt & ~0x3f:
        raise ValueError('Unsupported property table format')
    n, = r.unpack('I',4)
    if n > 512:
        raise ValueError('Too many PCF properties')
    string_start = (8+n*9+3)//4*4
    ns, = r.unpack('I',string_start)
    strings = r.take(string_start+4,ns)
    def string_at(offset):
        if offset >= len(strings) or b'\0' not in strings[offset:]:
            raise ValueError('Invalid PCF property string')
        text = strings[offset:].split(b'\0',1)[0].decode('latin1')
        if any(ord(c)<32 or ord(c)==127 for c in text):
            raise ValueError('Control character in PCF property')
        return text
    props = {}
    for i in range(n):
        no, flag, value = r.unpack('IBI',8+i*9)
        if flag not in (0,1):
            raise ValueError('Invalid string-property flag')
        name = string_at(no)
        if not name or any(not (c.isalnum() or c=='_') for c in name) or name in props:
            raise ValueError('Invalid or duplicate property name')
        props[name] = string_at(value) if flag else value
    fmt, r = tables[4]
    if fmt & ~0x13f:
        raise ValueError('Unsupported metrics format')
    if fmt & 0x100:
        n, = r.unpack('H',4)
        metrics = [tuple(x-128 for x in r.take(6+i*5,5)) for i in range(n)]
    else:
        n, = r.unpack('I',4)
        if n > 65535:
            raise ValueError('Too many glyph metrics')
        metrics = [r.unpack('5hH',8+i*12)[:5] for i in range(n)]
    if not n:
        raise ValueError('Empty metrics')
    fmt, r = tables[64]
    if r.unpack('I',4)[0] != n:
        raise ValueError('SWIDTH count disagrees with metrics')
    swidths = r.unpack(str(n)+'i',8)
    fmt, r = tables[8]
    if fmt & ~0x3f or r.unpack('I',4)[0] != n:
        raise ValueError('Invalid bitmap format/count')
    offsets = r.unpack(str(n)+'I',8)
    sizes = r.unpack('4I',8+n*4)
    pad, unit = 1<<(fmt & 3), 1<<((fmt>>4)&3)
    bitmap = r.take(8+n*4+16,sizes[fmt & 3])
    glyph_list = []
    for index,(left,right,advance,asc,desc) in enumerate(metrics):
        w,h = right-left,asc+desc
        if not 0 <= w <= 256 or not 0 <= h <= 256 or not 0 <= advance <= 256:
            raise ValueError('Invalid bitmap metrics')
        stride = ((w+7)//8 + pad-1)//pad*pad
        start,end = offsets[index],offsets[index]+stride*h
        if start > len(bitmap) or end > len(bitmap):
            raise ValueError('Glyph bitmap outside bitmap table')
        rows = []
        for y in range(h):
            row = bitmap[start+y*stride:start+(y+1)*stride]
            if bool(fmt & 4) != bool(fmt & 8) and unit != 1:
                if len(row)%unit:
                    raise ValueError('Incomplete PCF scan unit')
                row = b''.join(row[i:i+unit][::-1] for i in range(0,len(row),unit))
            if not fmt & 8:
                row = bytes(int(f'{x:08b}'[::-1],2) for x in row)
            rows.append(int.from_bytes(row,'big') >> (stride*8-w) if w else 0)
        glyph_list.append(Glyph(w,h,left,-desc,advance,swidths[index],tuple(rows)))
    fmt,r = tables[32]
    lo,hi,lb,hb,default = r.unpack('5H',4)
    if not (0<=lo<=hi<=255 and 0<=lb<=hb<=255):
        raise ValueError('Invalid encoding range')
    indices = r.unpack(str((hi-lo+1)*(hb-lb+1))+'H',14)
    glyphs = {}
    for i,index in enumerate(indices):
        if index == 65535:
            continue
        if index >= n:
            raise ValueError('Encoding refers to an absent glyph')
        code = ((i//(hi-lo+1)+lb)<<8)|(i%(hi-lo+1)+lo)
        glyphs[code] = glyph_list[index]
    def accelerator(kind):
        fmt,r = tables[kind]
        ascent,descent,overlap = r.unpack('3i',12)
        if not 0 <= ascent <= 256 or not 0 <= descent <= 256:
            raise ValueError('Invalid global ascent/descent')
        return ascent,descent
    ascent,descent = accelerator(2)
    if 256 in tables and accelerator(256) != (ascent,descent):
        raise ValueError('Accelerator metrics disagree')
    return props,glyphs,ascent,descent


def map_gbk(glyphs):
    mapping,unmapped,seen = {},[],set()
    for code in sorted(glyphs):
        raw = bytes([code]) if code<128 else code.to_bytes(2,'big')
        try:
            text = raw.decode('gbk','strict')
        except UnicodeError:
            unmapped.append(code)
            continue
        if len(text)!=1 or ord(text) in seen:
            raise ValueError('Ambiguous or duplicate Unicode mapping')
        mapping[code] = ord(text)
        seen.add(ord(text))
    return mapping,unmapped


def validate_font(props,glyphs,ascent,descent,source):
    mapping,unmapped = map_gbk(glyphs)
    digest = sha256(b''.join(c.to_bytes(2,'big')+u.to_bytes(4,'big') for c,u in sorted(mapping.items())))
    unknown_digest = sha256(b''.join(c.to_bytes(2,'big') for c in unmapped))
    han = [c for c,u in mapping.items() if 0x4e00<=u<=0x9fff]
    ascii_codes = {u for u in mapping.values() if u<128}
    n=source['cell']
    if (len(glyphs),len(mapping),len(unmapped),len(han)) != (21980,21885,95,20902):
        raise ValueError('Unexpected original/Unicode/Han/unmapped coverage')
    if digest!=MAPPING_SHA256 or unknown_digest!=UNMAPPED_SHA256:
        raise ValueError('GBK mapping fingerprint mismatch; do not substitute GB18030 or PUA mappings')
    if ascii_codes!=set(range(0x21,0x7f)) or 0x20 in glyphs:
        raise ValueError('Unexpected ASCII coverage')
    if any((glyphs[c].width,glyphs[c].height,glyphs[c].advance)!=(n,n,n) for c in han):
        raise ValueError('Unexpected Han bitmap dimensions/advance')
    if (ascent,descent)!=(source['ascent'],source['descent']):
        raise ValueError('Unexpected original global font metrics')
    if props.get('CHARSET_REGISTRY')!='gbk' or props.get('Copyright')!='Copyright (c) 1997 Beijing Zhong Yi Electronics Co.':
        raise ValueError('Unexpected native identity properties')
    return mapping,unmapped


def make_bdf(props,glyphs,ascent,descent,mapping,encoding='unicode'):
    if encoding not in ('unicode','native-gbk'):
        raise ValueError('Unknown encoding mode')
    output = {mapping[c] if encoding=='unicode' else c:g for c,g in glyphs.items() if encoding!='unicode' or c in mapping}
    if not output:
        raise ValueError('No output glyphs')
    left=min(g.xoff for g in output.values());bottom=min(g.yoff for g in output.values())
    right=max(g.xoff+g.width for g in output.values());top=max(g.yoff+g.height for g in output.values())
    ps=dict(props)
    original_name=str(ps.pop('FONT'))
    ps.update(FONT_ASCENT=ascent,FONT_DESCENT=descent,SOURCE_CHARSET_REGISTRY='gbk',SOURCE_CHARSET_ENCODING='0')
    if encoding=='unicode':
        ps['CHARSET_REGISTRY']='ISO10646';ps['CHARSET_ENCODING']='1'
    # DEFAULT_CHAR, if present, is not silently reinterpreted as a Unicode code.
    if 'DEFAULT_CHAR' in ps and encoding=='unicode':
        if ps['DEFAULT_CHAR'] in mapping:ps['DEFAULT_CHAR']=mapping[ps['DEFAULT_CHAR']]
        else:ps.pop('DEFAULT_CHAR')
    lines=['STARTFONT 2.1','COMMENT Source copyright 1997; package files 1998-07-23; Solaris 7 carrier 1999-11.',
           'COMMENT Native bitmap data only; no outlines, scaling, fallback or synthesized glyphs.',
           'COMMENT ASCII U+0020 is absent and is not added.',
           'COMMENT Unicode mode omits 95 unresolved native codes; native-gbk mode retains all 21980.',
           'COMMENT No font redistribution permission has been established.',
           'FONT '+original_name+('-Unicode' if encoding=='unicode' else '-NativeGBK'),
           f'SIZE {ps["POINT_SIZE"]//10} {ps["RESOLUTION_X"]} {ps["RESOLUTION_Y"]}',
           f'FONTBOUNDINGBOX {right-left} {top-bottom} {left} {bottom}',f'STARTPROPERTIES {len(ps)}']
    for k,v in sorted(ps.items()):
        if isinstance(v,str):v='"'+v.replace('"','""')+'"'
        lines.append(f'{k} {v}')
    lines += ['ENDPROPERTIES',f'CHARS {len(output)}']
    for code,g in sorted(output.items()):
        name=('uni' if encoding=='unicode' else 'GBK')+f'{code:04X}'
        lines += [f'STARTCHAR {name}',f'ENCODING {code}',f'SWIDTH {g.swidth} 0',f'DWIDTH {g.advance} 0',f'BBX {g.width} {g.height} {g.xoff} {g.yoff}','BITMAP']
        bw=(g.width+7)//8
        lines.extend(f'{row<<(bw*8-g.width):0{bw*2}X}' for row in g.rows)
        lines.append('ENDCHAR')
    return ('\n'.join(lines+['ENDFONT',''])).encode('ascii')


def output_path(path):
    require_safe_platform()
    path=Path(path)
    if '..' in path.parts:
        raise ValueError('Output parent traversal is not accepted')
    absolute=Path(os.path.abspath(path));root=Path.cwd()/'local-research'
    try:relative=absolute.relative_to(root)
    except ValueError as error:raise ValueError('Output must be inside ./local-research') from error
    if not relative.parts or absolute.suffix.lower()!='.bdf':
        raise ValueError('Output must be a new .bdf inside ./local-research')
    for p in [absolute,*absolute.parents]:
        if p.is_symlink():raise ValueError('Output path cannot contain symbolic links')
    if absolute.exists():raise ValueError('Output exists; never overwrites')
    return absolute


def write_bdf(path,data):
    path=output_path(path)
    relative=path.relative_to(Path.cwd())
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    parent=os.open('.',flags)
    try:
        for part in relative.parts[:-1]:
            try:os.mkdir(part,0o700,dir_fd=parent)
            except FileExistsError:pass
            child=os.open(part,flags,dir_fd=parent);os.close(parent);parent=child
        fd=os.open(relative.parts[-1],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
        with os.fdopen(fd,'wb') as handle:handle.write(data)
    # On write failure leave the new partial file for inspection. Removing a
    # pathname here could delete a replacement created concurrently by another
    # process; successful outputs and unrelated files must never be removed.
    finally:os.close(parent)


def export(font,output,encoding='unicode'):
    output=output_path(output)
    data,source=load_font(font)
    props,glyphs,ascent,descent=decode_pcf(data)
    mapping,unmapped=validate_font(props,glyphs,ascent,descent,source)
    bdf=make_bdf(props,glyphs,ascent,descent,mapping,encoding)
    write_bdf(output,bdf)
    return {'source':source['name'],'sourceSha256':sha256(data),'encoding':encoding,'sourceGlyphs':len(glyphs),
            'exportedGlyphs':len(mapping) if encoding=='unicode' else len(glyphs),'mappedHan':20902,
            'unmappedNativeCodes':[f'{c:04X}' for c in unmapped],'asciiRange':'U+0021-U+007E; U+0020 absent',
            'cell':[source['cell']]*2,'fontAscent':ascent,'fontDescent':descent,
            'mappingSha256':MAPPING_SHA256,'bdfSha256':sha256(bdf)}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font',required=True,type=Path,help='known local decompressed gbksong12/14/16/20/24.pcf')
    parser.add_argument('--output',required=True,type=Path,help='new .bdf under ./local-research; never overwritten')
    parser.add_argument('--encoding',choices=['unicode','native-gbk'],default='unicode')
    args=parser.parse_args(argv)
    try:report=export(args.font,args.output,args.encoding)
    except (ValueError,OSError,struct.error) as error:
        print(f'Error: {error}',file=sys.stderr);return 1
    print(json.dumps(report,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':
    sys.exit(main())
