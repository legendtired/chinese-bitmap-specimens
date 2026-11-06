#!/usr/bin/env python3
"""Verify a local PS2 exporter against original ROM pixels; embeds no font data.

All font bytes and generated BDFs stay in memory. The only optional output is a
small audit JSON containing hashes, counts, test statuses and limitations.
"""
import argparse
import binascii
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import zlib

ROM_SHA256='fe61257af2cd2675256c2dcc5ffd78eae1a22d24f816571c2f927a93ed3bcc2d'
MODULES={'FNTHANCH':(0xD0,6912,'26e3532a0609f8051aa9b3755a20ed07cc4ce5aa94560392896175e0d9895281'),
         'GB18030':(0x1BD0,2058552,'d9e535e7497b8e444e642715e420ccb0d7118bec05ec71f36e585670db4fd5a4')}
PHRASE='视野无限广，窗外有蓝天。'
ASCII='0123456789 AaBb GgMm !?:+-.'
EXTRA='片版牌局'
TRADITIONAL='視野無限廣，窗外有藍天。'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(condition,message):
    if not condition:
        raise AssertionError(message)


def source_directory(data):
    # Parse offsets from the binary directory, not exporter constants.
    pos=0
    cursor=0
    result={}
    while pos+16<=len(data):
        name_raw=data[pos:pos+10]
        if name_raw==bytes(10):
            break
        name=name_raw.split(b'\0',1)[0].decode('ascii')
        size=struct.unpack('<I',data[pos+12:pos+16])[0]
        check(name not in result,'Duplicate directory entry')
        result[name]=(cursor,size)
        cursor=((cursor+size+15)//16)*16
        pos+=16
    check(result.get('ROMDIR')==(0,pos+16),'Directory extent mismatch')
    check(result.get('RESET')==(0,0),'Missing RESET')
    return result


def direct_rows(frame):
    # Deliberately no int.from_bytes or exporter decoder. Each bit is addressed.
    check(len(frame)==72,'Unexpected source frame length')
    return tuple(sum(((frame[y*3+x//8]>>(7-x%8))&1)<<(23-x)
                     for x in range(24)) for y in range(24))


def independent_mapping(codec):
    # Enumerated source blocks, independent of exporter slot_index arithmetic.
    result={}
    byte_slots={}
    blocks=[(range(0xA1,0xAA),range(0xA1,0xFF),0),
            (range(0xB0,0xF8),range(0xA1,0xFF),846),
            (range(0x81,0xA1),[v for v in range(0x40,0xFF) if v!=0x7F],7614),
            (range(0xAA,0xFF),[v for v in range(0x40,0xA1) if v!=0x7F],13694)]
    for leads,trails,index in blocks:
        for lead in leads:
            for trail in trails:
                byte_slots[(lead,trail)]=index
                try:c=bytes([lead,trail]).decode(codec)
                except UnicodeDecodeError:pass
                else:
                    check(ord(c) not in result,'Duplicate independent Unicode key')
                    result[ord(c)]=index
                index+=1
    return result,byte_slots


def png_pixels(blob):
    check(blob[:8]==b'\x89PNG\r\n\x1a\n','PNG signature')
    p=8
    compressed=bytearray()
    header=None
    ended=False
    while p<len(blob):
        check(p+12<=len(blob),'Truncated PNG chunk')
        size=struct.unpack('>I',blob[p:p+4])[0]
        tag=blob[p+4:p+8]
        body=blob[p+8:p+8+size]
        check(len(body)==size and p+12+size<=len(blob),'PNG extent')
        crc=struct.unpack('>I',blob[p+8+size:p+12+size])[0]
        check(crc==binascii.crc32(tag+body)&0xFFFFFFFF,'PNG CRC')
        if tag==b'IHDR':
            check(header is None,'Repeated IHDR')
            header=struct.unpack('>IIBBBBB',body)
        elif tag==b'IDAT':compressed+=body
        elif tag==b'IEND':ended=True
        p+=size+12
    check(ended and header is not None,'Missing PNG header/end')
    w,h,bits,ctype,comp,fil,interlace=header
    check((bits,ctype,comp,fil,interlace)==(8,6,0,0,0),'Unexpected PNG format')
    raw=zlib.decompress(compressed)
    check(len(raw)==h*(w*4+1),'PNG decompressed extent')
    scanlines=[]
    for y in range(h):
        row=raw[y*(w*4+1):(y+1)*(w*4+1)]
        check(row[0]==0,'Expected exporter zero-filter scanline')
        scanlines.append(row[1:])
    return w,h,scanlines


def check_png(blob,texts,gap,source_frames):
    w,h,scanlines=png_pixels(blob)
    widths=[len(t)*(24+gap)-gap for t in texts]
    check((w,h)==(max(widths),len(texts)*24+(len(texts)-1)*4),'PNG dimensions')
    on=0
    for y,line in enumerate(scanlines):
        text_index,sy=divmod(y,28)
        for x in range(w):
            want=b'\xff\xff\xff\x00'
            if sy<24 and x<widths[text_index]:
                want=b'\xff\xff\xff\xff'
                ci,sx=divmod(x,24+gap)
                if sx<24:
                    frame=source_frames[ord(texts[text_index][ci])]
                    if (frame[sy*3+sx//8]>>(7-sx%8))&1:
                        want=b'\0\0\0\xff'
                        on+=1
            check(line[x*4:x*4+4]==want,f'PNG pixel mismatch at {x},{y}')
    return {'width':w,'height':h,'on_pixels':on,'sha256':sha(blob)}


def check_bdf(text,frames):
    lines=text.splitlines()
    check(lines[0]=='STARTFONT 2.1' and lines[-1]=='ENDFONT','BDF envelope')
    size=next(line for line in lines if line.startswith('SIZE '))
    check(size=='SIZE 24 75 75','BDF point size')
    check('FONTBOUNDINGBOX 24 24 0 0' in lines,'BDF bounding box')
    check('CHARS '+str(len(frames)) in lines,'BDF char count')
    actual={}
    widths=set()
    p=0
    while p<len(lines):
        if not lines[p].startswith('STARTCHAR '):p+=1;continue
        end=lines.index('ENDCHAR',p)
        block=lines[p+1:end]
        cp=int(next(x for x in block if x.startswith('ENCODING ')).split()[1])
        check(cp not in actual,'BDF duplicate encoding')
        check('DWIDTH 24 0' in block and 'BBX 24 24 0 0' in block,'BDF storage metrics')
        widths.add(next(x for x in block if x.startswith('SWIDTH ')))
        bit_start=block.index('BITMAP')+1
        hex_rows=block[bit_start:]
        check(len(hex_rows)==24 and all(len(row)==6 for row in hex_rows),'BDF bitmap dimensions')
        frame=b''.join(bytes.fromhex(row) for row in hex_rows)
        check(cp in frames and frame==frames[cp],f'BDF source-byte mismatch U+{cp:04X}')
        actual[cp]=True
        p=end+1
    check(set(actual)==set(frames),'BDF repertoire mismatch')
    # SWIDTH units are 1/1000 em; 24px at 24pt/75dpi requires 960.
    metrics_ok=widths=={'SWIDTH 960 0'}
    return {'glyph_count':len(actual),'sha256':sha(text.encode('ascii')),
            'source_pixel_roundtrip':True,'swidth_consistent_with_size_and_dwidth':metrics_ok,
            'swidth_values':sorted(widths)}


def audit(source,exporter,specimen_dir=None):
    data=source.read_bytes()
    check(len(data)==2097152 and sha(data)==ROM_SHA256,'Wrong source size/hash')
    directory=source_directory(data)
    for name,(off,size,digest) in MODULES.items():
        check(directory.get(name)==(off,size),'Source directory module mismatch')
        check(sha(data[off:off+size])==digest,'Source module hash mismatch')
    spec=importlib.util.spec_from_file_location('ps2_export_under_test',exporter)
    module=importlib.util.module_from_spec(spec)
    previous_bytecode_setting=sys.dont_write_bytecode
    sys.dont_write_bytecode=True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode=previous_bytecode_setting
    all_rows={}
    counts={}
    for name,(off,size,digest) in MODULES.items():
        frames=[data[start:start+72] for start in range(off,off+size,72)]
        expected=[]
        for index,frame in enumerate(frames):
            alternative=direct_rows(frame)
            check(tuple(module.decode_rows(frame))==alternative,f'{name} source record {index} pixel mismatch')
            expected.append(alternative)
        all_rows[name]=expected
        counts[name]=len(frames)
    check(counts=={'FNTHANCH':96,'GB18030':28591},'Unexpected total source records')
    source_frames={}
    modes={}
    failures=[]
    png_reports={}
    exported_disk={}
    for codec in ('gb2312','gbk'):
        expected,byte_slots=independent_mapping(codec)
        check(module.mapping(codec)==expected,codec+' mapping mismatch')
        for lead in range(256):
            for trail in range(256):
                check(module.slot_index(lead,trail)==byte_slots.get((lead,trail)),'Source byte-slot boundary mismatch')
        decoded=module.decode(data,codec)
        check(set(decoded)==set(expected)|set(range(32,127)),codec+' decoded repertoire')
        frames={}
        for cp,index in expected.items():
            check(tuple(decoded[cp])==all_rows['GB18030'][index],codec+' decoded mapped pixels')
            off=directory['GB18030'][0]+index*72
            frames[cp]=data[off:off+72]
        for cp in range(32,127):
            check(tuple(decoded[cp])==all_rows['FNTHANCH'][cp-32],codec+' decoded ASCII pixels')
            off=directory['FNTHANCH'][0]+(cp-32)*72
            frames[cp]=data[off:off+72]
        blank_chinese=[cp for cp in expected if not any(frames[cp])]
        check(blank_chinese==[0x3000],codec+' unexpected blank mapped glyph')
        bdf_report=check_bdf(module.bdf(decoded),frames)
        if not bdf_report['swidth_consistent_with_size_and_dwidth']:
            failures.append(codec+': BDF SWIDTH disagrees with SIZE/DWIDTH; expected 960 at 24pt/75dpi.')
        modes[codec]={'mapped_doublebyte':len(expected),'with_printable_ascii':len(decoded),
                      'mapped_han':sum(0x4E00<=cp<=0x9FFF for cp in expected),
                      'blank_mapped_unicode':['U+3000'],
                      'mapping_sha256':sha(''.join(f'{cp:04X}:{idx}\n' for cp,idx in sorted(expected.items())).encode('ascii')),
                      'bdf':bdf_report}
        samples=[('ps2_scph50009_24.png',[PHRASE,ASCII],1),
                 ('ps2-china-phrase-1x.png',[PHRASE],0),
                 ('ps2-china-diagnostic-1x.png',[EXTRA],0),
                 ('ps2-china-ascii-1x.png',[ASCII],0)]
        if codec=='gbk':samples.append(('ps2-china-traditional-1x.png',[TRADITIONAL],0))
        for filename,texts,gap in samples:
            blob=module.png_data(decoded,texts,gap=gap)
            png_reports[codec+'/'+filename]=check_png(blob,texts,gap,frames)
            if specimen_dir and codec=='gbk':
                disk=specimen_dir/filename
                check(disk.is_file(),'Missing existing specimen '+filename)
                disk_blob=disk.read_bytes()
                check_png(disk_blob,texts,gap,frames)
                check(disk_blob==blob,'Existing specimen does not match current exporter '+filename)
                exported_disk[filename]=sha(disk_blob)
        source_frames[codec]=frames
    check(0x30FB in source_frames['gb2312'] and 0x00B7 in source_frames['gbk'],'A1A4 labels')
    check(source_frames['gb2312'][0x30FB]==source_frames['gbk'][0x00B7],'A1A4 alias pixels')
    check(source_frames['gb2312'][0x2015]==source_frames['gbk'][0x2014],'A1AA alias pixels')
    check(all(row&0xFFF==0 for rows in all_rows['FNTHANCH'] for row in rows),'ASCII right-half storage unexpectedly nonblank')
    check(all_rows['FNTHANCH'][0]==(0,)*24 and all_rows['FNTHANCH'][95]==(0,)*24,'ASCII space/DEL expected blank')
    check(all(any(row) for row in all_rows['FNTHANCH'][1:95]),'Printable ASCII unexpectedly blank')
    return {'passed':not failures,'failures':failures,
            'source_sha256':sha(data),'exporter_sha256':sha(exporter.read_bytes()),
            'modules':{n:{'offset':v[0],'size':v[1],'sha256':v[2]} for n,v in MODULES.items()},
            'all_source_record_bit_checks':counts,'all_source_pixel_checks':sum(counts.values())*576,
            'mapping_modes':modes,
            'gb2312_gbk_label_differences':[
                {'source_bytes':'A1A4','source_index':3,'gb2312_unicode':'U+30FB','gbk_unicode':'U+00B7','same_source_pixels':True},
                {'source_bytes':'A1AA','source_index':9,'gb2312_unicode':'U+2015','gbk_unicode':'U+2014','same_source_pixels':True}],
            'png_samples':png_reports,'existing_specimens':exported_disk,
            'notes':['Each of 28687 records checked using direct byte-bit addressing, independent of exporter big-endian integer decoding.',
                     'Both mapping modes checked against independently enumerated source slots, including all 65536 lead/trail pairs.',
                     'Complete BDF pixel roundtrips run in memory only; no BDF or raw glyph array written.',
                     'PNG CRC, dimensions, alpha, gaps and every visible/source pixel checked.',
                     '24x24 is a storage cell, not verified runtime advance; all ASCII ink remains within the left 12 columns.',
                     'GB2312 mode has 7445 mapped characters, GBK mode 21638; not full GBK or GB18030 coverage.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('--exporter',type=Path,default=Path(__file__).with_name('ps2_china_bitmap_export.py'))
    p.add_argument('--specimen-dir',type=Path)
    p.add_argument('--report',type=Path)
    args=p.parse_args()
    report=audit(args.source,args.exporter,args.specimen_dir)
    if args.report:
        with args.report.open('x', encoding='utf-8') as handle:
            handle.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':
    sys.exit(main())
