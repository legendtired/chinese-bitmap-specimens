from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/catalog.json').read_text());hs=[r for r in rows if r['id'].startswith('hanyi-')]
assert len(hs)==4
assert set(json.loads((R/'data/curation.json').read_text())['postV17ModifiedIds'])=={r['id'] for r in hs}
for r in hs:
 g=r['acquisitionGuide'];assert g['steps']==[] and '不等于免费商用' in g['notice']
 assert g['links'][0]['url']==r['sourceUrl']
 page=(R/'fonts'/f"{r['id']}.html").read_text()
 for item in g['links']:assert item['url'].replace('&','&amp;') in page
 assert '获取方式' in page and '个人非商用许可协议' in page
assert 'row.acquisitionGuide' in (R/'app.js').read_text()
print('Hanyi guidance:4 official acquisition sections, cautious personal/commercial scope and no direct downloads; recommendation checked separately.')

assert {r['designHeight'] for r in hs}=={9,11,13,15}
for r in hs:
 assert r['gridReconstruction'] and r['heightBasis']=='han-design-grid'
 assert all(r[k] is None for k in ['width','height','cellWidth','cellHeight'])
 assert r['nativeEvidence']['bitmap_tables']==[] and not r['missing']
 assert '设计格点 · 1×' in (R/'fonts'/f"{r['id']}.html").read_text()
r=next(r for r in hs if r['designHeight']==11)
assert r['renderOmitted']==[':'] and not r['asciiMissing'] and '不是原字体缺字' in r['renderOmissionNote']
