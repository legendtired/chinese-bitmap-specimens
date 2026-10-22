"""v16 scope, baseline preservation and public-data boundaries."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/catalog.json').read_text());release=json.loads((R/'data/release-v16.json').read_text());byid={r['id']:r for r in rows}
assert len(rows)==len(byid)==206
assert set(release['baseIds'])|set(release['addedIds'])<=set(byid)
assert len(release['baseIds'])==155 and len(release['addedIds'])==36
for id,sha in release['baseRowChecksums'].items():
 row=byid[id]
 if id=='mplus_bitmap_12':row={k:v for k,v in row.items() if k!='relatedSources'}
 assert hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==sha,id
added=[byid[id] for id in release['addedIds']];refs=[r for r in added if r['sampleKind']=='reference']
assert len(refs)==11 and len(added)-len(refs)==25
assert len([r for r in added if r['family']=='Palm CJKOS'])==4
assert len([r for r in added if r['family']=='蒙纳点阵'])==1
assert not any('多巴胺' in r['name'] or 'dopa' in r['id'].lower() or 'silver' in r['id'].lower() for r in rows)
for r in rows:
 assert hashlib.sha256((R/r['specimen']).read_bytes()).hexdigest()==r['specimenSha256'],r['id']
 if r['sampleKind']=='reference':
  assert all(r.get(k) is None for k in ['width','height','cellWidth','cellHeight'])
  assert r['referenceType'] in ['官方试字截图','标准图样','历史外字资料']
  assert r.get('referenceNote') and 'nativeEvidence' not in r
 elif r.get('variableGrid'):assert all(r.get(k) is None for k in ['width','height','cellWidth','cellHeight'])
 else:assert isinstance(r['height'],int) and r['height']>0
 public=json.dumps(r,ensure_ascii=False)
 assert '/workspace/' not in public and '"glyphs"' not in public
assert byid['elisa_8_native']['height']==8 and byid['elisa_8_native']['width']==10 and byid['elisa_8_native']['cellWidth']==10
assert byid['elisa_8_native']['asciiOrigin']=='fullwidth-native'
assert byid['cns40_original']['asciiOrigin']=='fullwidth-native'
assert '\n' in byid['yh_1999_16']['text'] and byid['yh_1999_16']['asciiText']
assert all(not r['asciiText'] and r['asciiOrigin']=='absent' for r in added if r['family']=='Palm CJKOS')
s=json.loads((R/'data/summary.json').read_text());assert s['rows']==206 and s['referenceRows']==11 and s['nativePngCount']==195
print('v16 checks passed: base155 preserved, only allowed Silver provenance changes;25 native+11 reference, no excluded/unapproved fonts; hashes and source/privacy boundaries valid.')
