from approved_latin_update import historical_rows
from catalog_history import before_solaris_withdrawal
"""Cloudflare-first batch: exact prior208, exact authorized13 additions, no priority drift."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1]
m=json.loads((R/'data/release-20261105-batch.json').read_text());rows=[r for r in before_solaris_withdrawal(R) if r['id'] != 'wqx_pc505_14x15'];by={r['id']:r for r in rows}
assert len(rows)==len(by)==m['totalRows']==221
base=[r for r in rows if r['id'] in m['baseIds']];new=[r for r in rows if r['id'] in m['addedIds']]
assert [r['id'] for r in base]==m['baseIds'] and [r['id'] for r in new]==m['addedIds']
for group,key in [(base,'baseRowsSha256'),(new,'addedRowsSha256')]:assert hashlib.sha256(json.dumps(historical_rows(group),ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m[key]
assert [r['id'] for r in rows if r['priority']>0]==m['preservedRecommendedIds'] and len(m['preservedRecommendedIds'])==13
indices=[r['sourceIndex'] for r in rows if r.get('sourceIndex') is not None];assert len(indices)==len(set(indices))
print('Cloudflare-first batch: 208 exact old rows, 13 exact additions, 13 unchanged recommendations, no ID/index collision.')
