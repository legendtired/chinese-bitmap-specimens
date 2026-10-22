/* Synthetic DOM/logic regression checks only, not a real-browser visual acceptance. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const api = require('../app.js');
const reference = {id:'reference',name:'A 官方资料',family:'资料',sampleKind:'reference',referenceType:'官方试字截图',referenceNote:'保留来源截图；原生字符框尚未核定。',width:null,height:null,cellWidth:null,cellHeight:null,specimen:'assets/specimens/reference.png',specimenWidth:900,specimenHeight:420,text:null,missing:[],scripts:['简体'],styles:['黑体'],uses:['历史研究'],sourceUrl:'https://example.com/source'};
const native = {id:'native',name:'B 原生字样',family:'原生',sampleKind:'standard',width:12,height:12,specimen:'assets/specimens/native.png',specimenWidth:120,specimenHeight:30,text:'实际字样',asciiOrigin:'fullwidth-native',asciiText:'ＡＢ１２',missing:[],scripts:['简体'],styles:['宋体'],uses:['终端'],sourceUrl:'https://example.com/native'};
const tall = {...native,id:'tall',name:'C 大字号',height:24,width:24,sampleKind:'osd',sampleLabel:'来源限定设备菜单',asciiOrigin:'absent',asciiText:''};
const rows = [reference,native,tall];
const variable = {...native,id:'variable14',name:'D Pixels Han 14',variableGrid:true,designEmGrid:14,width:null,height:null,cellWidth:null,cellHeight:null,specimenWidth:137,specimenHeight:32,notes:'canvasBounds: 0,0,137,32；glyphAdvances: 7,9,14。'};
const variableSmall = {...variable,id:'variable9',name:'E Pixels Han 9',designEmGrid:9,specimenWidth:99,specimenHeight:25};
const mixedRows=[...rows,variable,variableSmall];
const ids = rows => rows.map(row=>row.id);
assert.equal(api.dimensions(reference),'未核定');
assert.equal(api.dimensions(native),'12×12');
assert.equal(api.cellDimensions(reference),null);
assert.equal(api.cellDimensions({...reference,cellWidth:12}),null);
assert.equal(api.heightValue(reference),'unknown');
assert.equal(api.heightLabel('unknown'),'未核定');
assert.equal(api.missingNotice({...reference,hanMissing:['字']}),'');
assert.deepEqual(ids(api.filterCatalog(rows,{height:['unknown']})),['reference']);
assert.deepEqual(ids(api.filterCatalog(rows,{height:['unknown'],styles:['宋体']})),[]);
assert.deepEqual(ids(api.filterCatalog(rows,{height:['unknown'],styles:['宋体','黑体']})),['reference']);
assert.deepEqual(ids(api.filterCatalog(rows,{height:['unknown','12']})),['reference'],'Height remains single-select even with multiple programmatic values');
assert.deepEqual(ids(api.filterCatalog(rows,{},'','height')),['native','tall','reference']);
assert.deepEqual(ids(api.filterCatalog(rows,{},'','height-desc')),['tall','native','reference']);
assert.deepEqual(ids(api.filterCatalog(rows,{},'','recommended')),['native','tall','reference']);
assert.deepEqual(ids(api.filterCatalog(rows,{},'','name')),['reference','native','tall']);
assert.deepEqual(ids(api.filterCatalog([reference,{...reference,id:'missing',height:undefined},native],{},'','height-desc')),['native','missing','reference']);
assert.deepEqual(ids(api.visibleCatalog(rows,{height:['12']},'','height-desc',true,['reference'])),['reference']);
assert.deepEqual(api.addComparison(['native'],'reference',new Set(ids(rows))),{ids:['native','reference'],limitReached:false});
assert.equal(api.isVariableGrid(variable),true);assert.equal(api.isReference(variable),false);
assert.equal(api.isVariableGrid({...reference,variableGrid:true}),false,'A reference image cannot become native merely through a grid flag');
assert.equal(api.dimensions(variable),'不定字框 · em 14 格');
assert.equal(api.dimensions(variableSmall),'不定字框 · em 9 格');
assert.equal(api.dimensions({...variable,width:14,height:14}),'不定字框 · em 14 格');
assert.equal(api.cellDimensions(variable),null);
assert.equal(api.heightValue(variable),'variable');assert.equal(api.heightLabel('variable'),'不定字框');
assert.deepEqual(ids(api.filterCatalog(mixedRows,{height:['variable']})),['variable14','variable9']);
assert.deepEqual(ids(api.filterCatalog(mixedRows,{height:['unknown']})),['reference']);
for(const em of ['9','14'])assert.deepEqual(api.filterCatalog(mixedRows,{height:[em]}),[],'Design em must not become a fixed pixel height');
assert.deepEqual(ids(api.filterCatalog(mixedRows,{},'','height')),['native','tall','variable14','variable9','reference']);
assert.deepEqual(ids(api.filterCatalog(mixedRows,{},'','height-desc')),['tall','native','variable14','variable9','reference']);

class Element {
  constructor(tag='div') { this.tagName=tag.toLowerCase();this.children=[];this.attributes={};this.dataset={};this.listeners={};this.style={};this._className='';this._text='';this.scrollLeft=0;this.scrollTop=0;this.hidden=false;this.classList={add:(name)=>this.classList.toggle(name,true),toggle:(name,on)=>{const list=new Set(this.className.split(/\s+/).filter(Boolean));const next=on===undefined?!list.has(name):on;next?list.add(name):list.delete(name);this.className=[...list].join(' ');return next;},contains:(name)=>this.className.split(/\s+/).includes(name)}; }
  set className(value){this._className=value;} get className(){return this._className;}
  set textContent(value){this.children=[];this._text=String(value);} get textContent(){return this._text+this.children.map(child=>child.textContent).join('');}
  set value(value){this._value=String(value);} get value(){return this._value??(this.tagName==='select'?(this.children.find(child=>child.selected)||this.children[0])?.value:'')??'';}
  setAttribute(key,value){this.attributes[key]=String(value);if(key==='class')this.className=value;if(key==='id')this.id=value;}
  getAttribute(key){if(key==='class')return this.className;if(key==='id')return this.id;if(key.startsWith('data-'))return this.dataset[key.slice(5).replace(/-([a-z])/g,(_,letter)=>letter.toUpperCase())];return this.attributes[key]??null;}
  append(...children){for(const child of children){if(child.tagName==='#fragment')this.append(...child.children);else{this.children.push(child);child.parent=this;}}}
  replaceChildren(...children){this._text='';this.children=[];this.append(...children);}
  addEventListener(type,handler){(this.listeners[type]??=[]).push(handler);}
  emit(type,values={}){const event={type,target:this,button:0,detail:1,clientX:0,clientY:0,preventDefault(){this.defaultPrevented=true;},...values};for(const handler of this.listeners[type]||[])handler(event);return event;}
  focus(){document.activeElement=this;} showModal(){this.open=true;} close(){this.open=false;this.emit('close');}
  get isConnected(){return !!this.parent;}
  matches(selector){
    const negative=selector.match(/:not\(([^)]+)\)/);if(negative){if(this.matches(negative[1]))return false;selector=selector.replace(negative[0],'');}
    if(selector.endsWith(':checked')){if(!this.checked)return false;selector=selector.replace(':checked','');}
    const attr=selector.match(/\[([^=\]]+)(?:=["']?([^\]"']+)["']?)?\]/);if(attr){const value=attr[1]==='open'?(this.open?'':null):this.getAttribute(attr[1]);if(value==null||(attr[2]!==undefined&&value!==attr[2]))return false;selector=selector.replace(attr[0],'');}
    const id=selector.match(/#([\w-]+)/);if(id&&this.id!==id[1])return false;
    for(const match of selector.matchAll(/\.([\w-]+)/g))if(!this.classList.contains(match[1]))return false;
    const tag=selector.match(/^[a-z]+/);return !tag||this.tagName===tag[0];
  }
  querySelectorAll(selector){const parts=selector.trim().split(/\s+/);const result=[];const visit=node=>{for(const child of node.children){if(child.matches(parts.at(-1))){let parent=child.parent,index=parts.length-2;while(parent&&index>=0){if(parent.matches(parts[index]))index--;parent=parent.parent;}if(index<0)result.push(child);}visit(child);}};visit(this);return result;}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  closest(selector){return this.matches(selector)?this:this.parent?.closest(selector)||null;}
}
const document = new Element('document');
document.createElement=tag=>new Element(tag);
document.createElementNS=(_,tag)=>new Element(tag);
document.createDocumentFragment=()=>new Element('#fragment');
document.body=new Element('body');document.append(document.body);
document.getElementById=id=>document.querySelector('#'+id);
const appSource=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8');
for(const id of new Set([...appSource.matchAll(/\$\('([^']+)'\)/g)].map(match=>match[1]))){const tag=id.endsWith('-dialog')?'dialog':['family','sort','compare-zoom'].includes(id)?'select':'div';const element=new Element(tag);element.id=id;document.body.append(element);}
const $=id=>document.getElementById(id);
$('family').value='';$('sort').value='recommended';$('compare-zoom').value='3';$('empty').append(new Element('p'));
for(const name of ['layout','site-header']){const node=new Element();node.className=name;document.body.append(node);}
const toolbar=new Element();toolbar.className='compare-toolbar';toolbar.append(new Element('label'),new Element('span'));document.body.append(toolbar);
const storage={value:null,getItem(){return this.value;},setItem(_,value){this.value=value;}};
vm.runInNewContext(appSource,{document,window:{FONT_CATALOG:mixedRows,localStorage:storage,matchMedia:()=>({addEventListener(){}})},Node:Element,URL});
const findCard=id=>$('catalog').children.find(element=>element.dataset.rowId===id);
let card=findCard('reference');
assert.equal(card.querySelectorAll('img').length,1);
assert.equal(card.querySelectorAll('select').length,0);
assert(card.textContent.includes('原始资料图 · 官方试字截图'));
assert(card.textContent.includes('字高未核定'));
assert(!/原尺寸|[13]×|null/.test(card.textContent));
let image=card.querySelector('img');
assert.equal(image.width,900);assert.equal(image.height,420);
image.setScale(4);assert.equal(image.width,900,'Reference dimensions never follow pixel zoom');
assert.equal(image.getAttribute('role'),'button');assert.equal(image.tabIndex,0);
image.emit('click');assert($('detail-dialog').open);
assert($('detail-content').textContent.includes(api.referenceCoverage));
assert($('detail-content').textContent.includes(reference.referenceNote));
assert($('detail-content').textContent.includes(reference.referenceType));
assert(!/本次样本文字未发现缺字|null/.test($('detail-content').textContent));
assert(!$('detail-content').querySelectorAll('dt').some(term=>term.textContent==='字符框'));
$('detail-dialog').close();
image.emit('pointerdown');image.emit('pointermove',{clientX:10});image.emit('click');assert(!$('detail-dialog').open,'Dragging the reference image must not open details');
image.emit('pointerdown');image.parent.scrollLeft=10;image.parent.emit('scroll');image.emit('click');assert(!$('detail-dialog').open,'Scrolling must not open details');
for(const key of ['Enter',' ']){image.emit('keydown',{key});assert($('detail-dialog').open);$('detail-dialog').close();}
const referenceLink=card.querySelector('.detail-button');
assert.equal(referenceLink.href,'fonts/reference.html');
assert(!referenceLink.emit('click',{ctrlKey:true}).defaultPrevented,'Modified click keeps standalone page navigation');
card.querySelector('.favorite-toggle').emit('click');
assert.equal(JSON.parse(storage.value)[0],'reference');
assert.equal(card.querySelector('.favorite-toggle').getAttribute('aria-pressed'),'true');
const heightOptions=$('filter-groups').children[0].querySelectorAll('input');
assert.deepEqual(heightOptions.map(option=>option.value),['','12','24','variable','unknown']);
assert(heightOptions.every(option=>option.type==='radio'));
heightOptions.forEach(option=>{option.checked=option.value==='unknown';});heightOptions.at(-1).emit('change');
assert.equal($('catalog').children.length,1);assert.equal($('catalog').children[0].dataset.rowId,'reference');
assert($('active-filters').textContent.includes('字高 未核定'));assert(!$('active-filters').textContent.includes('unknown'));
$('reset-filters').emit('click');
card=findCard('reference');card.querySelector('.compare-toggle').emit('click');findCard('native').querySelector('.compare-toggle').emit('click');$('compare-open').emit('click');
assert.equal($('compare-content').children.length,2);assert(!$('compare-warning').hidden);assert($('compare-warning').textContent.includes(api.referenceWarning));
assert(!toolbar.hidden);assert.equal(toolbar.querySelector('label').textContent,'原生字样放大');
const refImage=$('compare-content').querySelector('.reference-image');
const nativeImage=$('compare-content').querySelector('.specimen-image:not(.reference-image)');
assert.equal(refImage.width,900);assert.equal(nativeImage.width,360);
$('compare-zoom').value='4';$('compare-zoom').emit('change');assert.equal(refImage.width,900);assert.equal(nativeImage.width,480);
const nativeComparison=$('compare-content').children.find(element=>!element.classList.contains('reference-specimen'));
nativeComparison.querySelector('button').emit('click');assert(toolbar.hidden,'Reference-only comparison has no pixel multiplier');
assert(!$('compare-warning').hidden);assert.equal($('compare-content').querySelectorAll('img').length,1);
const nativeCard=findCard('native');assert.equal(nativeCard.querySelectorAll('img').length,2);assert.equal(nativeCard.querySelectorAll('select').length,1);assert(nativeCard.textContent.includes('原尺寸 · 1×'));
$('compare-dialog').close();nativeCard.querySelector('img').emit('click');
assert($('detail-content').textContent.includes('全角英数样文（非ASCII）'));assert($('detail-content').textContent.includes('ＡＢ１２'));
$('detail-dialog').close();findCard('tall').querySelector('img').emit('click');
assert($('detail-content').textContent.includes('来源限定设备菜单'));assert(!$('detail-content').textContent.includes('全角英数样文（非ASCII）'));
$('detail-dialog').close();findCard('tall').querySelector('.compare-toggle').emit('click');$('compare-open').emit('click');
assert($('compare-content').textContent.includes('来源限定设备菜单'));assert($('compare-warning').textContent.includes('包含来源限定设备样张'));
$('compare-dialog').close();$('compare-clear').emit('click');
for(const row of [variable,variableSmall]){
 const gridCard=findCard(row.id),images=gridCard.querySelectorAll('img');
 assert(gridCard.textContent.includes(`不定字框 · em ${row.designEmGrid} 格`));
 assert(!/未核定|原始资料图|null|14×14|9×9|0×0/.test(gridCard.textContent));
 assert.equal(images.length,2);assert.equal(gridCard.querySelectorAll('select').length,1);
 assert.equal(images[0].width,row.specimenWidth*3);assert.equal(images[0].height,row.specimenHeight*3);
 assert.equal(images[1].width,row.specimenWidth);assert.equal(images[1].height,row.specimenHeight);
 assert(images.every(image=>!image.classList.contains('reference-image')));
 images[0].emit('keydown',{key:'Enter'});
 assert($('detail-content').textContent.includes(`不定字框 · em ${row.designEmGrid} 格`));
 assert($('detail-content').textContent.includes(api.variableGridNote));
 assert($('detail-content').textContent.includes(row.notes));
 assert(!$('detail-content').textContent.includes(api.referenceCoverage));
 assert(!$('detail-content').querySelectorAll('dt').some(term=>term.textContent==='字符框'));
 $('detail-dialog').close();
}
heightOptions.forEach(option=>{option.checked=option.value==='variable';});heightOptions.find(option=>option.value==='variable').emit('change');
assert.deepEqual($('catalog').children.map(card=>card.dataset.rowId),['variable14','variable9']);
assert($('active-filters').textContent.includes('字高 不定字框'));assert(!$('active-filters').textContent.includes('variable'));
$('reset-filters').emit('click');
findCard('variable14').querySelector('.favorite-toggle').emit('click');assert(JSON.parse(storage.value).includes('variable14'));
for(const id of ['variable14','variable9'])findCard(id).querySelector('.compare-toggle').emit('click');
$('compare-open').emit('click');
assert(!toolbar.hidden);assert($('compare-warning').textContent.includes(api.variableGridWarning));
assert(!$('compare-warning').textContent.includes(api.referenceWarning));
assert.equal($('compare-content').querySelectorAll('img').length,2);
assert.equal($('compare-content').querySelectorAll('.reference-image').length,0);
const gridImages=$('compare-content').querySelectorAll('img');
$('compare-zoom').value='4';$('compare-zoom').emit('change');
assert.equal(gridImages[0].width,variable.specimenWidth*4);assert.equal(gridImages[1].width,variableSmall.specimenWidth*4);
$('compare-dialog').close();findCard('reference').querySelector('.compare-toggle').emit('click');$('compare-open').emit('click');
assert($('compare-warning').textContent.includes(api.variableGridWarning));assert($('compare-warning').textContent.includes(api.referenceWarning));
assert.equal($('compare-content').querySelector('.reference-image').width,reference.specimenWidth);
console.log('Reference / variable-grid tests passed: distinct unknown/flexible-height filters, honest em labels, native pixel sizes/zoom, details, keyboard/drag, favorites and mixed comparisons (synthetic DOM, not browser acceptance).');
