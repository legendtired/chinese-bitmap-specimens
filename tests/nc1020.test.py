"""Approved NC1020 addition, fixed preview only, exact baseline preservation."""
from pathlib import Path
import json,hashlib,subprocess,sys,tempfile
R=Path(__file__).resolve().parents[1]; rows=json.loads((R/'data/catalog.json').read_text())
assert hashlib.sha256(json.dumps([r for r in rows if r['id']!='wqx_nc1020_12'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()==json.loads((R/'data/release-nc1020.json').read_text())['baseRowsSha256']
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
