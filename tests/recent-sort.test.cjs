/* Independent read-only regression review. Run against the final tree with:
 * FONT_CATALOG_ROOT=/path/to/tree node --test recent-sort.test.cjs
 * These checks do not modify the target checkout and are not visual acceptance.
 */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const root = process.env.FONT_CATALOG_ROOT || path.resolve(__dirname, '..');
const read = relative => fs.readFileSync(path.join(root, relative), 'utf8');
const json = relative => JSON.parse(read(relative));
const api = require(path.join(root, 'app.js'));
const rows = json('data/catalog.json').filter(r => !r.id.startsWith('psion618c_'));
const release = json('data/release-20261105-batch.json');
const baselinePath = fs.existsSync(path.join(__dirname, 'previous-sort-baseline.json'))
  ? path.join(__dirname, 'previous-sort-baseline.json')
  : path.join(__dirname, 'fixtures/recent-sort-baseline.json');
const originalPrevious = JSON.parse(fs.readFileSync(baselinePath, 'utf8'));
const withdrawn = new Set(json('data/withdrawal-solaris-gb2312.json').removedIds);
const previous = Object.fromEntries(Object.entries(originalPrevious).map(([mode, list]) => [mode, list.filter(id => !withdrawn.has(id))]));
const ids = values => values.map(row => row.id);
const byName = (a, b) => a.name.localeCompare(b.name, 'zh-CN') || a.id.localeCompare(b.id);
// sourceIndex is a typed nonnegative JSON number. Numeric-looking strings are
// deliberately unverified, rather than silently coercing them into chronology.
const validNumber = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const bySource = (a, b) => {
  const av = validNumber(a.sourceIndex), bv = validNumber(b.sourceIndex);
  return Number(bv) - Number(av) || (av ? Number(b.sourceIndex) - Number(a.sourceIndex) : 0) || byName(a, b);
};
const recent = (values, selections = {}, family = '') => api.filterCatalog(values, selections, family, 'recent');
const pcId = 'wqx_pc505_14x15';
const priorRows = rows.filter(r => r.id !== pcId);
const newIds = new Set(release.addedIds.filter(id => !withdrawn.has(id)));
const baseIds = new Set(release.baseIds);
const row = (id, sourceIndex, extra = {}) => ({id, sourceIndex, name: id, height: 12, family: 'fixture', scripts: ['简体'], styles: ['宋体'], uses: ['研究'], ...extra});
const fixture = [
  row('missing', undefined),
  row('null', null),
  row('nan', NaN),
  row('empty', ''),
  row('whitespace', '  '),
  row('nonnumeric', 'not-a-number'),
  row('infinity', Infinity),
  row('string-infinity', 'Infinity'),
  row('negative', -10),
  row('boolean', true),
  row('zero-number', 0),
  row('ten-number', 10),
  row('ten-string', '10'),
  row('nine-number', 9),
  row('two-string', '2'),
  row('three-space-string', ' 3 ')
];

test('PC505 is newest, followed by the prior 10 retained collected items and entire 208-item baseline', () => {
  assert.equal(rows.length, 219);
  assert.equal(priorRows.length, 218);
  assert.equal(newIds.size, 10);
  assert.equal(baseIds.size, 208);
  const sorted = recent(rows);
  assert.equal(sorted.length, rows.length);
  assert.equal(sorted[0].id, pcId);
  assert.equal(sorted[0].sourceIndex, 252);
  assert.deepEqual(new Set(ids(sorted.slice(1, 11))), newIds);
  assert.deepEqual(new Set(ids(sorted.slice(11))), baseIds);
  assert.deepEqual(new Set(ids(sorted)), new Set(ids(rows)));
});

test('FM Towns precedes older Sharp and batch order wins even if Sharp has a larger index', () => {
  const fm = rows.find(r => r.id === 'fmtowns_f20_20');
  const sharp = rows.find(r => r.id === 'sharp_x68000_16');
  assert.equal(fm.sourceIndex, 234);
  assert.equal(sharp.sourceIndex, 233);
  assert.deepEqual(ids(recent([sharp, fm])), [fm.id, sharp.id]);
  assert(ids(recent(rows)).indexOf(fm.id) < ids(recent(rows)).indexOf(sharp.id));
  assert.deepEqual(ids(recent([{...sharp, sourceIndex:239}, fm])), [fm.id, sharp.id]);
});

