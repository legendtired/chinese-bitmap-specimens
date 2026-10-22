const assert = require('node:assert/strict');
const {filterCatalog,missingNotice,formatData,safeSourceUrl} = require('../app.js');
const rows = [
{name:'A', family:'甲', width:12,height:12,scripts:['简体中文'],styles:['黑体'],uses:['终端']},
{name:'B', family:'乙', width:16,height:16,scripts:['繁体中文'],styles:['宋体'],uses:['终端']},
{name:'C', family:'乙', width:8,height:12,scripts:['繁体中文'],styles:['黑体'],uses:['游戏']}
];
assert.equal(filterCatalog(rows,{}).length,3);
assert.equal(filterCatalog(rows,{scripts:['简体中文','繁体中文']}).length,3);
assert.deepEqual(filterCatalog(rows,{scripts:['繁体中文'],styles:['黑体']}).map(x=>x.name),['C']);
assert.deepEqual(filterCatalog(rows,{height:['12']}).map(x=>x.name),['A','C']);
assert.equal(filterCatalog(rows,{uses:['没有的用途']}).length,0);
assert.deepEqual(filterCatalog(rows,{},'乙').map(x=>x.name),['C','B']);
assert.deepEqual(filterCatalog(rows,{},'','height-desc').map(x=>x.name),['B','A','C']);
assert.deepEqual(filterCatalog(rows,{},'','name').map(x=>x.name),['A','B','C']);
assert.deepEqual(filterCatalog(rows,{height:['12'],scripts:['繁体中文']}).map(x=>x.name),['C']);
assert.deepEqual(filterCatalog(rows,{height:['16']}).map(x=>x.name),['B']);
assert.equal(filterCatalog(rows,{height:[]}).length,3);
assert.equal(filterCatalog(rows,{height:['99']}).length,0);
const extremeRows = [{...rows[0],name:'tiny',width:6,height:6},{...rows[0],name:'large',width:48,height:48}];
assert.deepEqual(filterCatalog(extremeRows,{height:['6']}).map(x=>x.name),['tiny']);
assert.deepEqual(filterCatalog(extremeRows,{height:['48']}).map(x=>x.name),['large']);
assert.equal(rows[0].name,'A');
assert.equal(missingNotice({missing:[]}), '');
assert.equal(missingNotice({hanMissing:['视'],asciiMissing:['A'],missing:['视','A']}), '中文缺字：视；拉丁字符／符号缺字：A。对应位置留空，不借用其他字体补齐。');
assert.equal(missingNotice({missing:['天']}), '缺字：天。对应位置留空，不借用其他字体补齐。');
assert.equal(formatData({nested:{pixels:[6,8]}}),'nested：pixels：6、8');
assert.equal(safeSourceUrl('javascript:alert(1)'),null);
assert.equal(safeSourceUrl('data:text/html,bad'),null);
assert.equal(safeSourceUrl('/relative'),null);
assert.equal(safeSourceUrl('https://littlelimit.net/k6x8.htm'),'https://littlelimit.net/k6x8.htm');
assert.equal(missingNotice({asciiMissing:['A'],missing:['A'],omittedEmptyLines:['ascii']}), '拉丁字符／符号缺字：A。拉丁字符行全部缺失，样图省略该空白行；不借用其他字体补齐。');
console.log('Filter tests passed: single height across different widths, OR within other groups, AND across groups, family, empty, sort and no mutation.');
