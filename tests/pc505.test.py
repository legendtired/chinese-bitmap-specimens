#!/usr/bin/env python3
"""Additive PC505 overlay invariants; no fixed global catalog size/index."""
from approved_recommendation_update import before_recommendations
from pathlib import Path
import hashlib,json,struct,unittest
ROOT=Path(__file__).resolve().parents[1];ID='wqx_pc505_14x15'
class OverlayTests(unittest.TestCase):
 def setUp(self):
  self.rows=json.loads((ROOT/'data/pc505-catalog-overlay.json').read_text());self.r=self.rows[0]
  self.release=json.loads((ROOT/'data/release-pc505.json').read_text())
 def test_one_additive_id(self):
  self.assertEqual(len(self.rows),1);self.assertEqual(self.r['id'],ID);self.assertNotIn('sourceIndex',self.r)
  self.assertFalse(self.release['collectionBatchAssigned']);self.assertEqual(self.r['priority'],0)
 def test_native_dimensions(self):
  self.assertEqual([self.r[k]for k in ('width','height','cellWidth','cellHeight')],[14,15,14,15])
  self.assertEqual(self.r['nativeEvidence']['asciiStorageCell'],[8,16]);self.assertEqual(self.r['nativeEvidence']['globalExportBounds'],[14,16,0,0])
  self.assertEqual(self.r['styles'],['未分类'])
 def test_coverage(self):
  self.assertEqual(self.release['glyphCounts'],{'gbSlots':7599,'gbMapped':7445,'han':6763,'asciiSlots':128,'asciiMapped':95,'combinedMapped':7540})
  for k in ['missing','hanMissing','asciiMissing']:self.assertEqual(self.r[k],[])
  self.assertEqual(self.r['asciiOrigin'],'native')
 def test_source_bounds(self):
  self.assertFalse(self.r['nativeEvidence']['physicalDumpVerified']);self.assertEqual(self.r['sourceUrl'],'https://archive.org/details/wqxarchive')
  self.assertEqual(self.r['acquisitionGuide']['links'],[{'label':'查看历史资料集','url':'https://archive.org/details/wqxarchive','action':'source'}])
  self.assertIn('不是',self.r['provenance']);self.assertIn('导出约定',self.r['layoutNote'])
 def test_png(self):
  raw=(ROOT/self.r['specimen']).read_bytes();self.assertEqual(raw[:8],b'\x89PNG\r\n\x1a\n')
  self.assertEqual(struct.unpack('>II',raw[16:24]),(216,36));self.assertEqual(hashlib.sha256(raw).hexdigest(),self.r['specimenSha256'])
  self.assertEqual(self.release['specimen']['sha256'],self.r['specimenSha256'])
 def test_no_full_font_in_public_roots(self):
  for d in ['assets','data','docs','scripts','tests']:
   for p in (ROOT/d).rglob('*'):
    if p.is_file()and ID in p.name:self.assertNotIn(p.suffix.lower(),['.bdf','.bin','.rom','.rar','.zip','.pcf'])
 def test_integrated_row_if_present(self):
  p=ROOT/'data/catalog.json'
  if p.exists():
   rows=before_recommendations(json.loads(p.read_text()));selected=[r for r in rows if r['id']==ID];self.assertEqual(len(selected),1)
   assigned=selected[0].copy();index=assigned.pop('sourceIndex');self.assertIsInstance(index,int)
   self.assertEqual(assigned,self.r);self.assertEqual(sum(r.get('sourceIndex')==index for r in rows),1)
 def test_allowlist_if_packaged(self):
  p=ROOT/'PUBLIC-FILES.json'
  if p.exists():
   manifest=json.loads(p.read_text());self.assertEqual(len(manifest),7)
   for x in manifest:
    path=ROOT/x['path'];raw=path.read_bytes();self.assertEqual(len(raw),x['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),x['sha256'])
if __name__=='__main__':unittest.main(verbosity=2)
