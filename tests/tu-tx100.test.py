"""Additive, byte-exact old catalog preservation and safe source-specific export."""
import hashlib, importlib.util, json, pathlib, tempfile
R=pathlib.Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/catalog.json').read_text()); manifest=json.loads((R/'data/release-panasonic-tutx100.json').read_text())
new=[r for r in rows if r['id'] in manifest['addedIds']];old=[r for r in rows if r['id'] not in manifest['addedIds']]
assert len(new)==1 and len(old)==219 and len(rows)==220
assert hashlib.sha256(json.dumps(old,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==manifest['baseRowsSha256']
r=new[0];assert (r['width'],r['height'],r['cellWidth'],r['cellHeight'])==(16,24,16,24)
assert r['priority']==0 and r['asciiOrigin']=='fullwidth-native'
assert r['missing']==['廣','窗']
assert hashlib.sha256((R/r['specimen']).read_bytes()).hexdigest()==r['specimenSha256']
assert '作者标称' in r['provenance'] and '未独立' in r['provenance']
assert json.loads((R/'data/collection-history.json').read_text())['batches'][-1]['ids']==manifest['addedIds']
assert len(list((R/'fonts').glob('*.html')))==220
spec=importlib.util.spec_from_file_location('tu',R/'scripts/tu_tx100_to_bdf.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as d:
 bad=pathlib.Path(d)/'bad.inc';bad.write_text('not a font')
 try:m.read_font(bad)
 except ValueError:pass
 else:raise AssertionError('Unvalidated source accepted')
 out=pathlib.Path(d)/'synthetic.bdf';m.write_bdf({65:tuple([0x8000]+[0]*23)},out)
 s=out.read_text();assert 'CHARS 1' in s and 'BBX 16 24 0 0' in s and '8000' in s
 try:m.write_bdf({},out)
 except FileExistsError:pass
 else:raise AssertionError('Existing output overwritten')
print('TU-TX100: exact219-row baseline preserved, one approved fixed sample, source-only exporter and safe output verified.')
