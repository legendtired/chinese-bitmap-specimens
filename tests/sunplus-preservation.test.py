"""Final integrated Sunplus release preserves the complete 227-row baseline."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1]
rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id']!='samsung_r208_16'];m=json.loads((R/'data/release-sunplus.json').read_text())
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
base=[r for r in rows if r['id'] in m['baseIds']];added=[r for r in rows if r['id'] in m['addedIds']]
assert len(rows)==len({r['id'] for r in rows})==m['totalRows']==229
assert len(base)==m['baseRows']==227 and [r['id'] for r in base]==m['baseIds']
assert digest(base)==m['baseRowsSha256'] and digest(added)==m['addedRowsSha256']
assert [r['id'] for r in added]==m['addedIds']
assert [r['id'] for r in rows if r.get('priority',0)>0]==m['preservedRecommendedIds']
assert len(m['preservedRecommendedIds'])==13
for r in base:assert hashlib.sha256((R/r['specimen']).read_bytes()).hexdigest()==r['specimenSha256'],r['id']
indices=[r['sourceIndex'] for r in rows if r.get('sourceIndex') is not None]
assert len(indices)==len(set(indices))
h=json.loads((R/'data/collection-history.json').read_text())
assert next(b for b in h['batches'] if b['sourceManifest']=='release-sunplus.json')=={'sourceManifest':'release-sunplus.json','ids':m['addedIds']}
s=json.loads((R/'data/summary.json').read_text());assert s['rows']==230 and s['nativePngCount']==229
for k in ['standardAsciiComplete','ordinaryAsciiRows']:assert s[k]==m['previousSummary'][k]+1
assert s['partialAscii']==m['previousSummary']['partialAscii']
assert s['ordinaryWithoutAsciiEvaluation']==m['previousSummary']['ordinaryWithoutAsciiEvaluation']+2
assert s['fontFilesIncluded']==0 and s['glyphDataIncluded'] is False
c=json.loads((R/'data/curation.json').read_text());assert not set(c['removedIds']).intersection(r['id'] for r in rows)
assert len(list((R/'fonts').glob('*.html')))==230
assert len(list((R/'assets/specimens').glob('sunplus*')))==2
print('Sunplus integrated release: 227 baseline rows and PNGs unchanged; exactly two simplified additions; no recommendation or ASCII substitution.')
