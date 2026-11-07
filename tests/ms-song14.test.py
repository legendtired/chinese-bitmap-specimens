"""MS Song14 + explicitly external Arial13; immutable 245-row baseline."""
from approved_xelibri14 import before_xelibri14_data, ID as XELIBRI14_ID
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,struct,copy
from PIL import Image
from approved_ms_song14 import before_ms14_file_sha, before_ms14_data, ID
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import ms_song14_specimen as sc
import generate_static as generator
sha=lambda b:hashlib.sha256(b).hexdigest()
digest=lambda value:sha(json.dumps(value,ensure_ascii=False,sort_keys=True).encode())
read=lambda path:before_xelibri14_data(path,json.loads((ROOT/path).read_text()))
rows=read('data/catalog.json');m=read('data/release-ms-song14.json')
assert m['addedIds']==[ID] and m['baseRows']==245 and m['totalRows']==246
assert m['baseCommit']=='1b4a4d305c2d396fe1cce45aad90d91ae81e3bec' and m['baseTree']=='9d776566260e34460c5133808ee8d3f9c27e38ce'
assert len(rows)==len({r['id'] for r in rows})==246
old=[r for r in rows if r['id']!=ID]
assert len(old)==245 and digest(old)==m['baseRowsSha256']
assert digest({r['id']:sha((ROOT/r['specimen']).read_bytes()) for r in old})==m['baseSpecimensSha256']
assert digest({r['id']:sha((ROOT/'fonts'/f"{r['id']}.html").read_bytes()) for r in old})==m['basePagesSha256']
for path,expected in m['baseFilesSha256'].items():assert before_ms14_file_sha(path)==expected,path
assert [r['id'] for r in sorted(rows,key=lambda r:-r['priority']) if r['priority']>0]==m['baseRecommendedIds']
assert len(m['baseRecommendedIds'])==17
r=next(r for r in rows if r['id']==ID)
assert digest(r)==m['addedRowSha256']=='b02f20c4bdedf93cbca6c6a093c04a34512b69d662dd180b5266923ac4ef1dc8'
assert r['sourceIndex']==283 and r['priority']==0
assert (r['width'],r['height'],r['cellWidth'],r['cellHeight'],r['inkWidth'],r['inkHeight'])==(14,14,14,14,13,13)
assert r['text'].splitlines()==sc.LINES and r['asciiText']==sc.ASCII
assert not r['hanMissing'] and not r['asciiMissing']
assert r['asciiOrigin']=='not-in-source' and r['nativeEvidence']['printableAscii']==0
assert r['asciiPairing']['kind']=='user-selected-external-source' and r['asciiPairing']['originalRuntimePairingVerified'] is False
assert r['asciiPairing']['uid']=='0x100001f4' and r['asciiPairing']['cellHeight']==13 and r['asciiPairing']['scale']==[1,1]
assert r['asciiPairing']['sourceSha256']==sc.ARIAL_SHA256 and r['nativeEvidence']['source_sha256']==sc.SOURCE_SHA256
assert r['nativeEvidence']['gb2312Han']==6763 and r['nativeEvidence']['big5Han']==4383 and r['nativeEvidence']['big5ExpectedHan']==13061
assert r['scripts']==['简体'] and r['nativeEvidence']['mappedCharacters']==7429
assert sha((ROOT/'scripts/ms_song14_specimen.py').read_bytes())==m['sourceScriptSha256']=='bf8717d35db62743f4a143e58c317d961d6dd3a4eaa56d7263d0288c2dba76db'
assert sha((ROOT/'docs/ms-song14.md').read_bytes())==m['documentationSha256']
summary=read('data/summary.json');assert summary['rows']==246 and summary['nativePngCount']==245
assert len([p for p in (ROOT/'fonts').glob('*.html') if p.stem != XELIBRI14_ID])==246
assert read('data/collection-history.json')['batches'][-1]=={'sourceManifest':'release-ms-song14.json','ids':[ID]}
order=json.loads(subprocess.check_output(['node','-e',"console.log(JSON.stringify(require('./app.js').filterCatalog(require('./data/catalog.json'), {}, '', 'recent').map(r=>r.id)))"],cwd=ROOT))
assert [ident for ident in order if ident != XELIBRI14_ID][:3]==[ID,'sc_song_13','samsung_ypt6_14x16']
index=(ROOT/'index.html').read_text();assert index.count(generator.article(r)+'\n')==1
assert (ROOT/'fonts/ms_song_14.html').read_text()==generator.font_page(r)
png=ROOT/r['specimen'];im=Image.open(png)
assert im.mode=='RGBA' and im.size==(210,32)
assert sha(png.read_bytes())==r['specimenSha256']==m['specimenSha256']=='a706f62e4fa32e81cbe99e306835dd3f461af3b7e0b3ac0f7dd9973b3d95f78e'
assert set(im.getdata())=={(0,0,0,0),(0,0,0,255)}
assert sha(im.crop((0,0,168,14)).tobytes())=='58f2e265a793f61d566e79adc7414dc5fee9d309fef840e2a555f1fdbe15e33c'
assert not im.crop((168,0,210,14)).getbbox()
assert not im.crop((0,14,210,18)).getbbox() and not im.crop((0,31,210,32)).getbbox()
# Normalization must refuse an unknown change to the newly added row/batch.
bad=copy.deepcopy(rows);bad[-1]['name']+=' UNREVIEWED'
try:before_ms14_data('data/catalog.json',bad,xelibri14_reversed=True)
except AssertionError:pass
else:raise AssertionError('Changed added row was silently normalized')
bad=read('data/collection-history.json');bad['batches'][-1]['ids'].append('UNREVIEWED')
try:before_ms14_data('data/collection-history.json',bad,xelibri14_reversed=True)
except AssertionError:pass
else:raise AssertionError('Changed added batch was silently normalized')
with tempfile.TemporaryDirectory() as td:
    td=Path(td);bad=td/'bad';bad.write_bytes(b'not a font')
    for fn in (sc.chinese,sc.arial):
        try:fn(b'wrong bytes')
        except ValueError:pass
        else:raise AssertionError('Wrong SHA accepted')
    source=os.environ.get('MS_SONG14_SOURCE');arial=os.environ.get('MS_SONG14_ARIAL_SOURCE')
    if source and arial:
        for i in range(2):
            out=td/f'fixed{i}.png';sc.render(source,arial,out);assert out.read_bytes()==png.read_bytes()
        for a,b in ((bad,arial),(source,bad)):
            out=td/'invalid.png'
            try:sc.render(a,b,out)
            except ValueError:pass
            else:raise AssertionError('Wrong source accepted')
            assert not out.exists()
        out=td/'fixed0.png';saved=out.read_bytes()
        try:sc.render(source,arial,out)
        except FileExistsError:pass
        else:raise AssertionError('Existing output overwritten')
        assert out.read_bytes()==saved
        # FontTools independently resolves original cmap/EBLC locations; Pillow
        # decodes the continuous MSB stream, without using renderer functions.
        from fontTools.ttLib import TTFont
        font=TTFont(source);raw=Path(source).read_bytes();cm=font.getBestCmap()
        strike=next(s for s in font['EBLC'].strikes if (s.bitmapSizeTable.ppemX,s.bitmapSizeTable.ppemY)==(14,14))
        byname={name:(sub.metrics,loc) for sub in strike.indexSubTables for name,loc in zip(sub.names,sub.locations)}
        ebdt=font.reader.tables['EBDT'].offset;expected=Image.new('RGBA',im.size,(0,0,0,0))
        for li,line in enumerate(sc.LINES):
            x0=0
            for c in line:
                met,(start,end)=byname[cm[ord(c)]];mask=Image.frombytes('1',(met.width*met.height,1),raw[ebdt+start:ebdt+end])
                for j,v in enumerate(mask.getdata()):
                    if v:expected.putpixel((x0+met.horiBearingX+j%met.width,li*18+12-met.horiBearingY+j//met.width),(0,0,0,255))
                x0+=met.horiAdvance
        # Independent GDR integer-reservoir parser for only the fixed ASCII line.
        data=Path(arial).read_bytes();u=lambda p:int.from_bytes(data[p:p+4],'little');p=u(32);count=u(p);p+=4;chosen=None
        for _ in range(count):
            uid=u(p);n=u(p+15);secs=[struct.unpack_from('<HHII',data,p+19+i*12) for i in range(n)]
            if uid==0x100001f4:chosen=secs;assert list(data[p+4:p+11])==[0,0,1,13,11,15,15]
            p+=19+n*12
        assert chosen is not None
        families={};n=u(p);p+=4
        for _ in range(n):
            assert data[p]&3==2
            length=data[p]>>2;p+=1;name=data[p:p+length].decode('ascii');p+=length+1;nfaces=u(p);p+=4
            families[name]=[struct.unpack_from('<IBB',data,p+6*i) for i in range(nfaces)];p+=6*nfaces
        assert families['Arial'].count((0x100001f4,1,1))==1
        x0=0
        for c in sc.ASCII:
            cp=ord(c);lo,hi,co,bo=next(s for s in chosen if s[0]<=cp<=s[1]);at=co+4+8*(cp-lo)
            off=int.from_bytes(data[at:at+2],'little');asc,h,left,advance,right=struct.unpack_from('5b',data,at+2);w=advance-left-right
            reservoir=int.from_bytes(data[bo+4+off:bo+4+u(bo)],'little');rows2=[]
            while len(rows2)<h:
                literal=reservoir&1;nr=(reservoir>>1)&15;reservoir>>=5;assert 1<=nr<=h-len(rows2)
                for _ in range(nr if literal else 1):
                    val=reservoir&((1<<w)-1);reservoir>>=w;rows2.extend([val]*(1 if literal else nr))
            for y,val in enumerate(rows2):
                for x in range(w):
                    if (val>>x)&1:expected.putpixel((x0+left+x,29-asc+y),(0,0,0,255))
            x0+=advance
        assert x0==210 and expected.tobytes()==im.tobytes()
        print('MS Song14 dual source redraw and independent FontTools/Pillow + GDR reservoir pixel regression passed.')
    else:print('MS Song14 private source regression not run; set MS_SONG14_SOURCE and MS_SONG14_ARIAL_SOURCE (requires FontTools).')
print('MS Song14: 246 rows, 17 recommendations, all prior 245 rows/PNGs/pages unchanged; external Arial not counted as original ASCII.')
