"""Approved source-native MS Ming14 only; no ASCII substitution or other sizes."""
from pathlib import Path
import hashlib,json,os,sys,tempfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import msming14_specimen as m
rows=json.loads((ROOT/'data/catalog.json').read_text())
r=next(r for r in rows if r['id']=='ms_ming_14')
assert r['priority']==0 and r['sourceIndex']==278
assert (r['width'],r['height'],r['cellWidth'],r['cellHeight'])==(14,14,14,14)
assert r['asciiOrigin']=='absent' and r['asciiText']==''
assert r['asciiMissing']==list(map(chr,range(32,127)))
assert r['text'].splitlines()==m.LINES and not r['hanMissing']
assert r['nativeEvidence']['source_sha256']==m.EXPECTED
p=ROOT/r['specimen']; im=Image.open(p)
assert im.size==(168,32) and im.mode=='1'
assert hashlib.sha256(p.read_bytes()).hexdigest()==r['specimenSha256']=='d65ad17575f3e3406beb6e8ece9a722bbd56b8461dfc6c3bbe6f3a0f911811bc'
manifest=json.loads((ROOT/'data/release-alcatel715.json').read_text())
added=[r for r in rows if r['id'] in manifest['addedIds']]
assert hashlib.sha256(json.dumps(added,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==manifest['addedRowsSha256']
with tempfile.TemporaryDirectory() as td:
    bad=Path(td)/'bad.ttf';bad.write_bytes(b'not a font')
    try:m.render(bad,Path(td)/'bad.png')
    except ValueError:pass
    else:raise AssertionError('Wrong SHA accepted')
    assert not (Path(td)/'bad.png').exists()
    if os.environ.get('MSMING14_SOURCE'):
        out=Path(td)/'fixed.png';m.render(os.environ['MSMING14_SOURCE'],out)
        assert out.read_bytes()==p.read_bytes()
        print('MS Ming14 exact source-to-PNG regression passed.')
    else:print('MS Ming14 private source regression not run; set MSMING14_SOURCE.')
print('MS Ming14: exact fixed PNG, 14px only, no substitute ASCII, priority0.')
