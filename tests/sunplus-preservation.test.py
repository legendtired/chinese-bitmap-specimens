from approved_alcatel715 import before_alcatel_data
from approved_recommendation_update import before_recommendations
from approved_p908_merge import restore_sun, historical_file_sha
"""Final integrated Sunplus release preserves the complete 227-row baseline."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1]
rows=[r for r in before_recommendations(before_alcatel_data('data/catalog.json', json.loads((R/'data/catalog.json').read_text()))) if r['id'] not in ('sony_ericsson_p802_12','sony_ericsson_p908_14','nokia_9210c_15','nokia_9210c_17','nokia_9210c_19','aix_isas_cns_24','hpux_song_40','hpux_sung_24','hpux_sung_34','hpux_sung_42','samsung_r208_16')];m=json.loads((R/'data/release-sunplus.json').read_text())
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
base=[r for r in rows if r['id'] in m['baseIds']];added=[r for r in rows if r['id'] in m['addedIds']]
assert len(rows)==len({r['id'] for r in rows})==m['totalRows']==229
assert len(base)==m['baseRows']==227 and [r['id'] for r in base]==m['baseIds']
assert digest(restore_sun(base))==m['baseRowsSha256'] and digest(added)==m['addedRowsSha256']
assert [r['id'] for r in added]==m['addedIds']
assert [r['id'] for r in rows if r.get('priority',0)>0]==m['preservedRecommendedIds']
assert len(m['preservedRecommendedIds'])==13
for r in base:assert hashlib.sha256((R/r['specimen']).read_bytes()).hexdigest()==r['specimenSha256'],r['id']
indices=[r['sourceIndex'] for r in rows if r.get('sourceIndex') is not None]
assert len(indices)==len(set(indices))
h=before_alcatel_data('data/collection-history.json', json.loads((R/'data/collection-history.json').read_text()))
assert next(b for b in h['batches'] if b['sourceManifest']=='release-sunplus.json')=={'sourceManifest':'release-sunplus.json','ids':m['addedIds']}
s=before_alcatel_data('data/summary.json', json.loads((R/'data/summary.json').read_text()));assert s['rows']==239 and s['nativePngCount']==238
for k in ['standardAsciiComplete','ordinaryAsciiRows']:assert s[k]==m['previousSummary'][k]+9
assert s['partialAscii']==m['previousSummary']['partialAscii']
assert s['ordinaryWithoutAsciiEvaluation']==m['previousSummary']['ordinaryWithoutAsciiEvaluation']+3
assert s['fontFilesIncluded']==0 and s['glyphDataIncluded'] is False
c=json.loads((R/'data/curation.json').read_text());assert not set(c['removedIds']).intersection(r['id'] for r in rows)
assert len([p for p in (R/'fonts').glob('*.html') if p.stem not in ('olympus_mrobe_mr100_12', 'sony_psp_bwfont_16x18', 'alcatel_ot715_13x14', 'ms_ming_14')])==239
assert len(list((R/'assets/specimens').glob('sunplus*')))==2
print('Sunplus integrated release: 227 baseline rows and PNGs unchanged; exactly two simplified additions; no recommendation or ASCII substitution.')
