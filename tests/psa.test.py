from acquisition_baseline import before_acquisition
from pathlib import Path
import json,hashlib,struct,importlib.util
try:
 from PIL import Image
except ImportError:
 Image=None
R=Path(__file__).resolve().parents[1];rows=json.loads((R/'data/catalog.json').read_text());byid={r['id']:r for r in rows};manifest=json.loads((R/'data/release-psa.json').read_text())
removed=set(json.loads((R/'data/curation.json').read_text()).get('postPsaRemovedIds',[]))
assert removed=={'taipeib20'}
removed |= set(json.loads((R/'data/curation.json').read_text())['postEfontRemovedIds'])
assert len(rows)==199 and len(manifest['baseIds'])==200
for id,sha in manifest['baseRowChecksums'].items():
 if id in removed:continue
 assert hashlib.sha256(json.dumps(before_acquisition(byid[id]),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==sha,id
assert set(byid)==(set(manifest['baseIds'])|set(manifest['addedIds']))-removed
for id,ink,w,h in [('psa_c_screen_12',12,14,14),('psa_c_screen_14',14,16,17)]:
 r=byid[id];assert r['priority']==(8 if ink==12 else 0) and r['designHeight']==ink and r['heightBasis']=='han-ink-grid'
 assert (r['width'],r['height'],r['cellWidth'],r['cellHeight'])==(w,h,w,h)
 assert r['sourceUrl'] is None and r['sourceType']=='physical-extraction'
 assert r['nativeEvidence']['unicodeEntries']==28684 and '不是全汉字' in r['coverage']
 if Image is not None:
  im=Image.open(R/r['specimen']).convert('RGBA');a=im.getchannel('A');assert set(a.tobytes())=={0,255}
  assert a.crop((0,0,1,h)).getbbox() is None and a.crop((w-1,0,w,h)).getbbox() is None
  assert a.crop((0,ink,w,h)).getbbox() is None and a.crop((1,0,w-1,ink)).getbbox()
 page=(R/'fonts'/f'{id}.html').read_text();assert 'https://github.com/legendtired/chinese-bitmap-specimens/issues' in page and '联系仓库作者' in page and 'href="None"' not in page and 'href="null"' not in page
if Image is None:
 print('PSA metadata checks passed; optional pixel/decoder verification skipped because Pillow is not installed.');raise SystemExit(0)
spec=importlib.util.spec_from_file_location('psa_renderer',R/'scripts/render_psa_specimens.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
data=bytearray(4194304);cm,wm,om,bm,h=module.TABLES[0];n=(wm-cm)//2
struct.pack_into('<'+'H'*n,data,cm,*range(n));data[wm:wm+n]=bytes([14])*n;struct.pack_into('<'+'I'*n,data,om,*[i*h*2 for i in range(n)])
p=bm+ord('A')*h*2
for y in range(12):struct.pack_into('<H',data,p+y*2,(1<<1)|(1<<12))
im=module.render(data,0,'A');assert im.size==(14,14) and im.getpixel((1,0))[3]==255 and im.getpixel((0,0))[3]==0 and im.getpixel((1,12))[3]==0
try:module.render(data,0,'\uffff')
except ValueError:pass
else:raise AssertionError('Missing source glyph must not use fallback')
print('PSA:199 retained prior rows unchanged except acquisition guidance; Taipei b20 explicitly removed; two original padded specimens; truthful no-source link/contact; synthetic LSB decoder and missing-glyph rejection passed.')