test('Prior retained 10-item batch order is numeric descending, independently of priority, height and original release year', () => {
  const added = rows.filter(r => newIds.has(r.id));
  assert.deepEqual(ids(recent(added)), ids([...added].sort(bySource)));
  const contradictory = added.map((r, i) => ({...r, priority: i * -100, height: 100 - i, releaseDate: `${2100-i}-01-01`, machineYear: 1800+i}));
  assert.deepEqual(ids(recent(contradictory)), ids([...added].sort(bySource)));
  assert.deepEqual(ids(recent(added)).slice(0, 3), ['sun_gbk_song_24', 'sun_gbk_song_20', 'sun_gbk_song_16']);
  assert.equal(ids(recent(added)).at(-1), 'fmtowns_f20_20');
});

test('History batches match their checked-in release manifests with no duplicate or unknown IDs', () => {
  const history = json('data/collection-history.json');
  history.batches = history.batches.filter(b => b.sourceManifest !== 'release-psion618c.json');
  assert(Array.isArray(history.batches) && history.batches.length > 0);
  const known = new Set(ids(rows)), assigned = new Set();
  for (const batch of history.batches) {
    assert.equal(typeof batch.sourceManifest, 'string');
    assert(Array.isArray(batch.ids));
    const file = batch.sourceManifest.startsWith('data/') ? batch.sourceManifest : `data/${batch.sourceManifest}`;
    const manifest = json(file);
    const declared = manifest.addedIds || (manifest.addedId ? [manifest.addedId] : []);
    assert(declared.length > 0, `${file} must state the batch additions`);
    assert.deepEqual(new Set(batch.ids), new Set(declared.filter(id => known.has(id))), `${file} must agree with current retained additions`);
    for (const id of batch.ids) {
      assert(known.has(id), `Unknown collection history ID: ${id}`);
      assert(!assigned.has(id), `Repeated collection history ID: ${id}`);
      assigned.add(id);
    }
  }
  const latest = history.batches.at(-1);
  assert.equal(path.basename(latest.sourceManifest), 'release-pc505-collection.json');
  assert.deepEqual(latest.ids, [pcId]);
  assert.equal(history.batches.length, 10);
  assert.deepEqual(new Set(history.batches.at(-2).ids), newIds);
});

test('Each recorded batch sorts ahead of older batches and unrecorded history', () => {
  const history = json('data/collection-history.json');
  history.batches = history.batches.filter(b => b.sourceManifest !== 'release-psion618c.json');
  const rank = new Map(history.batches.flatMap((batch, index) => batch.ids.map(id => [id, index + 1])));
  const expected = [...rows].sort((a, b) => (rank.get(b.id) || 0) - (rank.get(a.id) || 0) || bySource(a, b));
  assert.deepEqual(ids(recent(rows)), ids(expected));
  assert.deepEqual(ids(recent([...rows].reverse())), ids(expected), 'Input order must not alter deterministic recent order');
});

test('Missing, null, NaN, Infinity, negatives and string source numbers come after actual numbers', () => {
  const sorted = recent(fixture);
  assert.deepEqual(ids(sorted), ids([...fixture].sort(bySource)));
  assert.deepEqual(ids(sorted.slice(0, 3)), ['ten-number', 'nine-number', 'zero-number']);
  assert(sorted.slice(3).every(r => !validNumber(r.sourceIndex)));
  assert.deepEqual(ids(recent([...fixture].reverse())), ids(sorted));
});

test('Equal source numbers use name, then ID, as a deterministic tie break', () => {
  const tied = [row('z-id', 99, {name:'Alpha'}), row('name-b', 99, {name:'Beta'}), row('a-id', 99, {name:'Alpha'})];
  assert.deepEqual(ids(recent(tied)), ['a-id', 'z-id', 'name-b']);
  assert.deepEqual(ids(recent([...tied].reverse())), ['a-id', 'z-id', 'name-b']);
});

test('A known newer batch still wins when its source index is missing', () => {
  const newer = row('fmtowns_f20_20', null, {name:'Z New'});
  const older = row('sharp_x68000_16', 999999, {name:'A Old'});
  const unknown = row('unrecorded-fixture', 1000000, {name:'A Unknown'});
  assert.equal(recent([unknown, older, newer])[0].id, newer.id);
});

