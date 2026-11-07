"""One approved PS2 addition; all226 prior rows/specimens remain exact."""
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1]
rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id'] not in ['sony_ericsson_p908_14','nokia_9210c_15','nokia_9210c_17','nokia_9210c_19','aix_isas_cns_24','hpux_song_40','hpux_sung_24','hpux_sung_34','hpux_sung_42','samsung_r208_16','sunplus_sphe8202l_16x16','sunplus_sphe8202l_20x24']];m=json.loads((R/'data/release-ps2-china.json').read_text())
base=[r for r in rows if r['id'] in m['baseIds']];new=[r for r in rows if r['id'] in m['addedIds']]
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
assert len(rows)==len({r['id'] for r in rows})==m['totalRows']==227
assert len(base)==226 and [r['id'] for r in base]==m['baseIds']
assert digest(base)==m['baseRowsSha256'] and digest(new)==m['addedRowsSha256']
assert [r['id'] for r in new]==['ps2_scph50009_24']
assert [r['id'] for r in rows if r.get('priority',0)>0]==m['preservedRecommendedIds']
assert len(m['preservedRecommendedIds'])==13
for r in base:assert hashlib.sha256((R/r['specimen']).read_bytes()).hexdigest()==r['specimenSha256'],r['id']
r=new[0];assert r['priority']==0 and r['sourceIndex']==263
assert (r['width'],r['height'],r['cellWidth'],r['cellHeight'])==(24,24,24,24)
assert r['scripts']==['简体','繁体'] and r['asciiOrigin']=='native'
assert r['missing']==r['hanMissing']==r['asciiMissing']==[]
e=r['nativeEvidence'];assert (e['sourceGlyphSlots'],e['unicodeMappedGbk'],e['basicHan'],e['gb2312Han'],e['printableAscii'])==(28591,21638,20902,6763,95)
assert e['runtimeAdvance'] is None and e['asciiStorageWidth']==24 and e['asciiInkMaxWidth']==12
assert '非完整GBK' in r['coverage'] and '不公开ROM' in r['licenseNote'] and '实际advance与基线未核' in r['layoutNote']
b=(R/r['specimen']).read_bytes();assert hashlib.sha256(b).hexdigest()==r['specimenSha256']
assert struct.unpack('>II',b[16:24])==(r['specimenWidth'],r['specimenHeight'])==(674,52)
assert (R/'fonts/ps2_scph50009_24.html').is_file()
assert (R/'scripts/verify_ps2_bitmap_decode.py').is_file()
h=json.loads((R/'data/collection-history.json').read_text());assert next(b for b in h['batches'] if b['sourceManifest']=='release-ps2-china.json')=={'sourceManifest':'release-ps2-china.json','ids':['ps2_scph50009_24']}
s=json.loads((R/'data/summary.json').read_text());assert s['rows']==239 and s['nativePngCount']==238
for key in ['standardAsciiComplete','ordinaryAsciiRows']:assert s[key]==m['previousSummary'][key]+10
assert s['partialAscii']==m['previousSummary']['partialAscii']
assert s['ordinaryWithoutAsciiEvaluation']==m['previousSummary']['ordinaryWithoutAsciiEvaluation']+3
c=json.loads((R/'data/curation.json').read_text());assert not set(c['removedIds']).intersection(r['id'] for r in rows)
assert s['fontFilesIncluded']==0 and s['glyphDataIncluded'] is False
print('PS2: exactly1 approved addition; all226 prior rows and PNGs unchanged, native ASCII, mapping/layout/rights limits intact.')
