from approved_four import before_four_rows,before_four_data,IDS
"""Exact 247-row preservation and fixed-source HITECH scope."""
from pathlib import Path
import copy,hashlib,json,subprocess
from approved_hitech_adp3 import before_hitech_adp3_bytes,before_hitech_adp3_data
ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((ROOT/p).read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
digest=lambda v:sha(json.dumps(v,ensure_ascii=False,sort_keys=True).encode())
m=read('data/release-hitech-adp3.json');rows=before_four_rows(read('data/catalog.json'));ID='hitech_adp3_24'
assert len(rows)==248 and len({r['id'] for r in rows})==248
r=rows[-1];assert r['id']==ID and r['priority']==0 and r['sourceIndex']==285
assert digest(r)==m['addedRowSha256']
old=rows[:-1];assert len(old)==247 and digest(old)==m['baseRowsSha256']
assert digest({r['id']:sha((ROOT/r['specimen']).read_bytes()) for r in old})==m['baseSpecimensSha256']
assert digest({r['id']:sha((ROOT/'fonts'/f"{r['id']}.html").read_bytes()) for r in old})==m['basePagesSha256']
assert [r['id'] for r in sorted(rows,key=lambda r:-r['priority']) if r['priority']>0]==m['baseRecommendedIds']
assert len(m['baseRecommendedIds'])==17
for p,expected in m['baseFilesSha256'].items():assert sha(before_hitech_adp3_bytes(p))==expected,p
assert before_hitech_adp3_data('data/summary.json',read('data/summary.json'))==m['baseSummary']
assert r['asciiOrigin']=='absent' and not r['asciiText'] and 'asciiPairing' not in r
assert r['nativeEvidence']['big5Han']==13061 and r['nativeEvidence']['compatibilityHan']==2 and r['nativeEvidence']['cp950ExtensionHan']==7
assert not any('xeen' in row['id'].lower() for row in rows)
assert before_four_data('data/collection-history.json',read('data/collection-history.json'))['batches'][-1]=={'sourceManifest':'release-hitech-adp3.json','ids':[ID]}
assert len([p for p in (ROOT/'fonts').glob('*.html') if p.stem not in IDS])==248
for data,path in [(copy.deepcopy(rows),'data/catalog.json'),(copy.deepcopy(read('data/collection-history.json')),'data/collection-history.json')]:
 if isinstance(data,list):data[-1]['name']+=' UNREVIEWED'
 else:data['batches'][-1]['ids'].append('UNREVIEWED')
 try:before_hitech_adp3_data(path,data)
 except AssertionError:pass
 else:raise AssertionError('Unreviewed normalization')
print('HITECH integration: original 247 metadata, previews, pages, 17 recommendations, UI and historical hashes PASS')
# Prove normalization cannot hide edits to original rows, counters, UI or pages.
import tempfile,shutil
with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    paths=list(m['baseFilesSha256'])+[f"fonts/{old[0]['id']}.html",old[0]['specimen']]
    for p in paths:
        target=td/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/p).read_bytes())
    for key in ('name','priority'):
        altered=copy.deepcopy(rows)
        if key=='name':altered[0][key]+=' UNREVIEWED'
        else:altered[0][key]+=1
        (td/'data/catalog.json').write_text(json.dumps(altered,ensure_ascii=False,indent=2)+'\n')
        assert sha(before_hitech_adp3_bytes('data/catalog.json',td))!=m['baseFilesSha256']['data/catalog.json']
    (td/'data/catalog.json').write_bytes((ROOT/'data/catalog.json').read_bytes())
    for p in ('data/summary.json','app.js','styles.css'):
        raw=(td/p).read_bytes()
        if p.endswith('.json'):
            altered=json.loads(raw);altered['rows']+=1;data=(json.dumps(altered,ensure_ascii=False,indent=2)+'\n').encode()
        else:data=raw+b'\n/* unreviewed */\n'
        (td/p).write_bytes(data)
        assert sha(before_hitech_adp3_bytes(p,td))!=m['baseFilesSha256'][p]
        (td/p).write_bytes(raw)
    p=f"fonts/{old[0]['id']}.html";raw=(td/p).read_bytes();(td/p).write_bytes(raw+b'<!-- unreviewed -->')
    assert sha((td/p).read_bytes())!=sha((ROOT/p).read_bytes())
    p=old[0]['specimen'];raw=(td/p).read_bytes();(td/p).write_bytes(raw+b'unreviewed')
    assert sha((td/p).read_bytes())!=sha((ROOT/p).read_bytes())
print('HITECH preservation negative controls: original metadata, weights, summary, UI, pages and PNG tampering detected')

rel=r["nativeEvidence"]["relatedSource"]
assert rel["commonBig5SourceCodes"]==rel["exactInvertedCells"]==13494
assert rel["hanSourceVariants"]==13065 and rel["uniqueHan"]==13063
assert rel["sourceSha256"]=="813b175212ff8cf5fe2d43d85332ca6589a325f2cdcf7dc5e339a7f19a89fe1f"
assert rel["sourceUrl"]=="https://archive.org/details/windows-3.1-traditional-chinese"
assert any(link["url"]==rel["sourceUrl"] for link in r["acquisitionGuide"]["links"])
assert r["nativeEvidence"]["source_sha256"]=="1f46c0240a1a840f944baed0627c734351672c0dd388528313c9421d6a957121"
assert not any(row["id"].lower().startswith("mingli20") for row in rows)
print("Merged MINGLI24 provenance-only scope PASS")

assert (rel["asciiCellWidth"],rel["asciiCellHeight"],rel["asciiPhysicalSlots"])==(12,24,128)
assert rel["asciiShownInPreview"] is False and r["asciiText"]==""
