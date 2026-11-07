from approved_p908_merge import restore_sun, historical_file_sha
"""Approved Song40 addition, immutable prior catalog and private source redraw."""
import hashlib, io, json, os, subprocess, sys, tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads((R/p).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(o):return sha(json.dumps(o,ensure_ascii=False,sort_keys=True).encode())
rows=read('data/catalog.json');m=read('data/release-hpux-song.json')
base=[r for r in rows if r['id'] in m['baseIds']]
added=[r for r in rows if r['id'] in m['addedIds']]
assert len(rows)==len({r['id'] for r in rows})==239
assert len(base)==233 and digest(restore_sun(base))==m['baseRowsSha256']
assert len(added)==1 and digest(added)==m['addedRowsSha256']
assert [r['id'] for r in rows if r.get('priority',0)>0]==m['preservedRecommendedIds']
assert len(m['preservedRecommendedIds'])==13
for r in rows:assert sha((R/r['specimen']).read_bytes())==r['specimenSha256'],r['id']
r=added[0];assert r['id']=='hpux_song_40' and r['priority']==0
assert (r['width'],r['height'],r['cellWidth'],r['cellHeight'])==(40,40,40,40)
assert r['asciiOrigin']=='absent' and r['asciiText']=='' and len(r['asciiMissing'])==95
assert r['missing']==r['hanMissing']==[] and r['nativeEvidence']['gb2312HanCovered']==6763
s=read('data/summary.json');assert s['rows']==239 and s['nativePngCount']==238
for k in ['standardAsciiComplete','ordinaryAsciiRows']:assert s[k]==m['previousSummary'][k]+5
assert s['partialAscii']==m['previousSummary']['partialAscii']
assert s['ordinaryWithoutAsciiEvaluation']==m['previousSummary']['ordinaryWithoutAsciiEvaluation']+1
assert s['fontFilesIncluded']==0 and not s['glyphDataIncluded']
assert {'sourceManifest':'release-hpux-song.json','ids':m['addedIds']} in read('data/collection-history.json')['batches']
audit=read('data/hpux-song-independent-audit.json');assert audit['status']=='passed' and audit['glyphs']==7546 and audit['pixelsCompared']==12073600 and audit['missing']==[]
d=read('data/hpux-song-dedup.json');assert len(d['references'])==221
assert sum(x['compared'][0]['common']>0 for x in d['references'])==211
assert all(x['compared'][0]['crop']==x['compared'][0]['whole']==0 for x in d['references'])
p=d['sampleOnlySupplement'];assert p['currentCatalogCount']==233 and p['publicNativeSpecimensChecked']==232
assert len(p['results'])==232 and all(not x['matchedHan'] for x in p['results'])
sys.path.insert(0,str(R/'scripts'));from render_hpux_song import render
with tempfile.TemporaryDirectory() as tmp:
 bad=Path(tmp)/'bad.pcf';bad.write_bytes(b'bad')
 try:render(bad)
 except ValueError:pass
 else:raise AssertionError('Incorrect source accepted')
 out=Path(tmp)/'exists';out.mkdir()
 proc=subprocess.run([sys.executable,str(R/'scripts/render_hpux_song.py'),str(bad),str(out)],capture_output=True,text=True)
 assert proc.returncode!=0 and 'Output must not already exist' in proc.stderr
if os.environ.get('HPUX_SONG_PCF'):
 image=render(Path(os.environ['HPUX_SONG_PCF']));buffer=io.BytesIO();image.save(buffer,format='PNG')
 assert image.size==(488,48) and buffer.getvalue()==(R/r['specimen']).read_bytes()
 print('Song40 exact private source redraw passed.')
else:print('Song40 private source integration not run: PCF not supplied.')
print('Song40: one addition; all 233 prior rows, PNG hashes and 13 recommendations preserved.')