test('Recent ordering composes with all filters and family selection', () => {
  const sorted = recent(rows);
  for (const height of ['12', '14', '16', '24', 'unknown', 'variable']) {
    assert.deepEqual(ids(recent(rows, {height:[height]})), ids(sorted.filter(r => api.heightValue(r) === height)));
  }
  const selected = {height:['24'], scripts:['简体中文', '繁体中文'], styles:['宋体', '楷体']};
  // Existing name mode provides an independent filter-membership baseline.
  const membership = new Set(ids(api.filterCatalog(rows, selected, '', 'name')));
  assert.deepEqual(ids(recent(rows, selected)), ids(sorted.filter(r => membership.has(r.id))));
  const family = rows.find(r => newIds.has(r.id)).family;
  assert.deepEqual(ids(recent(rows, {}, family)), ids(sorted.filter(r => r.family === family)));
  assert.deepEqual(recent(rows, {height:['9999']}), []);
});

test('Favorites keep recent ordering and ignore the ordinary filter/family view', () => {
  const favorites = ['sharp_x68000_16', 'fmtowns_f20_20', 'founder_pixel12', 'sun_gb2312_song_20'];
  const expected = ids(recent(rows)).filter(id => favorites.includes(id));
  assert.deepEqual(ids(api.visibleCatalog(rows, {height:['9999']}, 'missing-family', 'recent', true, favorites)), expected);
  assert.equal(expected.indexOf('fmtowns_f20_20') < expected.indexOf('sharp_x68000_16'), true);
  assert.deepEqual(api.visibleCatalog(rows, {}, '', 'recent', true, []), []);
  assert.deepEqual(api.visibleCatalog(rows, {height:['9999']}, '', 'recent', false, favorites), []);
});

test('Empty input and one-item input are safe', () => {
  assert.deepEqual(recent([]), []);
  const one = row('single', undefined);
  assert.deepEqual(recent([one]), [one]);
});

test('Sorting mutates neither input array, rows, filters nor favorites', () => {
  const input = structuredClone([...rows, ...fixture]);
  const snapshot = structuredClone(input);
  const filters = {height:[], scripts:[], styles:[], uses:[]};
  const filtersBefore = structuredClone(filters);
  const favorites = ['sharp_x68000_16', 'fmtowns_f20_20'];
  Object.freeze(input);
  for (const r of input) Object.freeze(r);
  recent(input, filters);
  api.visibleCatalog(input, filters, '', 'recent', true, favorites);
  assert.deepEqual(input, snapshot);
  assert.deepEqual(filters, filtersBefore);
  assert.deepEqual(favorites, ['sharp_x68000_16', 'fmtowns_f20_20']);
});

test('All previous sort modes match the retained rows of the immutable pre-change 221-row baselines', () => {
  for (const mode of ['recommended', 'height', 'height-desc', 'name']) {
    assert.deepEqual(ids(api.filterCatalog(rows, {}, '', mode)).filter(id => id !== pcId), previous[mode], `${mode} ordering changed`);
  }
  assert.deepEqual(ids(api.filterCatalog(rows, {})).filter(id => id !== pcId), previous.recommended);
});

