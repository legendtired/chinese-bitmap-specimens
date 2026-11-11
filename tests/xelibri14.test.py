from approved_emperor import IDS as EMPEROR_IDS
from approved_simsun import IDS as SIMSUN_IDS, before_simsun_bytes
from approved_hitech_adp3 import before_hitech_adp3_data
"""Approved native Xelibri14 fixed preview; immutable 246-row baseline."""
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys,tempfile
from PIL import Image
from approved_xelibri14 import before_xelibri14_file_sha, before_xelibri14_data, ID
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import xelibri14_specimen as source_tool
import generate_static as generator
sha=lambda data:hashlib.sha256(data).hexdigest()
digest=lambda value:sha(json.dumps(value,ensure_ascii=False,sort_keys=True).encode())
read=lambda path:before_hitech_adp3_data(path,json.loads((ROOT/path).read_text()))
rows=read('data/catalog.json');m=read('data/release-xelibri14.json')
assert m['addedIds']==[ID] and m['baseRows']==246 and m['totalRows']==247
assert m['baseCommit']=='47105314604031e27a0e2c91f6401a5eaabc4a65' and m['baseTree']=='9804e1e00f3fb87ec2e55e83612c37420b666364'
assert len(rows)==len({r['id'] for r in rows})==247
old=[r for r in rows if r['id']!=ID]
assert len(old)==246 and digest(old)==m['baseRowsSha256']
assert digest({r['id']:sha((ROOT/r['specimen']).read_bytes()) for r in old})==m['baseSpecimensSha256']
assert digest({r['id']:sha(before_simsun_bytes(f"fonts/{r['id']}.html")) for r in old})==m['basePagesSha256']
for path,expected in m['baseFilesSha256'].items():assert before_xelibri14_file_sha(path)==expected,path
assert [r['id'] for r in sorted(rows,key=lambda r:-r['priority']) if r['priority']>0]==m['baseRecommendedIds']
assert len(m['baseRecommendedIds'])==17
r=next(r for r in rows if r['id']==ID)
assert digest(r)==m['addedRowSha256']=='fd15be7edc789d01cccba172ff20dfb8e4ec5153fda4543f3f5fadf04fcaa03b'
assert r['sourceIndex']==284 and r['priority']==0
assert all(r[k]==14 for k in ('width','height','cellWidth','cellHeight','inkWidth','inkHeight'))
assert r['text'].splitlines()==list(source_tool.LINES) and r['asciiText']==source_tool.ASCII
assert r['asciiOrigin']=='native' and 'asciiPairing' not in r
assert not r['missing'] and not r['hanMissing'] and not r['asciiMissing']
assert r['nativeEvidence']['source_sha256']==source_tool.SOURCE_SHA256
assert r['nativeEvidence']['sourceBytes']==source_tool.SOURCE_BYTES
for key,expected in {'fontTable':4,'mappedCharacters':9509,'nonblankCharacters':9506,'nonblankCjk':9247,'gb2312Han':6763,'big5Han':6703,'big5ExpectedHan':13061,'printableAscii':95,'nonblankAscii':94,'hanRawMetricByte':14}.items():assert r['nativeEvidence'][key]==expected,key
assert r['scripts']==['简体','繁体']
assert sha((ROOT/'scripts/xelibri14_specimen.py').read_bytes())==m['sourceScriptSha256']=='1a0e201b6f3285ba1b9d2adfe51d65d0f8d45a3800934767c29e21eef1764c46'
assert sha((ROOT/'docs/siemens-xelibri14.md').read_bytes())==m['documentationSha256']=='f67a0f30dc5c870fd4b3551c4efd88b68343d6e5d062cdcc785f00d344e1b6d6'
summary=read('data/summary.json');assert summary['rows']==247 and summary['nativePngCount']==246
assert summary['standardAsciiComplete']==before_xelibri14_data('data/summary.json',summary,hitech_reversed=True)['standardAsciiComplete']+1
assert len([p for p in (ROOT/'fonts').glob('*.html') if p.stem not in (SIMSUN_IDS + EMPEROR_IDS) and p.stem not in ('hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')])==247
assert read('data/collection-history.json')['batches'][-1]=={'sourceManifest':'release-xelibri14.json','ids':[ID]}
order=json.loads(subprocess.check_output(['node','-e',"console.log(JSON.stringify(require('./app.js').filterCatalog(require('./data/catalog.json'), {}, '', 'recent').map(r=>r.id)))"],cwd=ROOT))
order=[ident for ident in order if ident not in (SIMSUN_IDS + EMPEROR_IDS) and ident not in ('hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')]
assert order[:4]==[ID,'ms_song_14','sc_song_13','samsung_ypt6_14x16']
index=(ROOT/'index.html').read_text();assert index.count(generator.article(r)+'\n')==1
assert (ROOT/'fonts'/f'{ID}.html').read_text()==generator.font_page(r)
png=ROOT/r['specimen'];im=Image.open(png)
assert im.mode=='L' and im.size==(168,50) and set(im.tobytes())=={0,255}
assert sha(png.read_bytes())==r['specimenSha256']==m['specimenSha256']==source_tool.SPECIMEN_SHA256=='047cf9b058da58738e47025836496fa71b2c6e660d54729ef43aec0749673b51'
assert sha(im.tobytes())=='b427b5ec97be3da58d83fa881e9c2cf76b4ef037d68e424e2d5bc7acccef2459'
assert all(im.getpixel((x,y))==255 for y in (14,15,16,17,32,33,34,35) for x in range(168))
bad=copy.deepcopy(rows);bad[-1]['name']+=' UNREVIEWED'
try:before_xelibri14_data('data/catalog.json',bad)
except AssertionError:pass
else:raise AssertionError('Unknown added row normalized')
bad=read('data/collection-history.json');bad['batches'][-1]['ids'].append('UNREVIEWED')
try:before_xelibri14_data('data/collection-history.json',bad)
except AssertionError:pass
else:raise AssertionError('Unknown added batch normalized')
with tempfile.TemporaryDirectory() as td:
    td=Path(td);bad=td/'bad.cla';bad.write_bytes(b'not firmware')
    try:source_tool.fixed_glyphs(bad.read_bytes())
    except ValueError:pass
    else:raise AssertionError('Wrong source accepted')
    cmd=[sys.executable,str(ROOT/'scripts/xelibri14_specimen.py'),'--source',str(bad),'--output',str(td/'arbitrary.png'),'--text','unapproved']
    assert subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode!=0
    assert not(td/'arbitrary.png').exists()
    source=os.environ.get('XELIBRI14_SOURCE')
    if source:
        original=Path(source).read_bytes();assert len(original)==source_tool.SOURCE_BYTES and sha(original)==source_tool.SOURCE_SHA256
        for i in range(2):
            out=td/f'fixed{i}.png';source_tool.render(source,out);assert out.read_bytes()==png.read_bytes()
        tampered=td/'tampered.cla';changed=bytearray(original);changed[0]^=1;tampered.write_bytes(changed)
        exact_png_alias=td/'source.png';exact_png_alias.write_bytes(original)
        hardlink=td/'source-hardlink.png';os.link(exact_png_alias,hardlink)
        source_symlink=td/'input-link.cla';source_symlink.symlink_to(Path(source).absolute())
        out_symlink=td/'output-link.png';out_symlink.symlink_to(td/'fixed0.png')
        dir_symlink=td/'dir-link';dir_symlink.symlink_to(td,target_is_directory=True)
        for inp,out in [(bad,td/'rejected.png'),(tampered,td/'rejected.png'),(source,td/'fixed0.png'),(source,Path(source)),(exact_png_alias,exact_png_alias),(source,hardlink),(source_symlink,td/'rejected.png'),(source,out_symlink),(source,dir_symlink/'rejected.png')]:
            before=out.read_bytes() if out.is_file() else None
            try:source_tool.render(inp,out)
            except (ValueError,OSError):pass
            else:raise AssertionError(f'Unsafe source/output accepted: {out.name}')
            if before is not None:assert out.read_bytes()==before
            else:assert not out.exists()
        assert Path(source).read_bytes()==original
        print('Xelibri14 exact source redraw twice and wrong-source/overwrite/hardlink/symlink safety regression passed.')
    else:print('Xelibri14 private source regression not run; set XELIBRI14_SOURCE. No fresh source-to-pixel claim is made without it.')
print('Xelibri14: 247 rows, 17 recommendations; all prior 246 rows/PNGs/pages unchanged; native ASCII retained.')
