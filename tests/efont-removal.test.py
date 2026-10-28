"""Explicit 2026-10-28 /efont/ Unicode family removal, not a string purge."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/catalog.json').read_text());curation=json.loads((R/'data/curation.json').read_text())
removed={'efont_biwidth_10','efont_biwidth_12','efont_biwidth_14','efont_biwidth_16','efont_biwidth_24'}
assert set(curation['postEfontRemovedIds'])=={'efont_biwidth_16','efont_biwidth_24'}
assert removed<=set(curation['removedIds'])
assert not any(r['id'].startswith('efont_') or r['family']=='/efont/ Unicode' for r in rows)
for id in removed:
 assert not (R/'fonts'/f'{id}.html').exists()
 assert not (R/'assets/specimens'/f'{id}.png').exists()
 for name in ['index.html','sitemap.xml','data/catalog.js']:
  assert id not in (R/name).read_text()
assert {'ayu_gothic_18','ayu_gothic_20'}<={r['id'] for r in rows},'Do not remove separate Sazanami-hosted Ayu fonts by URL substring'
assert len(rows)==199 and len(list((R/'fonts').glob('*.html')))==199
print('efont removal: all five known Unicode sizes excluded; two current entries/assets/pages removed; independent Ayu family retained.')
