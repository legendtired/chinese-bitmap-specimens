from approved_psp_bwfont import before_psp_data, ID as PSP_ID
"""Approved one-item addition, source-native fixed PNG, immutable existing catalog."""
from pathlib import Path
import hashlib, json, os, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import alcatel715_specimen as a
from PIL import Image
read=lambda p:before_psp_data(p,json.loads((ROOT/p).read_text()))
sha=lambda b:hashlib.sha256(b).hexdigest()
digest=lambda x:sha(json.dumps(x,ensure_ascii=False,sort_keys=True).encode())
rows=read('data/catalog.json'); m=read('data/release-alcatel715.json')
assert len(rows)==len({r['id'] for r in rows})==241
assert m['addedIds']==['alcatel_ot715_13x14','ms_ming_14']
old=[r for r in rows if r['id'] not in m['addedIds']]
assert len(old)==239 and digest(old)==m['baseRowsSha256']
assert digest({r['id']:sha((ROOT/r['specimen']).read_bytes()) for r in old})==m['baseSpecimensSha256']
r=next(r for r in rows if r['id']==m['addedIds'][0])
assert digest(r)==m['addedRowSha256'] and r['priority']==2
recommended=[r['id'] for r in sorted(rows,key=lambda r:-r['priority']) if r['priority']>0]
assert recommended==m['baseRecommendedIds']+['alcatel_ot715_13x14'] and len(recommended)==17
assert (r['width'],r['height'],r['cellWidth'],r['cellHeight'])==(13,14,13,14)
p=ROOT/r['specimen']; assert sha(p.read_bytes())==r['specimenSha256']
im=Image.open(p); assert im.size==(r['specimenWidth'],r['specimenHeight']) and im.mode=='1'
assert len(a.LINES)==4 and r['text'].splitlines()==a.LINES[:3] and r['asciiText']==a.LINES[3]
assert r['nativeEvidence']['source_sha256']==a.EXPECTED
assert read('data/summary.json')['rows']==241
assert len([p for p in (ROOT/'fonts').glob('*.html') if p.stem not in ('sc_song_13', 'samsung_ypt6_14x16', PSP_ID, 'olympus_mrobe_mr100_12')])==241
assert read('data/collection-history.json')['batches'][-1]=={'sourceManifest':'release-alcatel715.json','ids':m['addedIds']}
with tempfile.TemporaryDirectory() as td:
    bad=Path(td)/'bad.dat';bad.write_bytes(b'not a firmware')
    try:a.render(bad,Path(td)/'bad.png')
    except ValueError:pass
    else:raise AssertionError('Wrong SHA accepted')
    assert not (Path(td)/'bad.png').exists()
    source=os.environ.get('ALCATEL715_SOURCE')
    if source:
        out=Path(td)/'fixed.png';a.render(source,out)
        assert out.read_bytes()==p.read_bytes()
        print('Alcatel exact private source-to-PNG regression passed.')
    else: print('Alcatel private source regression not run; set ALCATEL715_SOURCE.')
print('Alcatel: 241 items, 17 recommendations; all previous 239 rows/pixels/weights unchanged.')
