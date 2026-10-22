#!/usr/bin/env python3
"""Apply a manually reviewed local BDF preview to an existing catalog entry. Does not publish."""
from pathlib import Path
import argparse,json,hashlib,shutil,collections
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--id',required=True);p.add_argument('--report',required=True);p.add_argument('--reviewed-source-and-glyphs',action='store_true',required=True);a=p.parse_args()
report=Path(a.report).resolve();local=(ROOT/'local-research').resolve()
if not report.is_relative_to(local):p.error('Report must be under local-research/')
x=json.loads(report.read_text());assert x['format']=='bdf-bitmap-preview-v1';assert 1<=len(x['lines'])<=2
png=(report.parent/x['png']).resolve();assert png.parent==report.parent;assert hashlib.sha256(png.read_bytes()).hexdigest()==x['specimenSha256']
rows=json.loads((ROOT/'data/catalog.json').read_text());row=next((r for r in rows if r['id']==a.id),None)
if row is None:p.error('Only existing IDs can be updated; new source records require explicit curation.')
# Preserve a reversible local snapshot before changing public artifacts.
backup=local/'before-apply'/a.id;backup.mkdir(parents=True,exist_ok=True)
if (backup/'catalog-row.json').exists():p.error('A previous backup exists; review it before another apply.')
(backup/'catalog-row.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n');shutil.copy2(ROOT/row['specimen'],backup/'specimen.png')
row.update(text=x['lines'][0]['text'],asciiText=x['lines'][1]['text'] if len(x['lines'])==2 else '',hanMissing=x['lines'][0]['missing'],asciiMissing=x['lines'][1]['missing'] if len(x['lines'])==2 else [],missing=x['missing'],specimenWidth=x['specimenWidth'],specimenHeight=x['specimenHeight'],specimenSha256=x['specimenSha256'])
row['coverage']='部分字符未覆盖' if row['missing'] else '样文完整'
if row['sampleKind']!='osd':row['sampleKind']='partial' if row['missing'] else 'standard'
row.pop('omittedEmptyLines',None)
row['previewBuild']={'sourceSha256':x['sourceSha256'],'encoding':x['encoding'],'method':x['method']}
shutil.copy2(png,ROOT/row['specimen']);(ROOT/'data/catalog.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
s=json.loads((ROOT/'data/summary.json').read_text());ordinary=[r for r in rows if r['sampleKind']!='osd'];s.update(rows=len(rows),nativePngCount=len(rows),ordinaryRows=len(ordinary),sampleKinds=dict(collections.Counter(r['sampleKind'] for r in rows)),standardChineseComplete=sum(not r.get('hanMissing') for r in ordinary),partialChinese=sum(bool(r.get('hanMissing')) for r in ordinary),standardAsciiComplete=sum(not r.get('asciiMissing') for r in ordinary),partialAscii=sum(bool(r.get('asciiMissing')) for r in ordinary));(ROOT/'data/summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print('Preview applied locally. Review notes/provenance/ASCII-layer wording for the new sample, then run workspace.py build and check. No publication performed.')
