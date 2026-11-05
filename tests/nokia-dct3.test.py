"""Approved Nokia addition with unchanged211-row local IBM-inclusive baseline."""
from pathlib import Path
import json,hashlib,struct
R=Path(__file__).resolve().parents[1];rows=[r for r in json.loads((R/'data/catalog.json').read_text()) if r['id'] not in ('wqx_pc505_14x15','fmtowns_f20_20', 'sun_gbk_song_12', 'sun_gbk_song_14', 'sun_gbk_song_16', 'sun_gbk_song_20', 'sun_gbk_song_24', 'sun_gb2312_song_12', 'sun_gb2312_song_14', 'sun_gb2312_song_20')];m=json.loads((R/'data/release-nokia-dct3.json').read_text());fid='nokia_dct3_1999';new=[r for r in rows if r['id']==fid];base=[r for r in rows if r['id']!=fid]
assert len(rows)==212 and len(base)==211 and len(new)==1
assert [r['id'] for r in base]==m['baseIds']
assert hashlib.sha256(json.dumps(base,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m['baseRowsSha256']
r=new[0];assert r['id']==m['addedId'] and r['sourceIndex']==m['sourceIndex']==243
assert r['sourceIndex'] not in {x['sourceIndex'] for x in base}
assert r['width']==r['cellWidth']==11 and r['height']==r['cellHeight']==12
assert r['scripts']==['简体','繁体'] and r['priority']==0 and sum(x['priority']>0 for x in rows)==13
assert r['text']=='视野无限广，窗外有蓝天。' and r['asciiText']=='0123456789 AaBb GgMm !?:+-.'
assert r['missing']==r['hanMissing']==r['asciiMissing']==[] and r['asciiOrigin']=='native'
assert '9004' in r['notes'] and '6763' in r['notes'] and '完整Big5或GBK' in r['notes']
assert '12×15' in r['notes'] and '不等宽' in r['notes'] and '不声称对全目录全部字形去重' in r['notes']
assert '1999-07-01' in r['provenance'] and '不据此推定' in r['provenance']
assert m['mappedUnicode']==9385 and m['hanzi']==9004 and m['gb2312Hanzi']==6763
assert m['nativeHanFrame']==[11,12] and m['nativeBdfBoundingBox']==[12,15,0,-4]
png=(R/r['specimen']).read_bytes();assert struct.unpack('>II',png[16:24])==(185,32)
assert hashlib.sha256(png).hexdigest()==r['specimenSha256']==m['specimenSha256']
for p in ['fonts/nokia_dct3_1999.html','scripts/nokia_dct3_to_bdf.py','docs/nokia-dct3.md']:assert (R/p).is_file()
assert not any(x['id'].startswith('nokia_dct3_') and x['id']!=fid for x in rows)
assert r['acquisitionGuide']['links'][0]['url'].endswith('/docs/nokia-dct3.md')
print('Nokia DCT3: preserved211 rows, one1999 native11x12 Han entry, 9385 codes/9004 Han/GB6763, native Latin/baseline preserved, no new recommendation.')
