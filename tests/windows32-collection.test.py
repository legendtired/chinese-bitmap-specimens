"""Two approved Windows 3.2 additions; prior catalog and specimen bytes unchanged."""
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1]
rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id']!='ps2_scph50009_24'];m=json.loads((R/'data/release-windows32.json').read_text())
by={r['id']:r for r in rows};ids=['win32_simsun_13','win32_simsun_20']
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
base=[r for r in rows if r['id'] in m['baseIds']];new=[r for r in rows if r['id'] in ids]
assert len(rows)==len(by)==m['totalRows']==226
assert len(base)==224 and [r['id'] for r in base]==m['baseIds']
assert m['addedIds']==[r['id'] for r in new]==ids
assert digest(base)==m['baseRowsSha256'] and digest(new)==m['addedRowsSha256']
assert [r['id'] for r in rows if r.get('priority',0)>0]==m['preservedRecommendedIds']
assert len(m['preservedRecommendedIds'])==13
indices=[r['sourceIndex'] for r in rows if r.get('sourceIndex') is not None]
assert len(indices)==len(set(indices))
for row in base:
 assert hashlib.sha256((R/row['specimen']).read_bytes()).hexdigest()==row['specimenSha256'],row['id']
for row,n in zip(new,[13,20]):
 assert row['priority']==0 and row['scripts']==['简体'] and row['asciiOrigin']=='native'
 assert (row['width'],row['height'],row['cellWidth'],row['cellHeight'])==(n,n,n,n)
 assert row['inkWidth']==row['inkHeight']==(13 if n==13 else 19)
 assert row['missing']==row['hanMissing']==row['asciiMissing']==[]
 e=row['nativeEvidence'];assert (e['gb2312Doublebyte'],e['basicHan'],e['printableAscii'])==(7445,6763,95)
 assert '不分发完整' in row['licenseNote'] and '基线' in row['layoutNote']
 b=(R/row['specimen']).read_bytes();assert hashlib.sha256(b).hexdigest()==row['specimenSha256']
 assert struct.unpack('>II',b[16:24])==(row['specimenWidth'],row['specimenHeight'])
 assert (R/f"fonts/{row['id']}.html").is_file()
 assert row['sourceUrl']=='https://archive.org/details/microsoft-windows-3.2-simpl-chinese-3.5'
 assert not any('/download/' in x['url'] for x in row['acquisitionGuide']['links'])
h=json.loads((R/'data/collection-history.json').read_text());assert next(b for b in h['batches'] if b['sourceManifest']=='release-windows32.json')=={'sourceManifest':'release-windows32.json','ids':ids}
s=json.loads((R/'data/summary.json').read_text());assert s['rows']==227 and s['nativePngCount']==226
for key in ['standardAsciiComplete','ordinaryAsciiRows']:assert s[key]==m['previousSummary'][key]+3
for key in ['partialAscii','ordinaryWithoutAsciiEvaluation']:assert s[key]==m['previousSummary'][key]
curation=json.loads((R/'data/curation.json').read_text());assert not set(curation['removedIds']).intersection(by)
assert all(i not in by for i in ['win32_simsun_16','win32_simsun_24','nokia_dct3_2002','nokia3350_2002'])
assert s['fontFilesIncluded']==0 and s['glyphDataIncluded'] is False
print('Windows 3.2: exactly13/20 added; all224 prior rows and PNGs preserved, coverage/source/metrics/permissions boundaries intact.')
