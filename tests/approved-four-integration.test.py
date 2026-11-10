"""Strict 248 -> 252 local integration; published status is not inferred."""
from approved_simsun import before_simsun_rows,before_simsun_data,before_simsun_bytes,MANIFEST as simsun
from pathlib import Path
import copy,hashlib,json,sys
from approved_four import MANIFEST as m,IDS,before_four_rows,before_four_data,before_four_bytes,digest
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import generate_static as generator
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads((R/p).read_text())
rows=before_simsun_rows(read('data/catalog.json'));old=before_four_rows(rows)
assert len(rows)==len({r['id'] for r in rows})==252
assert [r['id'] for r in rows[-4:]]==IDS
assert [r['sourceIndex'] for r in rows[-4:]]==[286,287,288,289]
assert all(r['priority']==0 for r in rows[-4:])
assert len(old)==248 and digest(old)==m['baseRowsSha256']
assert digest({r['id']:sha(before_simsun_bytes(f"fonts/{r['id']}.html")) for r in old})==m['basePagesSha256']
assert digest({r['id']:sha((R/r['specimen']).read_bytes()) for r in old})==m['baseSpecimensSha256']
assert sum(r['priority']>0 for r in rows)==17
assert before_simsun_data('data/summary.json',read('data/summary.json'))==m['summary']
assert before_four_data('data/summary.json',read('data/summary.json'))==m['baseSummary']
assert before_simsun_data('data/collection-history.json',read('data/collection-history.json'))['batches'][-1]==m['batch']
for p,h in m['addedFiles'].items():assert sha(before_simsun_bytes(p))==h,p
for r in rows[-4:]:
 assert (R/'fonts'/f"{r['id']}.html").read_text()==generator.font_page(r)
 assert generator.article(r)+'\n' in (R/'index.html').read_text()
for path in ('data/catalog.json','data/catalog.js','data/collection-history.json','data/collection-history.js','data/summary.json','index.html','sitemap.xml','app.js','styles.css'):
 assert sha(before_four_bytes(path))==m['baseFilesSha256'][path],path
# Exact file scope: no private files, raw sources, arbitrary new assets or hidden additions.
actual={str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.git' not in p.parts}
actual-=set(simsun['newPaths'])
assert actual==set(m['baseFilesSha256'])|set(m['newPaths']), (actual-set(m['baseFilesSha256'])-set(m['newPaths']))
for path,h in m['baseFilesSha256'].items():
 if path not in m['changedPaths']:assert sha(before_simsun_bytes(path))==h,path
for path,h in m['changedFileHashes'].items():assert sha(before_simsun_bytes(path))==h,path
for p in R.rglob('*'):
 if '.git' not in p.parts and '__pycache__' not in p.parts:
  assert not p.is_symlink(),p
  if p.is_file():assert p.stat().st_nlink==1,p
for ident in IDS:
 bad=copy.deepcopy(rows);next(r for r in bad if r['id']==ident)['name']+=' UNREVIEWED'
 try:before_four_rows(bad)
 except AssertionError:pass
 else:raise AssertionError('Mutated row accepted')
bad=copy.deepcopy(read('data/collection-history.json'));bad['batches'][-1]['ids'].append('UNREVIEWED')
try:before_four_data('data/collection-history.json',bad)
except AssertionError:pass
else:raise AssertionError('Mutated history accepted')
print('Approved-four integration: all old 248 rows/pages/previews/UI unchanged; four exact rows/files; 252 total; scope and negative controls PASS.')
