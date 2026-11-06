"""Approved IBM native24 additions, unchanged previous rows and bounded claims."""
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1]
rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id'] not in ('psion618c_8','psion618c_11','wqx_pc505_14x15','nokia_dct3_1999', 'fmtowns_f20_20', 'sun_gbk_song_12', 'sun_gbk_song_14', 'sun_gbk_song_16', 'sun_gbk_song_20', 'sun_gbk_song_24', 'sun_gb2312_song_12', 'sun_gb2312_song_14', 'sun_gb2312_song_20')];m=json.loads((R/'data/release-ibm-pcdos.json').read_text());ids=m['addedIds'];byid={r['id']:r for r in rows}
assert len(rows)==len(byid)==211
assert ids==['ibm_pcdos_kai_24','ibm_pcdos_hei_24','ibm_pcdos_fangsong_24']
base=[r for r in rows if r['id'] in m['baseIds']]
assert len(base)==208 and [r['id'] for r in base]==m['baseIds']
assert hashlib.sha256(json.dumps(base,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m['baseRowsSha256']
assert {r['id'] for r in rows}-set(m['baseIds'])==set(ids)
new_indices={byid[i]['sourceIndex'] for i in ids}
assert len(new_indices)==3 and not new_indices & {r['sourceIndex'] for r in base}
assert sum(r['priority']>0 for r in rows)==13
for item in m['styles']:
 r=byid[item['id']]
 assert r['priority']==0 and r['scripts']==['简体']
 assert r['width']==r['height']==r['cellWidth']==r['cellHeight']==24
 assert r['text']==m['sampleText']=='视野无限广，窗外有蓝天。'
 assert r['asciiText']=='' and r['asciiOrigin']=='absent'
 assert r['missing']==r['hanMissing']==r['asciiMissing']==[]
 assert '7444' in r['coverage'] and '6763' in r['coverage']
 assert 'U+3000' in r['notes'] and '不是视觉猜名' in r['notes']
 assert '非全部目录全库去重' in r['notes'] and 'ANK' in r['notes']
 assert '01/24/92' in r['provenance'] and '不据此' in r['provenance']
 assert '不分发FNT' in r['licenseNote'] and '授权' in r['licenseNote']
 assert item['mappedGb2312']==7444 and item['hanzi']==6763 and item['missingStandardCodepoints']==['U+3000']
 assert item['sourceRecords'] in [7503,7472]
 png=(R/r['specimen']).read_bytes();assert struct.unpack('>II',png[16:24])==(288,24)
 assert hashlib.sha256(png).hexdigest()==r['specimenSha256']==item['sampleSha256']
 assert (R/'fonts'/f"{r['id']}.html").is_file()
 assert r['acquisitionGuide']['links'][0]['url'].endswith('/docs/ibm-pcdos.md')
for p in ['docs/ibm-pcdos.md','scripts/ibm_pcdos_to_bdf.py']:assert (R/p).is_file()
assert not any(r['id'].startswith('ibm_pcdos_') and r['id'] not in ids for r in rows)
assert len({r['sampleSha256'] for r in m['styles']})==3
print('IBM PC DOS: 3 native24 styles; exact208 prior rows, unchanged13 priorities; 7444 mapped/6763 Han; U+3000 and extensions honest; no duplicate Song.')
