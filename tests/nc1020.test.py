from export_baseline import before_export_guides
"""Approved NC1020 addition, fixed preview only, exact baseline preservation."""
from pathlib import Path
import json,hashlib,subprocess,sys,tempfile
R=Path(__file__).resolve().parents[1]; rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if not r['id'].startswith('casio_xda10000_') and r['id'] not in ('sunplus_sphe8202l_16x16','sunplus_sphe8202l_20x24','ps2_scph50009_24','win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18','palm_cjkos_fgb12ktf','palm_cjkos_fgb12fsf','palm_cjkos_fb512kbf','palm_cjkos_fb512xmf','psion618c_8','psion618c_11','wqx_pc505_14x15','panasonic_fsuv1_16','stone_ms2401h_style1_32','stone_ms2401h_style2_32','stone_ms2401h_style3_32','stone_ms2401h_style4_32','sharp_x68000_16','ibm_pcdos_kai_24','ibm_pcdos_hei_24','ibm_pcdos_fangsong_24','nokia_dct3_1999','fmtowns_f20_20','sun_gbk_song_12','sun_gbk_song_14','sun_gbk_song_16','sun_gbk_song_20','sun_gbk_song_24','sun_gb2312_song_12','sun_gb2312_song_14','sun_gb2312_song_20')]
assert hashlib.sha256(json.dumps([before_export_guides(r) for r in rows if r['id']!='wqx_nc1020_12'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()==json.loads((R/'data/release-nc1020.json').read_text())['baseRowsSha256']
r=next(r for r in rows if r['id']=='wqx_nc1020_12')
assert len(rows)==200 and r['priority']==7 and (r['width'],r['height'])==(12,12)
assert (r['specimenWidth'],r['specimenHeight'])==(144,12) and r['missing']==[]
assert hashlib.sha256((R/r['specimen']).read_bytes()).hexdigest()==r['specimenSha256']
assert '未实机验证' in r['notes'] and '再分发' in r['licenseNote']
assert r['asciiOrigin']=='absent' and r['asciiText']==''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'wrong.bin').write_bytes(bytes(10));result=subprocess.run([sys.executable,str(R/'scripts/wqx_to_bdf.py'),str(p/'wrong.bin'),str(p/'out.bdf')],capture_output=True)
 assert result.returncode!=0 and not (p/'out.bdf').exists()
print('NC1020: approved recommendation, unchanged199 baseline, sample SHA, unknown input rejected; no full font published.')
