from approved_latin_update import historical_rows
"""Exact additive Psion batch; historical rows and user withdrawals remain intact."""
from pathlib import Path
import json,hashlib,struct,sys
R=Path(__file__).resolve().parents[1]
rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id'] not in ('ps2_scph50009_24','win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18')];m=json.loads((R/'data/release-psion618c.json').read_text())
base=[r for r in rows if r['id'] in m['baseIds']];new=[r for r in rows if r['id'] in m['addedIds']]
assert len(rows)==222 and len(base)==219 and len(new)==2
for group,k in [(base,'baseRowsSha256'),(new,'addedRowsSha256')]:assert hashlib.sha256(json.dumps(historical_rows(group),ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m[k]
assert [r['id'] for r in new]==m['addedIds']
for r,n,coverage in zip(new,(8,11),(15441,15447)):
 assert r['priority']==0 and r['height']==n and r['scripts']==['简体','繁体']
 assert r['nativeEvidence']['nonblankHan']==coverage and r['nativeEvidence']['gb2312Han']==6763
 b=(R/r['specimen']).read_bytes();assert hashlib.sha256(b).hexdigest()==r['specimenSha256']
 assert struct.unpack('>II',b[16:24])==(r['specimenWidth'],r['specimenHeight'])
 assert r['missing']==[] and r['asciiText']=='0123456789 AaBb GgMm !?:+-.' and r['asciiOrigin']=='native' and r['asciiPairing']['family']=='Arial'
assert not any(r['id'] in ('psion618c_15','panasonic_tutx100_16x24') for r in rows)
h=json.loads((R/'data/collection-history.json').read_text());assert next(b for b in h['batches'] if b['sourceManifest']=='release-psion618c.json')['ids']==m['addedIds']
sys.path.insert(0,str(R/'scripts'));from psion_gdr_to_bdf import decode
try:decode(b'not a GDR',8)
except ValueError:pass
else:raise AssertionError('Input hash check missing')
print('Psion: 2 exact additions; 219 old rows unchanged; fixed PNGs, source-only exporter.')
