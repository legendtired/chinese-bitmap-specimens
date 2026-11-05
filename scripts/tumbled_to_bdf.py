#!/usr/bin/env python3
"""Export TUMBLED_18/24 native glyph/shape text to Unicode BDF (no rasterizer)."""
import argparse
import hashlib
import json
from pathlib import Path

def load_font(folder):
    folder=Path(folder)
    def read_source(relative):
        source=folder/relative
        try:
            source.resolve().relative_to(folder.resolve())
        except ValueError:
            raise ValueError(f'Source path escapes font folder: {relative}')
        return source.read_bytes()
    config_raw=read_source('font.json')
    config=json.loads(config_raw.decode('utf-8'))
    if config.get('name') not in ('TUMBLED_18','TUMBLED_24') or config.get('height') not in (18,24):
        raise ValueError('Only TUMBLED_18 and TUMBLED_24 native source folders are supported')
    if config['name'] != f'TUMBLED_{config["height"]}': raise ValueError('Conflicting name/height')
    nominal=config['height']; used={'font.json':config_raw}; glyphs=[]; shapes={}
    def shape(name):
        if not name or Path(name).name != name or name in ('.','..'):
            raise ValueError('Unsafe shape name')
        if name not in shapes:
            rel='shapes/'+name+'.txt';raw=read_source(rel);used[rel]=raw
            lines=raw.decode('utf-8').split('\n')
            top,left=map(int,lines[0].split())
            pixels=set()
            for y,line in enumerate(lines[1:]):
                for x,v in enumerate(line):
                    if v=='#': pixels.add((x+left,y+top))
                    elif v not in (' ','\r'): raise ValueError(f'Unexpected shape character in {rel}')
            shapes[name]=pixels
        return shapes[name]
    files=sorted((folder/'glyphs').glob('*.txt'))
    if not files: raise ValueError('No glyph files')
    seen=set()
    for f in files:
        if not f.stem.isdecimal(): raise ValueError(f'Variant filename requires an explicit regional selection: {f.name}')
        cp=int(f.stem)
        if cp>0x10ffff or 0xd800<=cp<=0xdfff or cp in seen: raise ValueError('Invalid/duplicate Unicode scalar')
        seen.add(cp);rel='glyphs/'+f.name;raw=read_source(rel);used[rel]=raw
        lines=raw.decode('utf-8').splitlines();advance=int(lines[0]);pixels=set()
        if not 0<=advance<=4096: raise ValueError('Invalid advance')
        components=0
        for line in lines[1:]:
            if not line.strip(): continue
            dy,dx,name=line.split();dy,dx=int(dy),int(dx);components+=1
            pixels.update((x+dx,y+dy) for x,y in shape(name))
        if pixels:
            left=min(x for x,y in pixels);top=min(y for x,y in pixels)
            right=max(x for x,y in pixels)+1;bottom=max(y for x,y in pixels)+1
        else: left=top=right=bottom=0
        if max(right-left,bottom-top)>4096: raise ValueError('Excessive glyph dimensions')
        glyphs.append(dict(codepoint=cp,advance=advance,pixels=pixels,left=left,top=top,
                           width=right-left,height=bottom-top,components=components))
    fingerprint=hashlib.sha256()
    for name,data in sorted(used.items()):
        fingerprint.update(name.encode('utf-8')+b'\0'+hashlib.sha256(data).digest())
    info=dict(name=config['name'],nominal_height=nominal,glyphs=len(glyphs),
              used_source_files=len(used),source_fingerprint_sha256=fingerprint.hexdigest(),
              fingerprint_algorithm='Sorted relative path UTF-8 + NUL + raw SHA256 digest of each used source file',
              ordinary_ascii_glyphs=sum(32<=g['codepoint']<127 for g in glyphs))
    return sorted(glyphs,key=lambda g:g['codepoint']),info

