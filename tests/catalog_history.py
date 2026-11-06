from approved_latin_update import historical_rows
"""Explicit historical view for release audits. Never imported by the site or builder."""
import json,hashlib
def before_solaris_withdrawal(root):
 current=[r for r in json.loads((root/'data/catalog.json').read_text()) if r['id'] not in ('ps2_scph50009_24','win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18','palm_cjkos_fgb12ktf','palm_cjkos_fgb12fsf','palm_cjkos_fb512kbf','palm_cjkos_fb512xmf','psion618c_8','psion618c_11')]
 m=json.loads((root/'data/withdrawal-solaris-gb2312.json').read_text())
 ids=set(m['removedIds']);assert not ids.intersection(r['id'] for r in current)
 assert hashlib.sha256(json.dumps(historical_rows(current),ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m['retainedRowsSha256']
 by={r['id']:r for r in current+m['removedRows']}
 assert len(by)==len(m['priorIds'])==222
 restored=[by[i] for i in m['priorIds']]
 assert hashlib.sha256(json.dumps(historical_rows(restored),ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m['priorRowsSha256']
 return restored
