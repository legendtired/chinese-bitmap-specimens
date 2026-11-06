from approved_latin_update import historical_rows
"""Five Solaris entries; exact prior rows, honest metrics/encoding, fixed PNGs.

Later independent additions may be present. Check this release's scoped row set,
not a global catalog count, so Nokia/FMTowns integration does not weaken checks.
"""
from pathlib import Path
import hashlib
import json
import struct
R=Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/catalog.json').read_text());m=json.loads((R/'data/release-solaris-gbk.json').read_text())
byid={r['id']:r for r in rows};ids=m['addedIds']
assert len(rows)==len(byid)
assert ids==[f'sun_gbk_song_{n}' for n in (12,14,16,20,24)]
base=[r for r in rows if r['id'] in m['baseIds']]
assert len(base)==211 and [r['id'] for r in base]==m['baseIds']
assert hashlib.sha256(json.dumps(historical_rows(base),ensure_ascii=False,sort_keys=True).encode()).hexdigest()==m['baseRowsSha256']
assert [r['id'] for r in rows if r['id'] in ids]==ids
assert not set(ids)&set(m['baseIds'])
assert sum(r['priority']>0 for r in base)==13
new_indices={byid[i]['sourceIndex'] for i in ids}
assert new_indices==set(range(244,249))
assert not new_indices&{r.get('sourceIndex') for r in rows if r['id'] not in ids}
assert m['copyrightYear']==1997 and m['fileDate']=='1998-07-23' and m['carrierVersion']=='1999-11'
assert m['inkRgba']==[30,34,30,255] and m['backgroundRgba']==[0,0,0,0] and m['lineGap']==4
assert 'U+0020 is absent' in m['layoutSpace']
for item in m['fonts']:
 r=byid[item['id']];n=item['cell'];e=r['nativeEvidence']
 assert r['family']=='Solaris 中易宋体' and r['priority']==0
 assert r['scripts']==['简体','繁体'] and r['styles']==['宋体 / 明朝']
 assert r['width']==r['height']==r['cellWidth']==r['cellHeight']==n
 assert r['inkWidth'] is None and r['inkHeight'] is None
 assert r['text']==m['sampleText']=='视野无限广，窗外有蓝天。'
 assert r['asciiText']==m['asciiText']=='0123456789 AaBb GgMm !?:+-.'
 assert r['asciiOrigin']=='native' and r['hanMissing']==[]
 assert r['missing']==r['asciiMissing']==[' ']
 assert 'U+0020' in r['notes'] and '排版留白' in r['notes'] and '94' in r['coverage']
 assert '95' in r['notes'] and '不猜映射' in r['notes']
 assert '1997' in r['provenance'] and '1998-07-23' in r['provenance'] and '1999-11' in r['provenance']
 assert '不是' in r['nativeEvidence']['summary'] and 'SWIDTH' in r['nativeEvidence']['summary']
 assert (e['sourceGlyphs'],e['unicodeMapped'],e['basicHan'],e['unmappedNativeCodes'])==(21980,21885,20902,95)
 assert (item['sourceGlyphs'],item['unicodeMapped'],item['basicHan'],item['unmapped'])==(21980,21885,20902,95)
 assert (e['fontAscent'],e['fontDescent'])=={12:(12,2),14:(13,3),16:(15,3),20:(19,3),24:(22,4)}[n]
 assert e['sourcePixelSize']==n+2==e['fontAscent']+e['fontDescent']
 assert e['source_sha256']==item['sourceSha256']
 assert '授权' in r['licenseStatus'] and '不分发PCF、BDF或完整字模' in r['licenseNote']
 assert r['sourceUrl']==m['sourcePage']=='https://archive.org/details/solaris-7-1199-sparc-cs'
 assert r['acquisitionGuide']['links'][0]['url'].endswith('/docs/solaris-gbk.md')
 png=(R/r['specimen']).read_bytes()
 assert png[:8]==b'\x89PNG\r\n\x1a\n' and png[24:26]==bytes([8,6])  # 8-bit RGBA
 assert struct.unpack('>II',png[16:24])==tuple(item['sampleDimensions'])==(27*n//2,2*n+4)
 assert hashlib.sha256(png).hexdigest()==r['specimenSha256']==item['sampleSha256']
 assert (R/'fonts'/f"{r['id']}.html").is_file()
assert len({r['sampleSha256'] for r in m['fonts']})==5
for p in ['docs/solaris-gbk.md','scripts/solaris_gbk_to_bdf.py','tests/solaris-export.test.py']:assert (R/p).is_file()
doc=(R/'docs/solaris-gbk.md').read_text();script=(R/'scripts/solaris_gbk_to_bdf.py').read_text()
for item in m['fonts']:
 assert item['sourceSha256'] in doc and item['sourceSha256'] in script
 assert str(item['sourceBytes']) in doc
for token in ['21980','21885','20902','95','U+0020','uncompress','native-gbk','O_NOFOLLOW','未确认','不提供']:
 assert token in doc
assert 'ENDFONT' not in json.dumps(m) and 'BITMAP' not in json.dumps(m)
# No raw/font payload or glyph dictionary accompanies these additions.
for f in (R/'assets').rglob('*sun_gbk_song*'):
 assert f.is_file() and f.suffix=='.png'
print('Solaris: 5 exact-source native sizes; exact211 previous rows and13 priorities; 21885 Unicode/21980 native, 95 unresolved, 94 ASCII and no space glyph; original global metrics, fixed PNGs and source-only converter.')
