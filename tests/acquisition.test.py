"""Acquisition-only update: all font metadata and pixels stay unchanged."""
from pathlib import Path
import json,hashlib,html
from acquisition_baseline import BASE
R=Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/catalog.json').read_text())
assert len(rows)==201 and {r['id'] for r in rows}==set(BASE['rowHashesWithoutGuide'])
assert sum(r.get('priority',0)>0 for r in rows)==11
for row in rows:
 original={k:v for k,v in row.items() if k!='acquisitionGuide'}
 digest=hashlib.sha256(json.dumps(original,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 assert digest==BASE['rowHashesWithoutGuide'][row['id']],row['id']
 guide=row['acquisitionGuide'];assert guide['notice'] and guide['title'] and guide['steps']==[]
 page=(R/'fonts'/f"{row['id']}.html").read_text()
 assert html.escape(guide['notice']) in page,row['id']
 for link in guide['links']:assert html.escape(link['url'],quote=True) in page,row['id']
for id in ['psa_c_screen_12','psa_c_screen_14']:
 row=next(r for r in rows if r['id']==id)
 assert row['acquisitionGuide']==BASE['originalGuides'][id]
js=(R/'data/catalog.js').read_text(); assert json.loads(js[js.index('['):].rstrip().rstrip(';'))==rows
assert 'row.acquisitionGuide.notice' in (R/'app.js').read_text()
print('Acquisition:201 concise guides; static/dynamic data match;11 priorities; all other row metadata, IDs and PSA contact guidance preserved.')
