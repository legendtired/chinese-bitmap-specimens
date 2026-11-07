from approved_recommendation_update import before_recommendations
from approved_p908_merge import restore_sun, historical_file_sha
"""Three approved HP-UX sizes with exact preserved baseline and public-only outputs."""
import hashlib,importlib.util,json,os,struct,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads((R/p).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(o):return sha(json.dumps(o,ensure_ascii=False,sort_keys=True).encode())
rows=before_recommendations(read('data/catalog.json'));m=read('data/release-hpux-sung.json');base=[r for r in rows if r['id']in m['baseIds']];added=[r for r in rows if r['id']in m['addedIds']]
assert len(rows)==len({r['id']for r in rows})==239
assert len(base)==230 and digest(restore_sun(base))==m['baseRowsSha256']
assert len(added)==3 and digest(added)==m['addedRowsSha256']
assert [r['id']for r in rows if r.get('priority',0)>0]==m['preservedRecommendedIds']
assert len({r['sourceIndex']for r in rows if r.get('sourceIndex') is not None})==len([r for r in rows if r.get('sourceIndex') is not None])
for r in rows:assert sha((R/r['specimen']).read_bytes())==r['specimenSha256'],r['id']
for r,n in zip(added,[24,34,42]):
 assert r['id']==f'hpux_sung_{n}' and r['priority']==0
 assert (r['width'],r['height'],r['cellWidth'],r['cellHeight'])==(n,n,n,n)
 assert r['asciiOrigin']=='native' and r['missing']==r['hanMissing']==r['asciiMissing']==[]
 assert r['nativeEvidence']['asciiWidth']==n//2
 assert struct.unpack_from('>II',(R/r['specimen']).read_bytes(),16)==(r['specimenWidth'],r['specimenHeight'])
s=read('data/summary.json');assert s['rows']==239 and s['nativePngCount']==238
for k in ['standardAsciiComplete','ordinaryAsciiRows']:assert s[k]==m['previousSummary'][k]+8
assert s['partialAscii']==m['previousSummary']['partialAscii']
assert s['fontFilesIncluded']==0 and s['glyphDataIncluded'] is False
assert {'sourceManifest':'release-hpux-sung.json','ids':m['addedIds']} in read('data/collection-history.json')['batches']
assert not set(read('data/curation.json')['removedIds'])&set(m['addedIds'])
# Optional exact source integration: all input hashes, same PNG bytes, mutated-source rejection.
if os.environ.get('HPUX_PCF_DIR'):
 spec=importlib.util.spec_from_file_location('hpux',R/'scripts/render_hpux_sung.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 source=Path(os.environ['HPUX_PCF_DIR'])
 import io
 for n in [24,34,42]:
  b=io.BytesIO();mod.render(source,n).save(b,format='PNG');assert b.getvalue()==(R/f'assets/specimens/hpux_sung_{n}.png').read_bytes()
 with tempfile.TemporaryDirectory()as d:
  p=Path(d);(p/'sung24n1.pcf').write_bytes(b'bad')
  try:mod.render(p,24)
  except ValueError:pass
  else:raise AssertionError('Corrupt source accepted')
 print('HP-UX exact private source redraw and rejection checks passed.')
else:print('HP-UX private PCF integration not run: source not supplied.')
print('HP-UX release: 230 baseline rows and PNGs, recommendations and exclusions preserved; exactly three additions.')

audit=read('data/hpux-sung-independent-audit.json')
assert audit['status']=='passed' and audit['totalGlyphsCompared']==41979 and audit['totalSourcePixelsCompared']==48472040
assert all(x['mismatchingPixels']==0 for x in audit['files'])
dedup=read('data/hpux-sung-dedup.json')
assert dedup['currentCatalogCount']==230 and dedup['referencesWithMappedHanIncludingDecSupplement']==213
assert len(dedup['currentAbsent'])==45
assert all(x['matched']==x['expected']==10 for x in dedup['sampleOnlySupplement']['positiveControls'])
