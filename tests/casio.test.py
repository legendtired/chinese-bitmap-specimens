from approved_alcatel715 import before_alcatel_data
from export_baseline import before_export_guides
"""Explicit Casio two-size addition with no baseline changes or full font files."""
from pathlib import Path
import json,hashlib,subprocess,sys,tempfile
R=Path(__file__).resolve().parents[1];rows=[r for r in before_alcatel_data('data/catalog.json', json.loads((R/'data/catalog.json').read_text())) if r['id'] not in ('sony_ericsson_p802_12','sony_ericsson_p908_14','nokia_9210c_15','nokia_9210c_17','nokia_9210c_19','aix_isas_cns_24','hpux_song_40','hpux_sung_24','hpux_sung_34','hpux_sung_42','samsung_r208_16','sunplus_sphe8202l_16x16','sunplus_sphe8202l_20x24','ps2_scph50009_24','win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18','palm_cjkos_fgb12ktf','palm_cjkos_fgb12fsf','palm_cjkos_fb512kbf','palm_cjkos_fb512xmf','psion618c_8','psion618c_11','wqx_pc505_14x15','panasonic_fsuv1_16','stone_ms2401h_style1_32','stone_ms2401h_style2_32','stone_ms2401h_style3_32','stone_ms2401h_style4_32','sharp_x68000_16','ibm_pcdos_kai_24','ibm_pcdos_hei_24','ibm_pcdos_fangsong_24','nokia_dct3_1999','fmtowns_f20_20','sun_gbk_song_12','sun_gbk_song_14','sun_gbk_song_16','sun_gbk_song_20','sun_gbk_song_24','sun_gb2312_song_12','sun_gb2312_song_14','sun_gb2312_song_20')];m=json.loads((R/'data/release-casio.json').read_text())
assert len(rows)==202
base=[r for r in rows if r['id'] not in m['addedIds']]
assert hashlib.sha256(json.dumps([before_export_guides(r) for r in base],ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m['baseRowsSha256']
assert not any(r['id']=='casio_xda10000_16' for r in rows)
for n,priority in [(12,6),(24,0)]:
 r=next(r for r in rows if r['id']==f'casio_xda10000_{n}');assert r['priority']==priority and (r['width'],r['height'])==(n,n)
 assert hashlib.sha256((R/r['specimen']).read_bytes()).hexdigest()==r['specimenSha256'] and r['missing']==[]
 assert '未独立认证' in r['notes'] and '授权' in r['licenseNote']
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'unknown.cjf').write_bytes(bytes(10));out=p/'font.bdf';r=subprocess.run([sys.executable,str(R/'scripts/cjf_to_bdf.py'),str(p/'unknown.cjf'),str(out)],capture_output=True);assert r.returncode and not out.exists()
print('Casio: two approved specimens, 12px recommended, 24px ordinary, original200 exact,16px not duplicated, unknown input rejected.')
