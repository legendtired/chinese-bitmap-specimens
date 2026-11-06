from acquisition_baseline import before_acquisition
"""v17 approved scope, preserved v16.1 rows and variable-grid semantics."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id'] not in ('win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18','palm_cjkos_fgb12ktf','palm_cjkos_fgb12fsf','palm_cjkos_fb512kbf','palm_cjkos_fb512xmf','psion618c_8','psion618c_11','wqx_pc505_14x15','wqx_nc1020_12','casio_xda10000_12','casio_xda10000_24','panasonic_fsuv1_16','stone_ms2401h_style1_32','stone_ms2401h_style2_32','stone_ms2401h_style3_32','stone_ms2401h_style4_32','sharp_x68000_16','ibm_pcdos_kai_24','ibm_pcdos_hei_24','ibm_pcdos_fangsong_24','nokia_dct3_1999','fmtowns_f20_20','sun_gbk_song_12','sun_gbk_song_14','sun_gbk_song_16','sun_gbk_song_20','sun_gbk_song_24','sun_gb2312_song_12','sun_gb2312_song_14','sun_gb2312_song_20')];manifest=json.loads((R/'data/release-v17.json').read_text());byid={r['id']:r for r in rows}
removed=set(json.loads((R/'data/curation.json').read_text())['postV17RemovedIds']);assert removed=={'monotype_bitmap_hk','hanyi-pixel-power','hanyi-pixel-invasion','fzbase','gb48_2025_reference','fzfeng','taipeib20'}
removed |= set(json.loads((R/'data/curation.json').read_text())['postEfontRemovedIds'])
assert len(rows)==len(byid)==199
assert len(manifest['baseIds'])==191 and len(manifest['addedIds'])==15
assert (set(manifest['baseIds'])|set(manifest['addedIds']))-removed|{'psa_c_screen_12','psa_c_screen_14'}==set(byid)
for id,sha in manifest['baseRowChecksums'].items():
 if id in removed or id in json.loads((R/'data/curation.json').read_text()).get('postV17ModifiedIds',[]):continue
 assert hashlib.sha256(json.dumps(before_acquisition(byid[id]),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==sha,id
new=[byid[id] for id in manifest['addedIds']];assert all(r['priority']==0 for r in new)
assert sum(r['id'].startswith('dec_') for r in new)==10
assert len([r for r in rows if r.get('variableGrid')])==2
for id,em in [('pixels_han_main',14),('pixels_han_mono',9)]:
 r=byid[id];assert r.get('variableGrid') and r['sampleKind']=='standard' and r['designEmGrid']==em
 assert all(r.get(k) is None for k in ['width','height','cellWidth','cellHeight'])
 assert r['text']=='视野无限广，窗外有蓝天。' and r['asciiText']
 assert r['nativeEvidence']['lines'][0]['canvasBounds']
for r in new:
 if r['id'].startswith('dec_') and r['id'].endswith('_34'):assert r['height']==r['cellHeight']==34
 if not r.get('variableGrid'):assert r['height']==r['cellHeight']
r=byid['relmon_ms6459'];assert r['sampleKind']=='osd' and (r['width'],r['height'])==(12,18)
assert '2013' in r['provenance'] and '17' in r['coverage'];assert not set('频頻星單')&set(r['text']+r['asciiText'])
assert '09:41' in r['text'] and '单' in r['text']
r=byid['ccdb_cccii_64'];assert r['height']==64 and r['nativeEvidence']['records']==73885
assert '不等于73885个独立汉字' in r['notes'] and ',' in r['text']
s=json.loads((R/'data/summary.json').read_text());assert (s['rows'],s['nativePngCount'],s['referenceRows'],s['variableGridRows'])==(226,225,1,2)
print('v17 checks passed: retained baseline exact except approved acquisition guidance and Hanyi edits; seven historical plus two efont exclusions; only15 approved additions, zero new priority; variable grids,34px frames,2013 OSD and64px evidence boundaries.')
