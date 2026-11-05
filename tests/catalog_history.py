"""Explicit historical view for release audits. Never imported by the site or builder."""
import json,hashlib
def before_solaris_withdrawal(root):
 current=[r for r in json.loads((root/'data/catalog.json').read_text()) if r['id'] != 'panasonic_tutx100_16x24']
 m=json.loads((root/'data/withdrawal-solaris-gb2312.json').read_text())
 ids=set(m['removedIds']);assert not ids.intersection(r['id'] for r in current)
 assert hashlib.sha256(json.dumps(current,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m['retainedRowsSha256']
 by={r['id']:r for r in current+m['removedRows']}
 assert len(by)==len(m['priorIds'])==222
 restored=[by[i] for i in m['priorIds']]
 assert hashlib.sha256(json.dumps(restored,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m['priorRowsSha256']
 return restored
