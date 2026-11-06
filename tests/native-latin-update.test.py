"""Approved native Latin supplement; keep original Han rows and other entries."""
from pathlib import Path
import hashlib,json
from PIL import Image
from approved_latin_update import AFTER,BEFORE,u
R=Path(__file__).resolve().parents[1]
rows={r['id']:r for r in json.loads((R/'data/catalog.json').read_text())}
assert len(AFTER)==len(BEFORE)==9
for id,a in AFTER.items():
 assert rows[id]==a
 data=(R/a['specimen']).read_bytes()
 assert hashlib.sha256(data).hexdigest()==a['specimenSha256']
 im=Image.open(R/a['specimen']).convert('RGBA')
 assert im.size==(a['specimenWidth'],a['specimenHeight'])
 m=u['originalHanMasks'][id];crop=im.crop((0,0,*m['topSize']))
 mask=bytes(int(alpha>0 and red+green+blue<384) for red,green,blue,alpha in crop.getdata())
 assert hashlib.sha256(mask).hexdigest()==m['topMaskSha256']
 assert a['text']==BEFORE[id]['text'] and a['priority']==BEFORE[id]['priority']
 if id.startswith('stone'):
  assert a['asciiOrigin']=='fullwidth-native' and all(ord(c)>127 for c in a['asciiText'])
 elif id.startswith('ibm'):
  assert a['asciiOrigin']=='native' and '12×24' in a['notes'] and a['asciiText']=='ABCabc0123456789'
 else:
  assert a['asciiPairing']['kind']=='user-selected-same-system' and a['asciiPairing']['family']=='Arial'
print('Native Latin: 9 approved previews; all original Han pixels and identities preserved.')
