"""Approved Sharp16 addition, exact prior207 rows and no duplicate24 entry."""
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/catalog.json').read_text());m=json.loads((R/'data/release-sharp-x68000.json').read_text())
new=[r for r in rows if r['id']=='sharp_x68000_16'];base=[r for r in rows if r['id']!='sharp_x68000_16']
assert len(new)==1 and len(base)==207 and len(rows)==208
assert hashlib.sha256(json.dumps(base,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m['baseRowsSha256']
r=new[0];assert r['id']==m['addedId'] and r['priority']==0
assert r['width']==r['height']==r['cellWidth']==r['cellHeight']==16
assert not any(x['id'].startswith('sharp_x68000') and x['id']!='sharp_x68000_16' for x in rows)
assert sum(x['priority']>0 for x in rows)==13
assert r['text']=='視野無限廣，窗外有藍天。' and r['asciiText']=='0123456789 AaBb GgMm !?:+-.'
assert r['missing']==r['hanMissing']==r['asciiMissing']==[] and r['asciiOrigin']=='native'
assert '不代表全库去重' in r['notes'] and '24点' in r['notes'] and 'IPL' in r['licenseNote']
assert '1987年首批' in r['provenance'] and '不能' in r['provenance']
assert '6877' in r['acquisitionGuide']['notice'] and 'ANK只在固定样图展示' in r['acquisitionGuide']['notice']
png=(R/r['specimen']).read_bytes();assert struct.unpack('>II',png[16:24])==(216,34)
assert hashlib.sha256(png).hexdigest()==r['specimenSha256']==m['sampleSha256']
assert m['hanzi']==6353 and m['mappedJis']==6877 and m['physicalJisSlots']==7238
for p in ['docs/sharp-x68000.md','scripts/sharp_x68000_to_bdf.py','fonts/sharp_x68000_16.html']:assert (R/p).is_file()
assert r['acquisitionGuide']['links'][0]['url'].endswith('/docs/sharp-x68000.md')
print('Sharp16: exact207 baseline, native pixels, JIS/ANK mapping limits, no duplicate24, no new recommendation.')
