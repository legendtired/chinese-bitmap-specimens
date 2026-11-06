"""Acquisition-only update: all font metadata and pixels stay unchanged."""
from pathlib import Path
import json,hashlib,html
from acquisition_baseline import BASE
R=Path(__file__).resolve().parents[1]
rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id'] not in ('win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18','palm_cjkos_fgb12ktf','palm_cjkos_fgb12fsf','palm_cjkos_fb512kbf','palm_cjkos_fb512xmf','psion618c_8','psion618c_11','wqx_pc505_14x15','wqx_nc1020_12','casio_xda10000_12','casio_xda10000_24','panasonic_fsuv1_16','stone_ms2401h_style1_32','stone_ms2401h_style2_32','stone_ms2401h_style3_32','stone_ms2401h_style4_32','sharp_x68000_16','ibm_pcdos_kai_24','ibm_pcdos_hei_24','ibm_pcdos_fangsong_24','nokia_dct3_1999','fmtowns_f20_20','sun_gbk_song_12','sun_gbk_song_14','sun_gbk_song_16','sun_gbk_song_20','sun_gbk_song_24','sun_gb2312_song_12','sun_gb2312_song_14','sun_gb2312_song_20')]
removed=set(json.loads((R/'data/curation.json').read_text())['postEfontRemovedIds'])
assert removed=={'efont_biwidth_16','efont_biwidth_24'}
assert len(rows)==199 and {r['id'] for r in rows}==set(BASE['rowHashesWithoutGuide'])-removed
assert sum(r.get('priority',0)>0 for r in rows)==11
for row in rows:
 original={k:v for k,v in row.items() if k!='acquisitionGuide'}
 digest=hashlib.sha256(json.dumps(original,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 assert digest==BASE['rowHashesWithoutGuide'][row['id']],row['id']
 guide=row['acquisitionGuide'];assert guide['notice'] and guide['title'] and guide['steps']==[]
 page=(R/'fonts'/f"{row['id']}.html").read_text()
 assert html.escape(guide['notice']) in page,row['id']
 for link in guide['links']:assert html.escape(link['url'],quote=True) in page,row['id']
for id in ['psa_c_screen_12','psa_c_screen_14']:
 row=next(r for r in rows if r['id']==id)
 guide=row['acquisitionGuide']; original=BASE['originalGuides'][id]
 assert guide['notice']==original['notice'] and guide['steps']==original['steps']
 assert [(x['url'],x['label']) for x in guide['links']]==[(x['url'],x['label']) for x in original['links']]
 assert guide['type']=='contact' and all(x['action']=='contact' for x in guide['links'])
js=(R/'data/catalog.js').read_text(); assert [r for r in json.loads(js[js.index('['):].rstrip().rstrip(';')) if r['id'] not in ('win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18','palm_cjkos_fgb12ktf','palm_cjkos_fgb12fsf','palm_cjkos_fb512kbf','palm_cjkos_fb512xmf','psion618c_8','psion618c_11','wqx_pc505_14x15','wqx_nc1020_12','casio_xda10000_12','casio_xda10000_24','panasonic_fsuv1_16','stone_ms2401h_style1_32','stone_ms2401h_style2_32','stone_ms2401h_style3_32','stone_ms2401h_style4_32','sharp_x68000_16','ibm_pcdos_kai_24','ibm_pcdos_hei_24','ibm_pcdos_fangsong_24','nokia_dct3_1999','fmtowns_f20_20','sun_gbk_song_12','sun_gbk_song_14','sun_gbk_song_16','sun_gbk_song_20','sun_gbk_song_24','sun_gb2312_song_12','sun_gb2312_song_14','sun_gb2312_song_20')]==rows
assert 'row.acquisitionGuide.notice' in (R/'app.js').read_text()
print('Acquisition:199 retained concise guides; static/dynamic data match;11 priorities; all other row metadata, IDs and PSA contact guidance preserved.')
