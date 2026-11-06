from acquisition_baseline import before_acquisition
"""v16 scope, baseline preservation and public-data boundaries."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1]
rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id'] not in ('ps2_scph50009_24','win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18','palm_cjkos_fgb12ktf','palm_cjkos_fgb12fsf','palm_cjkos_fb512kbf','palm_cjkos_fb512xmf','psion618c_8','psion618c_11','wqx_pc505_14x15','wqx_nc1020_12','casio_xda10000_12','casio_xda10000_24','panasonic_fsuv1_16','stone_ms2401h_style1_32','stone_ms2401h_style2_32','stone_ms2401h_style3_32','stone_ms2401h_style4_32','sharp_x68000_16','ibm_pcdos_kai_24','ibm_pcdos_hei_24','ibm_pcdos_fangsong_24','nokia_dct3_1999','fmtowns_f20_20','sun_gbk_song_12','sun_gbk_song_14','sun_gbk_song_16','sun_gbk_song_20','sun_gbk_song_24','sun_gb2312_song_12','sun_gb2312_song_14','sun_gb2312_song_20')];release=json.loads((R/'data/release-v16.json').read_text());byid={r['id']:r for r in rows}
removed=set(json.loads((R/'data/curation.json').read_text())['postV17RemovedIds']);assert removed=={'monotype_bitmap_hk','hanyi-pixel-power','hanyi-pixel-invasion','fzbase','gb48_2025_reference','fzfeng','taipeib20'}
removed |= set(json.loads((R/'data/curation.json').read_text())['postEfontRemovedIds'])
assert len(rows)==len(byid)==199
assert (set(release['baseIds'])|set(release['addedIds']))-removed<=set(byid)
assert len(release['baseIds'])==155 and len(release['addedIds'])==36
for id,sha in release['baseRowChecksums'].items():
 if id in removed:continue
 row=before_acquisition(byid[id])
 if id=='mplus_bitmap_12':row={k:v for k,v in row.items() if k!='relatedSources'}
 assert hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==sha,id
added=[byid[id] for id in release['addedIds'] if id not in removed];refs=[r for r in added if r['sampleKind']=='reference']
assert len(refs)==1 and len(added)-len(refs)==29
assert len([r for r in added if r['family']=='Palm CJKOS'])==4
assert len([r for r in added if r['family']=='蒙纳点阵'])==0
assert not any('多巴胺' in r['name'] or 'dopa' in r['id'].lower() or 'silver' in r['id'].lower() for r in rows)
for r in rows:
 assert hashlib.sha256((R/r['specimen']).read_bytes()).hexdigest()==r['specimenSha256'],r['id']
 if r['sampleKind']=='reference':
  assert all(r.get(k) is None for k in ['width','height','cellWidth','cellHeight'])
  assert r['referenceType'] in ['官方试字截图','标准图样','历史外字资料']
  assert r.get('referenceNote') and 'nativeEvidence' not in r
 elif r.get('variableGrid') or r.get('heightBasis')=='han-design-grid':assert all(r.get(k) is None for k in ['width','height','cellWidth','cellHeight'])
 else:assert isinstance(r['height'],int) and r['height']>0
 public=json.dumps(r,ensure_ascii=False)
 assert '/workspace/' not in public and '"glyphs"' not in public
assert byid['elisa_8_native']['height']==8 and byid['elisa_8_native']['width']==10 and byid['elisa_8_native']['cellWidth']==10
assert byid['elisa_8_native']['asciiOrigin']=='fullwidth-native'
assert byid['cns40_original']['asciiOrigin']=='fullwidth-native'
assert '\n' in byid['yh_1999_16']['text'] and byid['yh_1999_16']['asciiText']
assert all(not r['asciiText'] and r['asciiOrigin']=='absent' for r in added if r['family']=='Palm CJKOS')
s=json.loads((R/'data/summary.json').read_text());assert s['rows']==227 and s['referenceRows']==1 and s['nativePngCount']==226
print('v16 checks passed: retained base155 rows preserved except allowed acquisition guidance and Silver provenance changes;29 native/design-grid+1 retained reference; explicit pixel-style exclusions, no excluded/unapproved fonts; hashes and source/privacy boundaries valid.')
