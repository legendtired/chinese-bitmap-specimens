"""Fixed-source pixels, PNG identity and fail-closed file safety."""
from pathlib import Path
import hashlib, importlib.util, os, subprocess, sys, tempfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/windows31_mingli20_specimen.py'
spec=importlib.util.spec_from_file_location('fixed_source',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=Image.open(ROOT/'assets/specimens/windows31_mingli20.png');b=Image.open(ROOT/'assets/specimens/windows31_mingli20_4x.png')
assert a.size==(m.WIDTH*len(m.TEXT),m.HEIGHT)
assert b.size==(a.width*4,a.height*4)
assert b.tobytes()==a.resize(b.size,Image.Resampling.NEAREST).tobytes()
assert sha(ROOT/'assets/specimens/windows31_mingli20.png')==m.PNG_SHA256[1]
assert sha(ROOT/'assets/specimens/windows31_mingli20_4x.png')==m.PNG_SHA256[4]

def rejected(fn):
    try:fn()
    except (ValueError,OSError):return
    raise AssertionError('Unsafe action accepted')
with tempfile.TemporaryDirectory() as d:
    d=Path(d);bad=d/'bad-source';bad.write_bytes(b'not original source')
    rejected(lambda:m.fixed_image(b'bad'))
    rejected(lambda:m.render(bad,d/'bad.png'))
    assert not(d/'bad.png').exists()
    cmd=[sys.executable,str(SCRIPT),'--source',str(bad),'--output',str(d/'bad.png'),'--text','unapproved']
    assert subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode!=0
    assert not(d/'bad.png').exists()
    source=os.environ.get('WINDOWS31_MINGLI20_SOURCE')
    if source:
        source=Path(source).absolute();original=source.read_bytes()
        before=sha(source)
        # Independently enumerate three original code ranges, then decode with Pillow.
        independent=Image.new('1',(20*len(m.TEXT),20),1)
        for i,char in enumerate(m.TEXT):
            code=int.from_bytes(char.encode('big5'),'big')
            ranges=((0xa140,0xa3e0,0),(0xa440,0xc67e,684),(0xc940,0xf9d5,6085))
            start,end,base=next(r for r in ranges if r[0]<=code<=r[1])
            trails=list(range(0x40,0x7f))+list(range(0xa1,0xff))
            slot=base+((code>>8)-(start>>8))*157+trails.index(code&255)
            offset=5408+slot*60
            cell=Image.frombytes('1',(20,20),original[offset:offset+60],'raw','1',3,1)
            independent.paste(cell,(20*i,0))
        assert independent.tobytes()==a.tobytes()
        for scale in (1,4):
            out=d/f'fixed{scale}.png';m.render(source,out,scale)
            assert sha(out)==m.PNG_SHA256[scale]
            assert out.read_bytes()==(ROOT/f'assets/specimens/windows31_mingli20{"" if scale==1 else "_4x"}.png').read_bytes()
        rejected(lambda:m.render(source,d/'fixed1.png'))
        rejected(lambda:m.render(source,source))
        rejected(lambda:m.render(source,d/'bad.png',2))
        changed=bytearray(original);changed[0]^=1
        tampered=d/'tampered';tampered.write_bytes(changed)
        rejected(lambda:m.render(tampered,d/'bad.png'))
        source_link=d/'input-link';source_link.symlink_to(source)
        rejected(lambda:m.render(source_link,d/'bad.png'))
        out_link=d/'output-link.png';out_link.symlink_to(d/'fixed1.png')
        rejected(lambda:m.render(source,out_link))
        dir_link=d/'dir-link';dir_link.symlink_to(d,target_is_directory=True)
        rejected(lambda:m.render(source,dir_link/'bad.png'))
        rejected(lambda:m.render(dir_link/'tampered',d/'bad.png'))
        copy=d/'source-copy.png';copy.write_bytes(original)
        hardlink=d/'source-hardlink.png';os.link(copy,hardlink)
        rejected(lambda:m.render(copy,hardlink))
        rejected(lambda:m.render(hardlink,d/'bad.png'))
        assert copy.read_bytes()==original
        pipe=d/'fifo';os.mkfifo(pipe)
        rejected(lambda:m.render(pipe,d/'bad.png'))
        assert sha(source)==before and not(d/'bad.png').exists()
        print('windows31_mingli20: private-source exact pixels and file safety PASS')
    else:
        print('windows31_mingli20: private-source validation SKIPPED; set WINDOWS31_MINGLI20_SOURCE')
print('windows31_mingli20: fixed PNG and wrong-source checks PASS')
