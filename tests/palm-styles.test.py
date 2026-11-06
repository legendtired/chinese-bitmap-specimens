from pathlib import Path
import json,hashlib,struct,sys
R=Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/catalog.json').read_text());m=json.loads((R/'data/release-palm-styles.json').read_text())
base=[r for r in rows if r['id'] in m['baseIds']];new=[r for r in rows if r['id'] in m['addedIds']]
assert len(rows)==225 and len(base)==221 and len(new)==4
for group,key in [(base,'baseRowsSha256'),(new,'addedRowsSha256')]: assert hashlib.sha256(json.dumps(group,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m[key]
assert [r['id'] for r in rows[-4:]]==m['addedIds']
sys.path.insert(0,str(R/'scripts'));import cjkos_to_bdf as c
for r in new:
 assert r['priority']==0 and r['width']==r['height']==12
 assert r['missing']==[] and not r['asciiText']
 assert c.SOURCES[r['nativeEvidence']['source_sha256']]==(12,'gb2312' if r['scripts']==['简体'] else 'big5',True)
 b=(R/r['specimen']).read_bytes();assert hashlib.sha256(b).hexdigest()==r['specimenSha256'];assert struct.unpack('>II',b[16:24])==(r['specimenWidth'],r['specimenHeight'])
assert not any(r['id']=='palm_cjkos_fgb12stf' for r in rows)
h=json.loads((R/'data/collection-history.json').read_text());assert h['batches'][-1]['ids']==m['addedIds']
print('Palm styles: 4 exact additions, 221 unchanged rows, checked source hashes and fixed PNGs.')
