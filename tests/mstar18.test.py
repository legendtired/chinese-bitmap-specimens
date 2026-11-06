"""One additive MStar18 entry, exact old rows, fixed sample and source-only tools."""
from pathlib import Path
import hashlib,json,struct,sys
R=Path(__file__).resolve().parents[1]
rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id'] not in ('hpux_sung_24','hpux_sung_34','hpux_sung_42','samsung_r208_16','sunplus_sphe8202l_16x16','sunplus_sphe8202l_20x24','ps2_scph50009_24','win32_simsun_13','win32_simsun_20','san5_dos_16x14')];m=json.loads((R/'data/release-mstar18.json').read_text())
base=[r for r in rows if r['id'] in m['baseIds']];added=[r for r in rows if r['id'] in m['addedIds']]
assert len(rows)==223 and len(base)==222 and len(added)==1
assert [r['id'] for r in base]==m['baseIds']
for group,key in [(base,'baseRowsSha256'),(added,'addedRowsSha256')]:
 assert hashlib.sha256(json.dumps(group,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m[key]
r=added[0];assert r['id']=='mstar_tv_simp_18' and r['priority']==0
assert [r['id'] for r in rows if r.get('priority',0)>0]==m['preservedRecommendedIds']
assert (r['width'],r['height'],r['inkWidth'],r['inkHeight'])==(18,18,14,14)
assert r['nativeEvidence']['unicodeMapped']==7804 and r['nativeEvidence']['gb2312Han']==6763
assert r['asciiOrigin']=='native' and r['asciiMissing']==[] and r['missing']==[]
b=(R/r['specimen']).read_bytes();assert hashlib.sha256(b).hexdigest()==r['specimenSha256'];assert struct.unpack('>II',b[16:24])==(234,40)
assert not any(x['id'].startswith('mstar') and x['id']!='mstar_tv_simp_18' for x in rows)
h=json.loads((R/'data/collection-history.json').read_text());assert next(b for b in h['batches'] if b['sourceManifest']=='release-mstar18.json')=={'sourceManifest':'release-mstar18.json','ids':m['addedIds']}
assert (R/'fonts/mstar_tv_simp_18.html').is_file()
sys.path.insert(0,str(R/'scripts'));import mstar_18_to_bdf as e
try:e.decode(b'not the verified 18px source')
except ValueError:pass
else:raise AssertionError('Source hash gate missing')
# Fabricated patterns only; not original font data.
g=[{'code':32,'index':0,'source_bbox':[0,7,0,17],'rows':[0]*18}, {'code':65,'index':1,'source_bbox':[0,11,0,17],'rows':[1<<17,1]+[0]*16}]
v=e.bdf_text(g,'variable');f=e.bdf_text(g,'fixed')
assert 'DWIDTH 7 0' in v and 'DWIDTH 11 0' in v and f.count('DWIDTH 18 0')==2
assert '-72-72-P-0-ISO10646-1' in v and '-72-72-C-180-ISO10646-1' in f
assert v.count('BBX 18 18 0 0')==2 and '800000\n000040\n' in v
assert 'COMMENT SOURCE_BBOX 0 7 0 17' in v and 'CHARS 2' in v
try:e.bdf_text(g,'unknown')
except ValueError:pass
else:raise AssertionError('Unsupported layout accepted')
print('MStar18: 1 exact addition; 222 unchanged rows; native fixed PNG, no24; strict source gate and width modes.')
