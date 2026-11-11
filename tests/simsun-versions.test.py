from approved_emperor import before_emperor_rows,before_emperor_data,before_emperor_bytes,MANIFEST as emperor
"""Exact public SimSun 3.03/5.03 additions and narrow Founder relationship update."""
from PIL import Image
from pathlib import Path
import copy,json,sys
from approved_simsun import MANIFEST as m,IDS,sha,digest,before_simsun_rows,before_simsun_data,before_simsun_bytes,original_rows
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import generate_static as generator
read=lambda p:before_emperor_data(p,json.loads((R/p).read_text()))
rows=read('data/catalog.json');old=before_simsun_rows(rows)
assert IDS==['simsun_v303_12','simsun_v303_14','simsun_v503_12','simsun_v503_14']
assert len(rows)==len({r['id'] for r in rows})==256
assert [r['id'] for r in rows[-4:]]==IDS
assert len(old)==252 and digest(old)==m['baseRowsSha256']
assert set(original_rows())=={'founder_pixel12','founder_pixel14'}
replacement=m['founderRecommendationReplacement']
assert replacement['changes']=={'founder_pixel12':{'before':90,'after':0},'simsun_v503_12':{'before':1,'after':90}}
restored=copy.deepcopy(rows)
for row in restored:
 if row['id'] in replacement['changes']:
  change=replacement['changes'][row['id']]
  assert row['priority']==change['after']
  row['priority']=change['before']
assert digest(restored)==replacement['baseRowsSha256'], 'Only two approved recommendation weights may change'
assert len([r for r in rows if r['priority']>0])==20
for ident,before in original_rows().items():
 after=next(r for r in rows if r['id']==ident)
 assert {k for k in set(before)|set(after) if before.get(k)!=after.get(k)} <= ({'notes','relatedSources','priority'} if ident=='founder_pixel12' else {'notes','relatedSources'})
 assert after['specimen']==before['specimen']
assert digest({r['id']:sha(before_simsun_bytes(f"fonts/{r['id']}.html")) for r in old})==m['basePagesSha256']
assert digest({r['id']:sha((R/r['specimen']).read_bytes()) for r in old})==m['baseSpecimensSha256']
assert read('data/summary.json')==m['summary']
assert before_simsun_data('data/summary.json',m['summary'])==m['baseSummary']
assert read('data/collection-history.json')['batches'][-1]==m['batch']
assert [r['sourceIndex'] for r in rows[-4:]]==[290,291,292,293]
assert {r['family'] for r in rows[-4:]}=={'SimSun 中易宋体'}
assert [r['version'] for r in rows[-4:]]==['3.03','3.03','5.03','5.03']
for r in rows[-4:]:
 assert r['priority']==(90 if r['id']=='simsun_v503_12' else 1) and digest(r)==m['rowHashes'][r['id']]
 os='Windows XP' if r['version']=='3.03' else 'Windows 7'
 assert os in r['name'] and os in r['sampleLabel']
 assert '推荐' in r['sampleLabel'] and '未认证' in r['notes']
 before=m['recommendationUpdate']['rowsBefore'][r['id']]
 assert {k for k in set(before)|set(r) if before.get(k)!=r.get(k)}=={'priority','name','sampleLabel','notes','relatedSources'}
 assert before['priority']==0
 assert r['specimenSha256']==before['specimenSha256'] and r['nativeEvidence']==before['nativeEvidence']
 size=int(r['id'].rsplit('_',1)[1])
 assert (r['width'],r['height'],r['cellWidth'],r['cellHeight'])==(size,size,size,size)
 assert r['text']=='视野无限广，窗外有蓝天。'
 assert r['asciiText']=='' and r['asciiOrigin']=='absent'
 assert r['missing']==r['hanMissing']==r['asciiMissing']==[]
 evidence=r['nativeEvidence']
 assert evidence['fontVersion']==r['version'] and evidence['bitDepth']==1 and evidence['printableAscii']==0
 assert evidence['unicodeCount']==(21742 if r['version']=='3.03' else 28429)
 assert evidence['uniqueGlyphCount']==(21742 if r['version']=='3.03' else 28418)
 assert evidence['commonUnicodeAcrossVersions']==21741 and evidence['differentAdvanceCount']==0
 assert r['sampleKind']=='standard'
 raw=(R/r['specimen']).read_bytes();assert sha(raw)==r['specimenSha256']
 one=Image.open(R/r['specimen']).convert('RGBA')
 four=Image.open(R/r['specimen'].replace('.png','_4x.png')).convert('RGBA')
 assert one.size==(r['specimenWidth'],r['specimenHeight'])==(12*size,size)
 assert four.size==(one.width*4,one.height*4)
 assert four.tobytes()==one.resize(four.size,Image.Resampling.NEAREST).tobytes()
 assert set(one.get_flattened_data())=={(0,0,0,0),(28,31,33,255)}
 assert (R/'fonts'/f"{r['id']}.html").read_text()==generator.font_page(r)
 assert generator.article(r)+'\n' in (R/'index.html').read_text()
 assert (R/r['specimen']).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
for path,h in m['baseFilesSha256'].items():
 assert sha(before_simsun_bytes(path))==h,path
for path,h in m['changedFileHashes'].items():assert sha(before_emperor_bytes(path))==h,path
for path,h in m['addedFiles'].items():assert sha(before_emperor_bytes(path))==h,path
actual={str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.git' not in p.parts}
actual-=set(emperor['newPaths'])
assert actual==set(m['baseFilesSha256'])|set(m['newPaths']),actual-set(m['baseFilesSha256'])-set(m['newPaths'])
for path in actual:
 p=R/path
 assert not p.is_symlink() and p.stat().st_nlink==1,path
 assert p.suffix.lower() not in {'.ttc','.ttf','.otf','.fon','.fnt','.bdf','.pcf','.rom','.bin','.zip','.7z'},path
for ident in IDS+list(original_rows()):
 bad=copy.deepcopy(rows);next(r for r in bad if r['id']==ident)['name']+=' UNREVIEWED'
 try:before_simsun_rows(bad)
 except AssertionError:pass
 else:raise AssertionError('Mutated reviewed row accepted: '+ident)
bad=copy.deepcopy(read('data/collection-history.json'));bad['batches'][-1]['ids'].append('UNREVIEWED')
try:before_simsun_data('data/collection-history.json',bad)
except AssertionError:pass
else:raise AssertionError('Mutated history accepted')
print('SimSun versions: 252 retained previews; reviewed Founder relationship/recommendation updates and four native records; historical baseline, public scope and negative controls PASS.')
