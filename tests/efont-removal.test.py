from approved_rongta import IDS as RONGTA_IDS
from approved_cxdos import IDS as CXDOS_IDS
from approved_jqk import IDS as JQK_IDS
from approved_gtwin import IDS as GTWIN_IDS
from approved_h01 import IDS as H01_IDS
from approved_palm_gbk24 import IDS as PALM_GBK24_IDS
from approved_zhenhan import IDS as ZHENHAN_IDS
from approved_wonder import IDS as WONDER_IDS
from approved_advisor import IDS as ADVISOR_IDS
from approved_emperor import IDS as EMPEROR_IDS
from approved_simsun import IDS as SIMSUN_IDS, before_simsun_bytes
"""Explicit 2026-10-28 /efont/ Unicode family removal, not a string purge."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/catalog.json').read_text());curation=json.loads((R/'data/curation.json').read_text())
removed={'efont_biwidth_10','efont_biwidth_12','efont_biwidth_14','efont_biwidth_16','efont_biwidth_24'}
assert set(curation['postEfontRemovedIds'])=={'efont_biwidth_16','efont_biwidth_24'}
assert removed<=set(curation['removedIds'])
assert not any(r['id'].startswith('efont_') or r['family']=='/efont/ Unicode' for r in rows)
for id in removed:
 assert not (R/'fonts'/f'{id}.html').exists()
 assert not (R/'assets/specimens'/f'{id}.png').exists()
 for name in ['index.html','sitemap.xml','data/catalog.js']:
  assert id not in (R/name).read_text()
assert {'ayu_gothic_18','ayu_gothic_20'}<={r['id'] for r in rows},'Do not remove separate Sazanami-hosted Ayu fonts by URL substring'
assert len([r for r in rows if r['id'] not in (SIMSUN_IDS + EMPEROR_IDS + ADVISOR_IDS + WONDER_IDS + ZHENHAN_IDS + PALM_GBK24_IDS + H01_IDS + GTWIN_IDS + JQK_IDS + CXDOS_IDS + RONGTA_IDS) and r['id'] not in ('sc_song_13', 'ms_song_14', 'siemens_xelibri_14', 'hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')])==244 and len([p for p in (R/'fonts').glob('*.html') if p.stem not in (SIMSUN_IDS + EMPEROR_IDS + ADVISOR_IDS + WONDER_IDS + ZHENHAN_IDS + PALM_GBK24_IDS + H01_IDS + GTWIN_IDS + JQK_IDS + CXDOS_IDS + RONGTA_IDS) and p.stem not in ('sc_song_13', 'ms_song_14', 'siemens_xelibri_14', 'hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')])==244
print('efont removal: all five known Unicode sizes excluded; two current entries/assets/pages removed; independent Ayu family retained.')
