"""Acquisition UI/data contract checks; not real-browser visual acceptance."""
from pathlib import Path
from html.parser import HTMLParser
import json,re,subprocess,hashlib
R=Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/catalog.json').read_text())
ACTIONS={'font','trial','contact','method','reference','source','license'}
class Buttons(HTMLParser):
 def __init__(self):super().__init__();self.buttons=[];self.current=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and 'acquisition-button' in a.get('class','').split():self.current=[a,''];self.buttons.append(self.current)
 def handle_endtag(self,tag):
  if tag=='a':self.current=None
 def handle_data(self,data):
  if self.current is not None:self.current[1]+=data
# Exercise the actual popup acquisition block with a minimal synthetic DOM.
# This checks output parity only, not layout or browser interaction.
dynamic=json.loads(subprocess.check_output(['node','-e',r"""
const fs=require('fs'),app=require('./app.js'),source=fs.readFileSync('app.js','utf8');
const block=source.slice(source.indexOf('    if (row.acquisitionGuide) {'),source.indexOf("    addDetail(list, '样张类型'"));
class Node {constructor(tag,cls,text){this.tag=tag;this.className=cls||'';this.textContent=text||'';this.children=[];this.dataset={};}append(...nodes){this.children.push(...nodes)}get childElementCount(){return this.children.length}}
const render=new Function('row','create','asArray','safeSourceUrl','icon','addDetail','list',block);
const result={};for(const row of require('./data/catalog.json')){let saved;render(row,(...a)=>new Node(...a),v=>Array.isArray(v)?v:[],app.safeSourceUrl,()=>new Node('svg'),(list,title,node)=>saved={title,node},null);result[row.id]=saved;}process.stdout.write(JSON.stringify(result));
"""],cwd=R,text=True))
for row in rows:
 g=row['acquisitionGuide'];assert g['type'] in ACTIONS and g['title']=='获取方式',row['id']
 page=(R/'fonts'/f"{row['id']}.html").read_text();parser=Buttons();parser.feed(page)
 assert len(parser.buttons)==len(g['links']),row['id']
 popup=dynamic[row['id']];assert popup['title']=='获取方式'
 nodes=popup['node']['children'];assert nodes[0]['className']=='acquisition-notice' and nodes[0]['textContent']==g['notice']
 popup_buttons=nodes[-1]['children'] if nodes[-1]['className']=='acquisition-actions' else []
 assert len(popup_buttons)==len(parser.buttons)
 for button,(attrs,text) in zip(popup_buttons,parser.buttons):
  assert button['className']==attrs['class'] and button['textContent']==text and button['href']==attrs['href']
  assert button['dataset']['action']==attrs['data-action'] and button['target']==attrs['target'] and button['rel']==attrs['rel']
  assert button['children'][0]['tag']=='svg'
 assert 'class="acquisition-notice"' in page and '<dt>获取方式</dt><dd><div class="acquisition-guide">' in page
 for index,((attrs,text),link) in enumerate(zip(parser.buttons,g['links'])):
  assert link['action'] in ACTIONS and text==link['label'] and attrs['href']==link['url']
  assert attrs['data-action']==link['action'] and attrs['target']=='_blank' and attrs['rel']=='noopener noreferrer'
  assert ('acquisition-button-secondary' in attrs['class'])==(link['action'] in {'source','reference'} or index>0)
  assert text!='查看获取线索'
 if row['sourceUrl']:assert row['sourceUrl'].replace('&','&amp;') in page
 assert 'class="license-note"' in page
byid={r['id']:r for r in rows}
for id,kind in {'boutique9':'font','dinkie9':'trial','dinkie7':'trial','psa_c_screen_12':'contact','founder_pixel12':'license','dec_kaiti_gb2312_34':'method','chinasea_reference':'reference','hanyi-pixel9':'source','hanyi-pixel13':'source','lanapixel_11px':'source'}.items():assert byid[id]['acquisitionGuide']['type']==kind,(id,kind)
assert byid['relmon_ms6459']['acquisitionGuide']['links'][0]['action']=='reference'
assert byid['panasonic-mn1871681']['acquisitionGuide']['type']=='reference'
js=(R/'app.js').read_text();section=js[js.index('    if (row.acquisitionGuide) {'):js.index("    addDetail(list, '样张类型'")]
assert 'license-note' not in section and 'acquisition-notice' in section
assert "link.append(icon('external'))" in section and "link.dataset.action = action" in section
assert "addDetail(list, '获取方式', guide)" in section
css=(R/'styles.css').read_text()
assert '.acquisition-actions .acquisition-button:focus-visible' in css and '.acquisition-actions .acquisition-button:hover' in css
assert 'flex-wrap:wrap' in re.search(r'\.acquisition-actions\{([^}]+)',css).group(1)
assert 'min-height:38px' in re.search(r'\.acquisition-actions \.acquisition-button\{([^}]+)',css).group(1)
assert '.license-note{border-top:1px solid var(--line);margin-top:24px;padding:18px 0 0;font-size:11px;line-height:1.8;color:#858d95}' in css
print('Acquisition UI: all 199 retained typed guides and static buttons agree; source links preserved; honest action samples; separate note styles; focus/hover/wrapping CSS verified (not browser-rendered).')
