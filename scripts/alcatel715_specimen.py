"""Offline fixed OT-715 specimen. No network, firmware execution or font export."""
from pathlib import Path
import struct, hashlib, argparse
from PIL import Image
EXPECTED = '00028ebf54a5b7dca4ae4d20336d89c74f2f7c354f36f3f19a381c79ac285462'
LINES = ['视野无限广，窗外有蓝天。','視野無限廣，窗外有藍天。','汉漢龙龍龟龜国國爱愛梦夢','0123456789 AaBb GgMm !?:+-.']
def render(source, output):
    D=Path(source).read_bytes()
    if hashlib.sha256(D).hexdigest()!=EXPECTED:
        raise ValueError('Source SHA256 mismatch')
    R=0x576288;assert struct.unpack_from('<I',D,R+4)[0]==0x1000007a
    BASE=R+16
    fonts=[]
    for index in [3]:
        fid,offset,desc=struct.unpack_from('<III',D,R+20+index*12)
        height=desc&255;pages=desc>>16;start=BASE+offset
        nextoffset=struct.unpack_from('<I',D,R+20+(index+1)*12+4)[0];end=BASE+nextoffset
        glyphs={};groups=[];padding_errors=[]
        for i in range(pages):
            page,count,kind,fixedw,mo,go=struct.unpack_from('<4BII',D,start+i*12)
            assert kind in (0,1) and fixedw==0
            assert start+mo+count*3<=end
            entries=[tuple(D[start+mo+j*3:start+mo+j*3+3]) for j in range(count)]
            assert [e[0] for e in entries]==sorted(set(e[0] for e in entries))
            bucket_count=max(e[1] for e in entries)+1
            ptrs=struct.unpack_from('<'+'I'*bucket_count,D,start+go)
            group={'page':page,'count':count,'map_offset':hex(start+mo),'pointer_offset':hex(start+go),'buckets':[]}
            for bi,ptr in enumerate(ptrs):
                gstart=start+ptr;width=D[gstart];assert 1<=width<=32
                inds=[e[2] for e in entries if e[1]==bi];assert inds
                assert sorted(inds)==list(range(max(inds)+1))
                rowbytes=(height+7)//8;length=width*rowbytes
                assert gstart+1+length*(max(inds)+1)<=end
                group['buckets'].append({'width':width,'glyph_count':len(inds),'source_start':hex(gstart),'source_end':hex(gstart+1+length*(max(inds)+1))})
            for low,bi,gi in entries:
                cp=(page<<8)|low;assert cp not in glyphs
                gstart=start+ptrs[bi];w=D[gstart];bc=(height+7)//8;n=w*bc;pos=gstart+1+gi*n;raw=D[pos:pos+n]
                cols=[int.from_bytes(raw[k*bc:(k+1)*bc],'big') for k in range(w)]
                padding=(bc*8-height)
                if any(c&((1<<padding)-1) for c in cols):padding_errors.append(cp)
                rows=[''.join(str((v>>(bc*8-1-y))&1) for v in cols) for y in range(height)]
                glyphs[cp]={'width':w,'rows':rows,'source_offset':pos,'raw_length':n,'raw_sha256':hashlib.sha256(raw).hexdigest(),'page_table_offset':start+i*12,'mapping_entry_offset':start+mo+entries.index((low,bi,gi))*3}
            groups.append(group)
        assert not padding_errors
        fonts.append({'index':index,'id':hex(fid),'height':height,'page_count':pages,'start':hex(start),'end':hex(end),'descriptor':hex(desc),'glyphs':glyphs,'groups':groups})

    g=fonts[0]['glyphs']
    assert len(g)==10402 and fonts[0]['height']==14
    w=max(sum(g[ord(c)]['width']+1 for c in line)-1 for line in LINES)
    image=Image.new('1',(w,68),1)
    for li,line in enumerate(LINES):
        x0=0
        for c in line:
            glyph=g[ord(c)]
            for y,row in enumerate(glyph['rows']):
                for x,bit in enumerate(row):
                    if bit=='1': image.putpixel((x0+x,li*18+y),0)
            x0+=glyph['width']+1
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    image.save(output)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args(); render(a.source,a.output)
