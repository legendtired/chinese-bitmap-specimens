#!/usr/bin/env python3
"""Refresh catalogue counters; reference images never count as native glyph coverage."""
from pathlib import Path
import json,collections
ROOT=Path(__file__).resolve().parents[1]
def refresh(root=ROOT):
 rows=json.loads((root/'data/catalog.json').read_text())
 p=root/'data/summary.json';s=json.loads(p.read_text()) if p.exists() else {}
 native=[r for r in rows if r.get('sampleKind')!='reference']
 ordinary=[r for r in native if r.get('sampleKind')!='osd']
 ascii_rows=[r for r in ordinary if r.get('asciiText') and r.get('asciiOrigin') not in ['native-fullwidth','fullwidth-native','fullwidth','not-present','not-in-source','none','absent']]
 heights=[r['height'] for r in native if isinstance(r.get('height'),(int,float))]
 s.update(catalogVersion=17,rows=len(rows),nativePngCount=len(native),variableGridRows=sum(bool(r.get('variableGrid')) for r in native),referenceRows=len(rows)-len(native),ordinaryRows=len(ordinary),sampleKinds=dict(collections.Counter(r['sampleKind'] for r in rows)),scripts=dict(collections.Counter(v for r in rows for v in r['scripts'])),minCellHeight=min(heights),maxCellHeight=max(heights),standardChineseComplete=sum(not r.get('hanMissing') for r in ordinary),partialChinese=sum(bool(r.get('hanMissing')) for r in ordinary),standardAsciiComplete=sum(not r.get('asciiMissing') and not any(ord(c)<128 for c in r.get('renderOmitted',[])) for r in ascii_rows),partialAscii=sum(bool(r.get('asciiMissing')) or any(ord(c)<128 for c in r.get('renderOmitted',[])) for r in ascii_rows),ordinaryAsciiRows=len(ascii_rows),ordinaryWithoutAsciiEvaluation=len(ordinary)-len(ascii_rows),renderOmittedRows=sum(bool(r.get('renderOmitted')) for r in native),designHeightRows=sum(r.get('heightBasis')=='han-design-grid' for r in native),fontFilesIncluded=0,glyphDataIncluded=False)
 s.setdefault('curation',{})['removedBySelection']=len(json.loads((root/'data/curation.json').read_text())['removedIds'])
 s['coverageRule']='Reference screenshots/standard diagrams are not glyph coverage tests. Fullwidth samples and sources without ASCII are not counted as complete ordinary ASCII.'
 p.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');return s
if __name__=='__main__':
 s=refresh();print(f"Summary: {s['rows']} records; {s['nativePngCount']} native specimens; {s['referenceRows']} reference images.")
