from approved_latin_update import historical_rows
"""Approved FM Towns20 addition with exact208 baseline and bounded coverage."""
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1];rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id'] not in ('ps2_scph50009_24','win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18','palm_cjkos_fgb12ktf','palm_cjkos_fgb12fsf','palm_cjkos_fb512kbf','palm_cjkos_fb512xmf','psion618c_8','psion618c_11','wqx_pc505_14x15','ibm_pcdos_kai_24', 'ibm_pcdos_hei_24', 'ibm_pcdos_fangsong_24', 'nokia_dct3_1999', 'sun_gbk_song_12', 'sun_gbk_song_14', 'sun_gbk_song_16', 'sun_gbk_song_20', 'sun_gbk_song_24', 'sun_gb2312_song_12', 'sun_gb2312_song_14', 'sun_gb2312_song_20')];m=json.loads((R/'data/release-fmtowns-f20.json').read_text());fid='fmtowns_f20_20';new=[r for r in rows if r['id']==fid];base=[r for r in rows if r['id']!=fid]
assert len(new)==1 and len(base)==208 and len(rows)==209
assert hashlib.sha256(json.dumps(historical_rows(base),ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m['baseRowsSha256']
r=new[0];assert r['id']==m['addedId'] and r['priority']==0
assert r['width']==r['height']==r['cellWidth']==r['cellHeight']==20
assert sum(x['priority']>0 for x in rows)==13
assert not any(x['id'].startswith('fmtowns') and x['id']!=fid for x in rows)
assert r['text']=='視野無限廣，窗外有藍天。' and r['asciiText']=='0123456789 AaBb GgMm !?:+-.'
assert r['missing']==r['hanMissing']==r['asciiMissing']==[] and r['asciiOrigin']=='native'
assert '未作全库去重' in r['notes'] and '1994' in r['provenance'] and '不据此' in r['provenance']
assert '6355' in r['acquisitionGuide']['notice'] and 'ANK及未核定扩展区不纳入导出' in r['acquisitionGuide']['notice']
png=(R/r['specimen']).read_bytes();assert struct.unpack('>II',png[16:24])==(270,42)
assert hashlib.sha256(png).hexdigest()==r['specimenSha256']==m['sampleSha256']
assert m['hanzi']==6355 and m['nativeFrame']==[20,20] and m['machineYear']==1994
for p in ['docs/fmtowns-f20.md','scripts/fmtowns_f20_to_bdf.py','fonts/fmtowns_f20_20.html']:assert (R/p).is_file()
print('FM Towns20: exact208 baseline, native pixels, 6355 JIS Han, source date and sample/export limits, no new priority.')
