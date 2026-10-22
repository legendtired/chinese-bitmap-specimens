const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createFavoriteStore,bindSpecimenDetails}=require('../app.js');
const rows=require('../data/catalog.json'),curation=require('../data/curation.json');
const ids=new Set(rows.map(r=>r.id));
assert.equal(rows.length,require('../data/release-psa.json').totalRows-require('../data/curation.json').postPsaRemovedIds.length);assert.equal(curation.removedIds.length,29);
for(const id of [...curation.removedIds,...Object.keys(curation.merged)])assert(!ids.has(id));
assert(ids.has('taipeil24'),'Do not confuse separate Taipei l24 entry');
for(const [old,id] of Object.entries(curation.merged))assert(rows.find(r=>r.id===id).relatedSources.length);
const store=createFavoriteStore(()=>({getItem:()=>JSON.stringify([...Object.keys(curation.merged),'removed']),setItem(){}}),ids,curation.merged);
assert.deepEqual(store.ids,Object.values(curation.merged));
function el(){const handlers={};return{handlers,scrollLeft:0,scrollTop:0,classList:{add(){}},setAttribute(){},focus(){},addEventListener(n,f){handlers[n]=f;}};}
const image=el(),scroll=el();let opens=0;bindSpecimenDetails(image,scroll,'测试',()=>opens++);
const ev=(extras={})=>({preventDefault(){},detail:1,clientX:0,clientY:0,...extras});
image.handlers.pointerdown(ev());image.handlers.click(ev());assert.equal(opens,1);
image.handlers.pointerdown(ev());image.handlers.pointermove(ev({clientX:20}));image.handlers.click(ev());assert.equal(opens,1);
image.handlers.pointerdown(ev());scroll.scrollLeft=20;scroll.handlers.scroll();image.handlers.click(ev());assert.equal(opens,1);
image.handlers.pointerdown(ev());image.handlers.pointercancel();image.handlers.click(ev());assert.equal(opens,1);
image.handlers.keydown(ev({key:'Enter'}));image.handlers.keydown(ev({key:' '}));assert.equal(opens,3);
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
assert(html.includes('id="detail-content" class="dialog-body"'));assert(html.includes('aria-label="字形对比内容"'));assert(html.includes('aria-label="关于本站内容"'));
const css=fs.readFileSync(path.join(__dirname,'../styles.css'),'utf8');assert(css.includes('dialog[open]{display:flex;flex-direction:column}'));assert(css.includes('.dialog-body{flex:1 1 auto;min-height:0;min-width:0;overflow:auto;'));
console.log('Curation tests passed: 29 exclusions, 3 merges/provenance/favorites, pointer/keyboard/scroll suppression, fixed-header modal structure. Not a real-browser visual test.');

const stale=createFavoriteStore(()=>({getItem:()=>JSON.stringify(['monotype_bitmap_hk','pixels_han_main']),setItem(){}}),ids,curation.merged);assert.deepEqual(stale.ids,['pixels_han_main']);assert(!ids.has('monotype_bitmap_hk'));

const removedHanyi=createFavoriteStore(()=>({getItem:()=>JSON.stringify(['hanyi-pixel-power','hanyi-pixel-invasion','hanyi-pixel13']),setItem(){}}),ids,curation.merged);assert.deepEqual(removedHanyi.ids,['hanyi-pixel13']);
