"""Mobile header contracts; does not claim browser layout/visual acceptance."""
from pathlib import Path
import json, subprocess
R=Path(__file__).resolve().parents[1]
html=(R/'index.html').read_text()
js=(R/'app.js').read_text()
css=(R/'styles.css').read_text()
assert '收集、展示与研究中文点阵字形，记录像素背后的来源。' not in html
assert '默认按字框高度；标明设计字高或有效字面的条目按其注明字高。' not in js
assert 'class="catalog-intro"' not in html
assert "create('p', 'filter-basis-note'" not in js
mobile=css.split('/* Compact, deliberate mobile header and two-row catalog controls. */',1)[1]
for rule in [
 'grid-template-columns:minmax(0,1fr) minmax(0,1fr)',
 '.toolbar #family-control{grid-column:2;grid-row:1}',
 '.toolbar #result-count{grid-column:1;grid-row:2}',
 '.toolbar .sort-control{grid-column:2;grid-row:2;margin-left:0;min-width:0}',
 '.toolbar .active-filters{grid-column:1/-1;grid-row:3}',
 '.header-actions{width:100%;margin-left:0}',
 'width:100%;max-width:100%;min-width:0;min-height:38px',
]: assert rule in mobile, rule
assert '[hidden]{display:none!important}' in css
# Execute the actual visibility assignments, not a separately rewritten state model.
states=json.loads(subprocess.check_output(['node','-e',r"""
const fs=require('fs'),s=fs.readFileSync('app.js','utf8');
const a=s.slice(s.indexOf("    $('favorites-back').hidden"),s.indexOf("    $('empty').querySelector('p').textContent"));
const b=s.split('\n').find(line=>line.includes("$('favorites-clear').hidden ="));
const toggle=new Function('$','favoritesView','favoriteIds',a+'\n'+b);
const out=[];
for(const view of [false,true]) for(const count of [0,1,20]){
  const nodes={}; const $=id=>nodes[id]||(nodes[id]={});toggle($,view,Array(count).fill('font'));
  out.push({view,count,nodes});
}
process.stdout.write(JSON.stringify(out));
"""],cwd=R,text=True))
for state in states:
 n=state['nodes']
 for first,second in [('filters-open','favorites-back'),('family-control','favorites-clear')]:
  assert n[first]['hidden'] or n[second]['hidden'], (state,first,second)
 assert n['active-filters']['hidden']==state['view']
 assert n['favorites-back']['hidden']!=state['view']
 assert n['favorites-clear']['hidden']==(not state['view'] or not state['count'])
# Detail pages keep their native wordmark and plain back link; no catalog grid.
for path in (R/'fonts').glob('*.html'):
 page=path.read_text();header=page.split('<header',1)[1].split('</header>',1)[0]
 assert 'width="192" height="48"' in header
 assert 'class="back-link"' in header and 'class="toolbar"' not in header
print('Mobile header contracts passed: copy removed, explicit grid, full-row chips, mutually exclusive favorite controls, unchanged detail header structure. Browser QA not included.')
