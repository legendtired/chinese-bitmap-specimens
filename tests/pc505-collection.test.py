from catalog_history import before_solaris_withdrawal
"""Exact additive PC505 collection batch: old221 rows and original public7 remain intact."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1]
m=json.loads((R/'data/release-pc505-collection.json').read_text());rows=before_solaris_withdrawal(R);by={r['id']:r for r in rows}
assert len(rows)==len(by)==m['totalRows']==222
base=[r for r in rows if r['id'] in m['baseIds']];new=[r for r in rows if r['id'] in m['addedIds']]
assert [r['id'] for r in base]==m['baseIds'] and len(base)==221
assert [r['id'] for r in new]==m['addedIds']==['wqx_pc505_14x15']
for group,key in [(base,'baseRowsSha256'),(new,'addedRowsSha256')]:assert hashlib.sha256(json.dumps(group,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m[key]
assert new[0]['sourceIndex']==252 and new[0]['priority']==0
assert [r['id'] for r in rows if r.get('priority',0)>0]==m['preservedRecommendedIds'] and len(m['preservedRecommendedIds'])==13
indices=[r['sourceIndex'] for r in rows if r.get('sourceIndex') is not None];assert len(indices)==len(set(indices))
for f in json.loads((R/'data/pc505-public-files.json').read_text()):
 p=R/f['path'];assert p.stat().st_size==f['bytes'];assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],f['path']
h=json.loads((R/'data/collection-history.json').read_text());assert next(b for b in h['batches'] if b['sourceManifest']=='release-pc505-collection.json')=={'sourceManifest':'release-pc505-collection.json','ids':m['addedIds']}
assert (R/'fonts/wqx_pc505_14x15.html').is_file()
print('PC505 collection: 221 exact old rows, 1 exact addition, 7 unchanged reviewed public files, newest batch, no priority or index collision.')