def render_bdf(glyphs,info):
    nominal=info['nominal_height'];ink=[g for g in glyphs if g['pixels']]
    xmin=min([0]+[g['left'] for g in ink]);xmax=max([0]+[g['left']+g['width'] for g in ink])
    ymin=min([0]+[g['top'] for g in ink]);ymax=max([nominal]+[g['top']+g['height'] for g in ink])
    ascent=nominal-ymin;descent=ymax-nominal
    lines=['STARTFONT 2.1','COMMENT Native shape pixels with source bearings and advances; no fallback or synthetic bold',
           'COMMENT Baseline is defined at source font.json height; ascent/descent expanded to contain every glyph',
           'COMMENT Source fingerprint SHA256 '+info['source_fingerprint_sha256'],
           f'FONT -cjkarchive-{info["name"]}-medium-r-normal--{nominal}-{nominal*10}-72-72-p-0-ISO10646-1',f'SIZE {nominal} 72 72',
           f'FONTBOUNDINGBOX {xmax-xmin} {ymax-ymin} {xmin} {nominal-ymax}',
           'STARTPROPERTIES 6',f'FONT_ASCENT {ascent}',f'FONT_DESCENT {descent}',
           f'PIXEL_SIZE {nominal}',f'SOURCE_LINE_HEIGHT {nominal}',
           'CHARSET_REGISTRY "ISO10646"','CHARSET_ENCODING "1"','ENDPROPERTIES',f'CHARS {len(glyphs)}']
    for g in glyphs:
        cp=g['codepoint'];w=g['width'];h=g['height'];left=g['left'];top=g['top'];advance=g['advance']
        yoff=nominal-top-h if g['pixels'] else 0
        lines += [f'STARTCHAR uni{cp:04X}',f'ENCODING {cp}',f'SWIDTH {round(advance*1000/nominal)} 0',
                  f'DWIDTH {advance} 0',f'BBX {w} {h} {left} {yoff}','BITMAP']
        padded=((w+7)//8)*8
        for y in range(top,top+h):
            bits=sum(1<<(padded-1-(x-left)) for x in range(left,left+w) if (x,y) in g['pixels'])
            lines.append(f'{bits:0{padded//4}X}')
        lines.append('ENDCHAR')
    lines.append('ENDFONT')
    from collections import Counter
    report=dict(info,source_coordinate_bounds=[xmin,ymin,xmax,ymax],
                font_bounding_box=[xmax-xmin,ymax-ymin,xmin,nominal-ymax],
                ascent=ascent,descent=descent,advances=dict(sorted(Counter(g['advance'] for g in glyphs).items())),
                multi_component_glyphs=sum(g['components']>1 for g in glyphs),
                empty_glyphs=sum(not g['pixels'] for g in glyphs),
                note='The catalog sample dimensions are not whole-font clipping bounds. Native nominal line height is retained in SOURCE_LINE_HEIGHT; BDF ascent/descent include all pixels.')
    return '\n'.join(lines)+'\n',report

def preflight_outputs(output, report, source):
    """Do not overwrite inputs, prior outputs, symlinks, or aliasing targets."""
    output, report, source = Path(output), Path(report), Path(source)
    targets = (output, report)
    resolved = [p.resolve() for p in targets]
    if resolved[0] == resolved[1]:
        raise ValueError('Output and report must be different targets, including resolved aliases')
    source_resolved = source.resolve()
    for target, real in zip(targets, resolved):
        if real == source_resolved:
            raise ValueError('Output/report must not replace the input')
        if target.exists() or target.is_symlink():
            raise ValueError(f'Refusing existing output/report target: {target}')
        if not target.parent.is_dir():
            raise ValueError(f'Output/report parent directory does not exist: {target.parent}')
    return targets


def write_outputs(output, report, source, bdf, metadata):
    """Exclusively create both files; remove only our own files after failure."""
    import os
    targets = preflight_outputs(output, report, source)
    payloads = (bdf.encode('ascii'), (json.dumps(metadata, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    opened = []
    try:
        # Open both before writing either. 'xb' uses O_EXCL and refuses symlinks.
        for target in targets:
            stream = target.open('xb')
            st = os.fstat(stream.fileno())
            opened.append((target, stream, (st.st_dev, st.st_ino)))
        for (_, stream, _), payload in zip(opened, payloads):
            stream.write(payload)
            stream.flush()
        for _, stream, _ in opened:
            stream.close()
    except BaseException:
        for target, stream, identity in opened:
            try:
                stream.close()
            except OSError:
                pass
            try:
                st = target.lstat()
                if (st.st_dev, st.st_ino) == identity:
                    target.unlink()
            except OSError:
                pass
        raise

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('output',type=Path);p.add_argument('--report',type=Path);a=p.parse_args()
    try:
        target=a.report or a.output.with_suffix(a.output.suffix+'.json')
        preflight_outputs(a.output,target,a.folder)
        glyphs,info=load_font(a.folder);bdf,report=render_bdf(glyphs,info)
        write_outputs(a.output,target,a.folder,bdf,report)
        print(f'{len(glyphs)} glyphs; bounds {report["font_bounding_box"]}; source line height {info["nominal_height"]}')
    except (OSError,ValueError,KeyError,IndexError,TypeError) as e:p.exit(1,f'Error: {e}\n')
if __name__=='__main__':main()