test('HTML offers explicit latest-collected order without replacing the recommended default', () => {
  const html = read('index.html');
  const select = html.match(/<select\b[^>]*\bid=["']sort["'][^>]*>([\s\S]*?)<\/select>/);
  assert(select, 'Sort control is present');
  assert.match(select[1], /<option\b[^>]*\bvalue=["']recent["'][^>]*>[^<]*收录[^<]*<\/option>/);
  assert.match(select[1], /<option\b[^>]*\bvalue=["']recommended["'][^>]*\bselected\b/);
  assert.doesNotMatch(select[1], /<option\b[^>]*\bvalue=["']recent["'][^>]*\bselected\b/);
  assert.match(select[0], /aria-describedby=["']sort-note["']/);
  const note = html.match(/<p\b[^>]*\bid=["']sort-note["'][^>]*>([\s\S]*?)<\/p>/);
  assert(note);
  assert.match(note[0], /\bhidden\b/);
  assert.match(note[1], /本站收录批次/);
  assert.match(note[1], /早期收录时间未核/);
  assert.match(note[1], /来源编号倒序/);
  assert.match(note[1], /缺失置后/);
});

test('Offline script order loads catalog and collection history before the app', () => {
  const html = read('index.html');
  const scripts = [...html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/g)].map(m => m[1]);
  assert.deepEqual(scripts, ['data/catalog.js', 'data/collection-history.js', 'app.js']);
  for (const script of scripts) assert(fs.existsSync(path.join(root, script)), `Missing offline script: ${script}`);
  assert(!/<script\b[^>]*\basync(?:\s|=|>)/.test(html), 'Dependent scripts must preserve their load order');
});

test('Browser global history path produces the same newest-first order as CommonJS', () => {
  const context = vm.createContext({window:{}, URL});
  vm.runInContext(read('data/catalog.js'), context, {filename:'data/catalog.js'});
  vm.runInContext(read('data/collection-history.js'), context, {filename:'data/collection-history.js'});
  assert.deepEqual(JSON.parse(JSON.stringify(context.window.FONT_COLLECTION_HISTORY)), json('data/collection-history.json'));
  // Expose pure functions immediately before the existing no-DOM return, without
  // injecting CommonJS; this independently exercises browser global data loading.
  const marker = "if (typeof document === 'undefined') return;";
  const app = read('app.js');
  assert(app.includes(marker), 'Expected no-DOM guard for the VM review');
  vm.runInContext(app.replace(marker, `globalThis.reviewApi = { filterCatalog, visibleCatalog }; ${marker}`), context, {filename:'app.js'});
  const actual = context.reviewApi.filterCatalog(context.window.FONT_CATALOG, {}, '', 'recent');
  assert.deepEqual(Array.from(actual, r => r.id), ids(recent(json('data/catalog.json'))));
  assert.deepEqual(Array.from(actual.slice(0,2), r => r.id), ['psion618c_11','psion618c_8']);
});

test('UI change events toggle the recency explanation and keep recent order across favorites and filter resets', () => {
  // Reuse only the repository's synthetic DOM adapter, not any of its assertions.
  // It exercises the actual app render/event bindings, without claiming browser QA.
  const source = read('tests/reference.test.cjs');
  const adapter = source.slice(source.indexOf('class Element {'), source.indexOf('const findCard='))
    .replace('FONT_CATALOG:mixedRows,', 'FONT_CATALOG:mixedRows,FONT_COLLECTION_HISTORY:history,');
  assert(adapter.includes('class Element {'));
  const context = vm.createContext({fs, path, vm, URL, __dirname:path.join(root, 'tests'), mixedRows:rows, history:json('data/collection-history.json')});
  vm.runInContext(`${adapter}\nglobalThis.reviewHarness = { $, document };`, context);
  const {$} = context.reviewHarness;
  const displayed = () => Array.from($('catalog').children, card => card.dataset.rowId);
  assert.equal($('sort-note').hidden, true);
  assert.deepEqual(displayed().filter(id => id !== pcId), previous.recommended);
  assert.deepEqual(displayed(), ids(api.filterCatalog(rows, {}, '', 'recommended')));
  $('sort').value = 'recent';
  $('sort').emit('change');
  assert.equal($('sort-note').hidden, false);
  assert.deepEqual(displayed(), ids(recent(rows)));
  for (const id of ['sharp_x68000_16', 'fmtowns_f20_20']) {
    $('catalog').children.find(card => card.dataset.rowId === id).querySelector('.favorite-toggle').emit('click');
  }
  $('favorites-open').emit('click');
  assert.deepEqual(displayed(), ['fmtowns_f20_20', 'sharp_x68000_16']);
  assert.equal($('sort-note').hidden, false);
  $('sort').value = 'name';
  $('sort').emit('change');
  assert.equal($('sort-note').hidden, true);
  $('sort').value = 'recent';
  $('sort').emit('change');
  $('favorites-back').emit('click');
  $('reset-filters').emit('click');
  assert.deepEqual(displayed(), ids(recent(rows)));
  assert.equal($('sort-note').hidden, false);
  $('sort').value = 'recommended';
  $('sort').emit('change');
  assert.deepEqual(displayed().filter(id => id !== pcId), previous.recommended);
  assert.deepEqual(displayed(), ids(api.filterCatalog(rows, {}, '', 'recommended')));
  assert.equal($('sort-note').hidden, true);
});

// Withdrawal must not remap old favorites or reintroduce removed entries.
test('Withdrawn Solaris GB2312 is absent while all five GBK sizes and PC505 remain', () => {
  for (const id of withdrawn) assert(!rows.some(r => r.id === id));
  for (const n of [12,14,16,20,24]) assert(rows.some(r => r.id === `sun_gbk_song_${n}`));
  assert.equal(recent(rows)[0].id, pcId);
  assert.equal(Object.keys(originalPrevious).length, Object.keys(previous).length);
});
