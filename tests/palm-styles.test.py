from approved_latin_update import historical_rows
from pathlib import Path
import json,hashlib,struct,sys
R=Path(__file__).resolve().parents[1]
rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id'] not in ('hpux_song_40','hpux_sung_24','hpux_sung_34','hpux_sung_42','samsung_r208_16','sunplus_sphe8202l_16x16','sunplus_sphe8202l_20x24','ps2_scph50009_24','win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18')];m=json.loads((R/'data/release-palm-styles.json').read_text())
base=[r for r in rows if r['id'] in m['baseIds']];new=[r for r in rows if r['id'] in m['addedIds']]
assert len(rows)==222 and len(base)==221 and len(new)==1
for group,key in [(base,'baseRowsSha256'),(new,'addedRowsSha256')]: assert hashlib.sha256(json.dumps(historical_rows(group),ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m[key]
assert [r['id'] for r in rows[-1:]]==m['addedIds']
sys.path.insert(0,str(R/'scripts'));import cjkos_to_bdf as c
for r in new:
 assert r['priority']==0 and r['width']==r['height']==12
 assert r['missing']==[] and not historical_rows([r])[0]['asciiText']
 assert c.SOURCES[r['nativeEvidence']['source_sha256']]==(12,'gb2312' if r['scripts']==['简体'] else 'big5',True)
 b=(R/r['specimen']).read_bytes();assert hashlib.sha256(b).hexdigest()==r['specimenSha256'];assert struct.unpack('>II',b[16:24])==(r['specimenWidth'],r['specimenHeight'])
assert not any(r['id']=='palm_cjkos_fgb12stf' for r in rows)
h=json.loads((R/'data/collection-history.json').read_text());assert next(b for b in h['batches'] if b['sourceManifest']=='release-palm-styles.json')['ids']==m['addedIds']
print('Palm styles: 1 exact addition, 221 unchanged rows, checked source hashes and fixed PNGs.')

removed=['palm_cjkos_fgb12ktf', 'palm_cjkos_fgb12fsf', 'palm_cjkos_fb512kbf']
for fid in removed:
 assert not any(r["id"]==fid for r in rows)
 assert not (R/f"assets/specimens/{fid}.png").exists()
 assert not (R/f"fonts/{fid}.html").exists()
