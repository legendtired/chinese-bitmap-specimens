from approved_simsun import IDS as SIMSUN_IDS, before_simsun_bytes
"""SC_Song13 + explicitly external Arial13; immutable 244-row baseline."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,struct,copy
from PIL import Image
from approved_sc_song13 import before_sc13_file_sha, before_sc13_data, ID
from approved_ms_song14 import before_ms14_data, ID as MS14_ID
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import sc_song13_specimen as sc
import generate_static as generator
sha=lambda b:hashlib.sha256(b).hexdigest()
digest=lambda value:sha(json.dumps(value,ensure_ascii=False,sort_keys=True).encode())
read=lambda path:before_ms14_data(path,json.loads((ROOT/path).read_text()))
rows=read('data/catalog.json');m=read('data/release-sc-song13.json')
assert m['addedIds']==[ID] and m['baseRows']==244 and m['totalRows']==245
assert m['baseCommit']=='fc60511282cb071fe047f75cb069537a2cd0db1e' and m['baseTree']=='eb9a228cc3540d5e59ef18e614716e7abb43da39'
assert len(rows)==len({r['id'] for r in rows})==245
old=[r for r in rows if r['id']!=ID]
assert len(old)==244 and digest(old)==m['baseRowsSha256']
assert digest({r['id']:sha((ROOT/r['specimen']).read_bytes()) for r in old})==m['baseSpecimensSha256']
assert digest({r['id']:sha(before_simsun_bytes(f"fonts/{r['id']}.html")) for r in old})==m['basePagesSha256']
for path,expected in m['baseFilesSha256'].items():assert before_sc13_file_sha(path)==expected,path
assert [r['id'] for r in sorted(rows,key=lambda r:-r['priority']) if r['priority']>0]==m['baseRecommendedIds']
assert len(m['baseRecommendedIds'])==17
r=next(r for r in rows if r['id']==ID)
assert digest(r)==m['addedRowSha256']=='00fec3d55dc184f7d706e62f2cbc4509d8b003ccd21065b11b37baad78fa5af0'
assert r['sourceIndex']==282 and r['priority']==0
assert (r['width'],r['height'],r['cellWidth'],r['cellHeight'],r['inkWidth'],r['inkHeight'])==(13,13,13,13,12,12)
assert r['text'].splitlines()==sc.LINES and r['asciiText']==sc.ASCII
assert not r['hanMissing'] and not r['asciiMissing']
assert r['asciiOrigin']=='not-in-source' and r['nativeEvidence']['printableAscii']==0
assert r['asciiPairing']['kind']=='user-selected-external-source' and r['asciiPairing']['originalRuntimePairingVerified'] is False
assert r['asciiPairing']['uid']=='0x100001f4' and r['asciiPairing']['cellHeight']==13 and r['asciiPairing']['scale']==[1,1]
assert r['asciiPairing']['sourceSha256']==sc.ARIAL_SHA256 and r['nativeEvidence']['source_sha256']==sc.SOURCE_SHA256
assert r['nativeEvidence']['basicHan']==20902 and r['nativeEvidence']['compatibilityHan']==21 and r['nativeEvidence']['extensionAHan']==0
assert sha((ROOT/'scripts/sc_song13_specimen.py').read_bytes())==m['sourceScriptSha256']=='b734d513b8ad7fecd19a14fae3f12bad7cb0490c5129c8e5ecd59db637776647'
assert sha((ROOT/'docs/sc-song13.md').read_bytes())==m['documentationSha256']
summary=read('data/summary.json');assert summary['rows']==245 and summary['nativePngCount']==244
assert len([p for p in (ROOT/'fonts').glob('*.html') if p.stem not in SIMSUN_IDS and p.stem not in (MS14_ID, 'siemens_xelibri_14', 'hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')])==245
assert read('data/collection-history.json')['batches'][-1]=={'sourceManifest':'release-sc-song13.json','ids':[ID]}
order=json.loads(subprocess.check_output(['node','-e',"console.log(JSON.stringify(require('./app.js').filterCatalog(require('./data/catalog.json'), {}, '', 'recent').map(r=>r.id)))"],cwd=ROOT))
assert [ident for ident in order if ident not in SIMSUN_IDS and ident not in (MS14_ID, 'siemens_xelibri_14', 'hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')][:3]==[ID,'samsung_ypt6_14x16','olympus_mrobe_mr100_12']
index=(ROOT/'index.html').read_text();assert index.count(generator.article(r)+'\n')==1
assert (ROOT/'fonts/sc_song_13.html').read_text()==generator.font_page(r)
png=ROOT/r['specimen'];im=Image.open(png)
assert im.mode=='RGBA' and im.size==(210,47)
assert sha(png.read_bytes())==r['specimenSha256']==m['specimenSha256']=='c9cdc3117e8f9083fd2f2383607b69fccda43a8cd46fd99fc446259c916be2e8'
assert set(im.getdata())=={(0,0,0,0),(0,0,0,255)}
assert sha(im.crop((0,0,156,30)).tobytes())=='f9071421793eda1103d7cb7ead9866a8cb16c84cf78780d35b7a6769895474e2'
assert not im.crop((156,0,210,30)).getbbox()
assert all(im.getpixel((x,y))==(0,0,0,0) for y in (*range(13,17),*range(30,34)) for x in range(210))
# Normalization must refuse an unknown change to the newly added row/batch.
bad=copy.deepcopy(rows);bad[-1]['name']+=' UNREVIEWED'
try:before_sc13_data('data/catalog.json',bad,ms14_reversed=True)
except AssertionError:pass
else:raise AssertionError('Changed added row was silently normalized')
bad=read('data/collection-history.json');bad['batches'][-1]['ids'].append('UNREVIEWED')
try:before_sc13_data('data/collection-history.json',bad,ms14_reversed=True)
except AssertionError:pass
else:raise AssertionError('Changed added batch was silently normalized')
with tempfile.TemporaryDirectory() as td:
    td=Path(td);bad=td/'bad';bad.write_bytes(b'not a font')
    for fn in (sc.chinese,sc.arial):
        try:fn(b'wrong bytes')
        except ValueError:pass
        else:raise AssertionError('Wrong SHA accepted')
    source=os.environ.get('SC_SONG13_SOURCE');arial=os.environ.get('SC_SONG13_ARIAL_SOURCE')
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
        strike=next(s for s in font['EBLC'].strikes if (s.bitmapSizeTable.ppemX,s.bitmapSizeTable.ppemY)==(13,13))
        byname={name:(sub.metrics,loc) for sub in strike.indexSubTables for name,loc in zip(sub.names,sub.locations)}
        ebdt=font.reader.tables['EBDT'].offset;expected=Image.new('RGBA',im.size,(0,0,0,0))
        for li,line in enumerate(sc.LINES):
            x0=0
            for c in line:
                met,(start,end)=byname[cm[ord(c)]];mask=Image.frombytes('1',(met.width*met.height,1),raw[ebdt+start:ebdt+end])
                for j,v in enumerate(mask.getdata()):
                    if v:expected.putpixel((x0+met.horiBearingX+j%met.width,li*17+11-met.horiBearingY+j//met.width),(0,0,0,255))
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
                    if (val>>x)&1:expected.putpixel((x0+left+x,45-asc+y),(0,0,0,255))
            x0+=advance
        assert x0==210 and expected.tobytes()==im.tobytes()
        print('SC_Song13 dual source redraw and independent FontTools/Pillow + GDR reservoir pixel regression passed.')
    else:print('SC_Song13 private source regression not run; set SC_SONG13_SOURCE and SC_SONG13_ARIAL_SOURCE (requires FontTools).')
print('SC_Song13: 245 rows, 17 recommendations, all prior 244 rows/PNGs/pages unchanged; external Arial not counted as original ASCII.')
