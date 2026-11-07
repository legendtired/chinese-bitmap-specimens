from approved_recommendation_update import before_recommendations
from approved_latin_update import historical_rows
"""Current scope and exact retention after explicit three-font withdrawal."""
from pathlib import Path
import json,hashlib
from catalog_history import before_solaris_withdrawal
R=Path(__file__).resolve().parents[1];m=json.loads((R/'data/withdrawal-solaris-gb2312.json').read_text());rows=[r for r in before_recommendations(json.loads((R/'data/catalog.json').read_text())) if r['id'] not in ('sony_ericsson_p802_12','sony_ericsson_p908_14','nokia_9210c_15','nokia_9210c_17','nokia_9210c_19','aix_isas_cns_24','hpux_song_40','hpux_sung_24','hpux_sung_34','hpux_sung_42','samsung_r208_16','sunplus_sphe8202l_16x16','sunplus_sphe8202l_20x24','ps2_scph50009_24','win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18','palm_cjkos_fgb12ktf','palm_cjkos_fgb12fsf','palm_cjkos_fb512kbf','palm_cjkos_fb512xmf','psion618c_8','psion618c_11')];old=before_solaris_withdrawal(R)
ids=set(m['removedIds']);assert ids=={f'sun_gb2312_song_{n}' for n in (12,14,20)}
assert len(rows)==len({r['id']for r in rows})==219
assert rows==[r for r in old if r['id']not in ids]
assert hashlib.sha256(json.dumps(historical_rows(rows),ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m['retainedRowsSha256']
by={r['id']:r for r in rows};assert all(i in by for i in m['preservedSolarisIds']);assert len(m['preservedSolarisIds'])==5
assert [r for r in rows if r['priority']>0]==[r for r in old if r['priority']>0]
c=json.loads((R/'data/curation.json').read_text());assert set(c['postSolarisGb2312RemovedIds'])==ids and ids<=set(c['removedIds'])
h=json.loads((R/'data/collection-history.json').read_text());assert not ids.intersection(i for b in h['batches']for i in b['ids'])
assert next(b for b in h['batches'] if b['sourceManifest']=='release-pc505-collection.json')['ids']==['wqx_pc505_14x15']
for r in m['removedRows']:
 assert not (R/r['specimen']).exists();assert not (R/'fonts'/f"{r['id']}.html").exists()
 assert r['id']not in (R/'index.html').read_text() and r['id']not in (R/'sitemap.xml').read_text()
assert len(list((R/'fonts').glob('*.html')))==239
print('Solaris withdrawal: exactly three absent, five GBK preserved, all other219 rows exact, recommendations and newest PC505 retained.')

# Withdrawn-only acquisition material is excluded from this GitHub synchronization.
for p in ['docs/solaris-gb2312.md', 'scripts/solaris_gb2312_to_bdf.py', 'tests/solaris-gb2312-export.test.py', 'tests/solaris-gb2312.test.py', 'data/release-solaris-gb2312.json']:
 assert not (R/p).exists(), p
assert '(solaris-gb2312.md)' not in (R/'docs/research-notes.md').read_text()
