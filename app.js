/* No requests, dependencies, font files, or server required. */
(function () {
  'use strict';
  const isReference = row => row.sampleKind === 'reference';
  const isVariableGrid = row => !isReference(row) && row.variableGrid === true;
  const knownSize = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value)) && Number(value) > 0;
  const variableGridLabel = row => `不定字框${knownSize(row.designEmGrid) ? ` · em ${row.designEmGrid} 格` : ''}`;
  const variableGridNote = '设计 em 仅表示设计坐标尺度，不等于固定字符框；实际边界和进位以各字形为准。';
  const variableGridWarning = '变宽设计无统一字符框；仅按原始像素整数倍显示，不将字形硬规整到同一网格。';
  const dimensions = row => row.heightBasis === 'han-ink-grid' && knownSize(row.designHeight) ? `${row.designHeight}px字面 · 存储 ${row.cellWidth}×${row.cellHeight}` : row.heightBasis === 'han-design-grid' && knownSize(row.designHeight) ? `设计字高 ${row.designHeight}px` : isVariableGrid(row) ? variableGridLabel(row) : knownSize(row.width) && knownSize(row.height) ? `${row.width}×${row.height}` : '未核定';
  const heightValue = row => ['han-design-grid','han-ink-grid'].includes(row.heightBasis) && knownSize(row.designHeight) ? String(row.designHeight) : isVariableGrid(row) ? 'variable' : knownSize(row.height) ? String(row.height) : 'unknown';
  const heightLabel = value => value === 'unknown' ? '未核定' : value === 'variable' ? '不定字框' : `${value} px`;
  const compareHeightValues = (a, b, descending = false) => {
    const rank = value => value === 'unknown' ? 2 : value === 'variable' ? 1 : 0;
    return rank(a) - rank(b) || (rank(a) ? 0 : (Number(a) - Number(b)) * (descending ? -1 : 1));
  };
  const referenceLabel = row => `原始资料图 · ${row.referenceType || '参考资料'}`;
  const referenceWarning = '资料图不代表原生字号，不能按像素尺寸比较';
  const referenceCoverage = '资料图不作逐字覆盖验证';
  const cellDimensions = row => {
    if (isVariableGrid(row)) return null;
    const width = row.cellWidth ?? row.width, height = row.cellHeight ?? row.height;
    return knownSize(width) && knownSize(height) ? `${width}×${height} px` : null;
  };
  const asArray = value => Array.isArray(value) ? value : value ? [value] : [];
  function formatData(value) {
    if (value === null || value === undefined) return '';
    if (Array.isArray(value)) return value.map(formatData).join('、');
    if (typeof value === 'object') return Object.entries(value).map(([key, item]) => `${key}：${formatData(item)}`).join('；');
    return String(value);
  }
  function safeSourceUrl(value) {
    try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : null; } catch { return null; }
  }
  const missingGlyphLabel = value => value === ' ' ? '空格' : value;
  function updateFavoriteEntryVisibility(button, count, activeElement, fallback) {
    const hide = count === 0;
    if (hide && activeElement === button && fallback) fallback.focus({ preventScroll: true });
    button.hidden = hide; button.setAttribute('aria-hidden', String(hide));
  }
  function missingNotice(row) {
    if (isReference(row)) return '';
    const han = asArray(row.hanMissing), ascii = asArray(row.asciiMissing);
    const parts = [];
    if (han.length) parts.push(`中文缺字：${han.map(missingGlyphLabel).join('、')}`);
    if (ascii.length) parts.push(`拉丁字符／符号缺字：${ascii.map(missingGlyphLabel).join('、')}`);
    if (asArray(row.renderOmitted).length) parts.push(`未绘制（原字体有字形）：${row.renderOmitted.map(missingGlyphLabel).join('、')}`);
    if (!parts.length && asArray(row.missing).length) parts.push(`缺字：${asArray(row.missing).map(missingGlyphLabel).join('、')}`);
    const explanation = asArray(row.omittedEmptyLines).includes('ascii') ? '拉丁字符行全部缺失，样图省略该空白行；不借用其他字体补齐。' : '对应位置留空，不借用其他字体补齐。';
    return parts.length ? `${parts.join('；')}。${explanation}` : '';
  }
  const groups = [
    { key: 'height', title: '字高', value: row => [heightValue(row)] },
    { key: 'scripts', title: '字形与字符范围', value: row => asArray(row.scripts) },
    { key: 'styles', title: '风格', value: row => asArray(row.styles) },
    { key: 'uses', title: '用途', value: row => asArray(row.uses) }
  ];
  function filterCatalog(rows, selections, family = '', sort = 'recommended') {
    const filtered = rows.filter(row => (!family || row.family === family) && groups.every(group => {
      const selected = selections[group.key] || [];
      return !selected.length || (group.key === 'height' ? heightValue(row) === String(selected[0]) : group.value(row).some(value => selected.includes(value)));
    }));
    const priority = row => Number.isFinite(Number(row.priority)) ? Number(row.priority) : 0;
    const byName = (a, b) => a.name.localeCompare(b.name, 'zh-CN') || String(a.id || '').localeCompare(String(b.id || ''));
    return filtered.sort((a, b) => {
      if (sort === 'name') return byName(a, b);
      if (sort === 'recommended') {
        const difference = priority(b) - priority(a);
        if (difference) return difference;
      }
      return compareHeightValues(heightValue(a), heightValue(b), sort === 'height-desc') || byName(a, b);
    });
  }
  const FAVORITES_KEY = 'chinese-bitmap:favorites:v1';
  function cleanIds(ids, validIds) { return [...new Set(asArray(ids).filter(id => typeof id === 'string' && validIds.has(id)))]; }
  function toggleId(ids, id) { return ids.includes(id) ? ids.filter(value => value !== id) : [...ids, id]; }
  function addComparison(ids, id, validIds) {
    const clean = cleanIds(ids, validIds).slice(0, 4);
    if (!validIds.has(id) || clean.includes(id)) return { ids: clean, limitReached: false };
    return clean.length === 4 ? { ids: clean, limitReached: true } : { ids: [...clean, id], limitReached: false };
  }
  function createFavoriteStore(getStorage, validIds, aliases = {}) {
    let storage = null, ids = [], sessionOnly = false;
    try {
      storage = getStorage();
      const raw = storage.getItem(FAVORITES_KEY);
      if (raw !== null) { const parsed = JSON.parse(raw); if (!Array.isArray(parsed)) throw new Error('Invalid favorites'); ids = cleanIds(parsed.map(id => Object.prototype.hasOwnProperty.call(aliases, id) ? aliases[id] : id), validIds); }
    } catch { storage = null; sessionOnly = true; }
    return {
      get ids() { return [...ids]; },
      get sessionOnly() { return sessionOnly; },
      save(next) {
        ids = cleanIds(next, validIds);
        if (storage) { try { storage.setItem(FAVORITES_KEY, JSON.stringify(ids)); } catch { storage = null; sessionOnly = true; } }
        return [...ids];
      }
    };
  }
  function visibleCatalog(rows, selections, family, sort, favoritesView, favoriteIds) {
    return favoritesView ? filterCatalog(rows.filter(row => favoriteIds.includes(row.id)), {}, '', sort) : filterCatalog(rows, selections, family, sort);
  }
  function bindSpecimenDetails(image, scroll, name, open) {
    image.tabIndex = 0; image.setAttribute('role', 'button');
    image.setAttribute('aria-label', `查看${name}详情`);
    image.setAttribute('aria-haspopup', 'dialog'); image.title = '点击查看字样详情'; image.draggable = false;
    image.classList.add('detail-trigger');
    let start = null, moved = false;
    image.addEventListener('pointerdown', event => { start = { x: event.clientX, y: event.clientY, left: scroll.scrollLeft, top: scroll.scrollTop }; moved = false; });
    image.addEventListener('pointermove', event => { if (start && (Math.abs(event.clientX - start.x) > 6 || Math.abs(event.clientY - start.y) > 6)) moved = true; });
    image.addEventListener('pointercancel', () => { moved = true; start = null; });
    scroll.addEventListener('scroll', () => { if (start && (scroll.scrollLeft !== start.left || scroll.scrollTop !== start.top)) moved = true; });
    image.addEventListener('click', event => { if (event.detail !== 0 && moved) { event.preventDefault(); start = null; return; } start = null; image.focus({ preventScroll: true }); open(); });
    image.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); start = null; moved = false; open(); } });
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { updateFavoriteEntryVisibility, bindSpecimenDetails, filterCatalog, dimensions, isReference, isVariableGrid, variableGridLabel, variableGridNote, variableGridWarning, heightValue, heightLabel, compareHeightValues, cellDimensions, referenceLabel, referenceWarning, referenceCoverage, missingNotice, formatData, safeSourceUrl, FAVORITES_KEY, cleanIds, toggleId, addComparison, createFavoriteStore, visibleCatalog };
  if (typeof document === 'undefined') return;
  const rows = Array.isArray(window.FONT_CATALOG) ? window.FONT_CATALOG : [];
  const $ = id => document.getElementById(id);
  const validIds = new Set(rows.map(row => row.id));
  const favoritesStore = createFavoriteStore(() => window.localStorage, validIds, { simsun_native_12: 'founder_pixel12', simsun_native_14: 'founder_pixel14', ccic_chkan_24: 'isas_song_24' });
  let favoriteIds = favoritesStore.ids, comparisonIds = [], favoritesView = false;
  const selections = { height: [], scripts: [], styles: [], uses: [] };
  const create = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  };
  const iconPaths = {"bookmark": "M6 4h12v17l-6-4-6 4V4Z", "compare": "M6 4h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2ZM12 4v16", "close": "m6 6 12 12M18 6 6 18", "external": "M7 17 17 7M7 7h10v10", "back": "M20 12H4m6-6-6 6 6 6", "filter": "M4 7h10m4 0h2M4 17h2m4 0h10M14 4v6M10 14v6", "reset": "M4 10a8 8 0 1 1 1 8M4 4v6h6"};
  function icon(name, filled = false) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    for (const [key, value] of Object.entries({ class: 'icon', viewBox: '0 0 24 24', width: '18', height: '18', fill: filled ? 'currentColor' : 'none', stroke: 'currentColor', 'stroke-width': '1.6', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', focusable: 'false' })) svg.setAttribute(key, value);
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path'); path.setAttribute('d', iconPaths[name]); svg.append(path); return svg;
  }
  function buttonContent(button, label, iconName, filled = false, after = false) {
    const text = create('span', '', label), symbol = icon(iconName, filled);
    button.replaceChildren(...(after ? [text, symbol] : [symbol, text]));
  }
  let returnFocus = null;
  function showDialog(dialog) { if (document.querySelector('dialog[open]')) return; returnFocus = document.activeElement; dialog.showModal(); }
  for (const group of groups) {
    const fieldset = create('fieldset', 'filter-group');
    fieldset.append(create('legend', '', group.title));
    if (group.key === 'height') fieldset.append(create('p', 'filter-basis-note', '默认按字框高度；标明设计字高或有效字面的条目按其注明字高。'));
    const options = create('div', group.key === 'height' ? 'filter-options sizes' : 'filter-options');
    let values = [...new Set(rows.flatMap(group.value))];
    if (group.key === 'height') { values.sort((a, b) => compareHeightValues(a, b)); values.unshift(''); }
    for (const value of values) {
      const label = create('label', 'filter-option');
      const input = create('input'); input.type = group.key === 'height' ? 'radio' : 'checkbox'; input.value = value; input.dataset.group = group.key;
      if (group.key === 'height') { input.name = 'glyph-height'; input.checked = value === ''; }
      input.addEventListener('change', () => { selections[group.key] = [...options.querySelectorAll('input:checked')].map(input => input.value).filter(Boolean); render(); });
      label.append(input, create('span', '', group.key === 'height' ? value ? heightLabel(value) : '全部' : value)); options.append(label);
    }
    fieldset.append(options); $('filter-groups').append(fieldset);
  }
  const families = [...new Set(rows.map(row => row.family).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-CN'));
  for (const family of families) { const option = create('option', '', family); option.value = family; $('family').append(option); }
  function addDetail(list, title, content) {
    if (content === null || content === undefined || content === '') return;
    const dd = create('dd');
    if (content instanceof Node) dd.append(content); else dd.textContent = formatData(content);
    list.append(create('dt', '', title), dd);
  }
  function detail(row) {
    $('detail-title').textContent = row.name;
    const list = create('dl', 'detail-list');
    const permalink = create('a', '', '打开独立资料页'); permalink.href = `fonts/${encodeURIComponent(row.id)}.html`; addDetail(list, '资料页', permalink);
    addDetail(list, '家族', row.family);
    const cell = cellDimensions(row);
    if (row.heightBasis === 'han-ink-grid') { addDetail(list, '筛选依据', `有效中文字面 ${row.designHeight}px，存储字框和空白边距另列`); addDetail(list, '排版说明', row.layoutNote); }
    if (row.sourceType === 'physical-extraction') addDetail(list, '来源', row.sourceLabel);
    if (row.heightBasis === 'han-design-grid') { addDetail(list, '筛选依据', `汉字设计格高 ${row.designHeight}px，不是固定字符框或原字体行高`); addDetail(list, '排版说明', row.layoutNote); }
    if (asArray(row.renderOmitted).length) addDetail(list, '有字形但未绘制', row.renderOmissionNote);
    addDetail(list, '字符框', cell ? `${cell}${row.heightBasis==='han-ink-grid' ? '（存储空白完整保留；筛选按有效中文字面）' : '（字高筛选以此为准）'}` : null);
    if (isVariableGrid(row)) { addDetail(list, '字框类型', variableGridLabel(row)); addDetail(list, '设计说明', variableGridNote); }
    if (isReference(row)) { addDetail(list, '资料类型', row.referenceType || '参考资料'); addDetail(list, '核验边界', row.referenceNote || referenceWarning); }
    if (row.inkWidth && row.inkHeight) addDetail(list, '字面／墨迹', `${row.inkWidth}×${row.inkHeight} px（不等于字符框大小）`);
    addDetail(list, '字符范围', row.scripts); addDetail(list, '覆盖说明', row.coverage);
    addDetail(list, '样本文字', row.text); addDetail(list, row.asciiOrigin === 'fullwidth-native' ? '全角英数样文（非ASCII）' : '拉丁字符', row.asciiOrigin === 'absent' ? null : row.asciiText);
    addDetail(list, '缺字', isReference(row) ? referenceCoverage : Array.isArray(row.missing) ? row.missing.length ? row.missing.join('、') : '本次样本文字未发现缺字' : row.missing);
    addDetail(list, '风格', row.styles); addDetail(list, '用途', row.uses);
    addDetail(list, '授权状态', row.licenseStatus || '尚未确认，请到来源项目核实。');
    addDetail(list, '许可说明', row.licenseNote); addDetail(list, '字形来源', row.provenance);
    if (row.acquisitionGuide) {
      const guide = create('div', 'acquisition-guide');
      for (const [index, step] of asArray(row.acquisitionGuide.steps).entries()) guide.append(create('p', '', `${index + 1}. ${step}`));
      guide.append(create('p', 'license-note', row.acquisitionGuide.notice || ''));
      for (const item of asArray(row.acquisitionGuide.links)) {
        const url = safeSourceUrl(item.url); if (!url) continue;
        const paragraph = create('p', ''), link = create('a', '', item.label); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; paragraph.append(link); guide.append(paragraph);
      }
      addDetail(list, row.acquisitionGuide.title || '官网授权与获取', guide);
    }
    addDetail(list, '样张类型', isReference(row) ? '原始资料图，不作为原生像素样张' : row.sampleLabel || (row.sampleKind === 'historical' ? '历史样张：保留来源实际可用字形，不与其他来源拼接' : row.sampleKind === 'partial' ? '统一新样文（缺字位置留空）' : row.sampleKind === 'standard' ? '统一比较样文' : row.sampleKind === 'osd' ? '来源限定字符样张' : null));
    if (safeSourceUrl(row.sourceUrl)) {
      const link = create('a', '', row.sourceLabel || '来源项目'); link.href = safeSourceUrl(row.sourceUrl); link.target = '_blank'; link.rel = 'noopener noreferrer'; link.append(icon('external')); addDetail(list, '来源', link);
    }
    if (row.nativeEvidence) {
      const evidence = create('div', 'native-evidence');
      if (typeof row.nativeEvidence === 'object' && !Array.isArray(row.nativeEvidence)) {
        const labels = { summary: '', method: '提取方式', bitmap_tables: '内嵌位图表', native_ppem: '原生像素尺寸', grid_step: '原生网格步长', maximum_grid_error: '最大网格误差' };
        for (const [key, value] of Object.entries(row.nativeEvidence)) {
          if (key === 'sourceUrl' || key === 'sha256') continue;
          evidence.append(create('p', '', `${labels[key] === '' ? '' : `${labels[key] || key}：`}${formatData(value)}`));
        }
        const url = safeSourceUrl(row.nativeEvidence.sourceUrl);
        if (url) { const link = create('a', '', '查看原生设计来源'); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.append(icon('external')); evidence.append(link); }
      } else evidence.textContent = formatData(row.nativeEvidence);
      addDetail(list, '原生证据', evidence);
    }
    for (const related of asArray(row.relatedSources)) {
      const source = create('div', 'related-source');
      source.append(create('p', '', `${related.name}${related.version ? `（版本 ${related.version}）` : ''}`));
      for (const key of ['comparison', 'coverageNote', 'provenance', 'licenseNote']) if (related[key]) source.append(create('p', '', related[key]));
      const url = safeSourceUrl(related.sourceUrl);
      if (url) { const link = create('a', '', '查看相关来源'); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.append(icon('external')); source.append(link); }
      addDetail(list, '相关来源', source);
    }
    addDetail(list, '说明', row.notes);
    const note = create('p', 'license-note', '样张仅供字形比较，不提供字体文件。预览不构成字体使用许可；请在使用前核实来源项目的适用授权。');
    $('detail-content').replaceChildren(list, note); showDialog($('detail-dialog'));
  }
  function specimenImage(row, scale) {
    const reference = isReference(row), image = create('img', reference ? 'specimen-image reference-image' : 'specimen-image'); image.src = row.specimen;
    image.alt = reference ? `${row.name}：${referenceLabel(row)}` : [row.text, row.asciiText].filter(Boolean).join(' / ') || `${row.name}真实点阵样张`;
    image.loading = 'lazy'; image.decoding = 'async';
    function setSize() {
      const width = Number(row.specimenWidth) || image.naturalWidth;
      const height = Number(row.specimenHeight) || image.naturalHeight;
      if (width && height) { image.width = width * (reference ? 1 : scale); image.height = height * (reference ? 1 : scale); }
    }
    image.setScale = next => { if (!reference) { scale = next; setSize(); } };
    image.addEventListener('load', setSize); setSize();
    image.addEventListener('error', () => { image.alt = `${row.name}：样张未能载入，请检查文件是否完整。`; });
    return image;
  }
  function card(row) {
    const reference = isReference(row), article = create('article', reference ? 'specimen reference-specimen' : isVariableGrid(row) ? 'specimen variable-grid-specimen' : 'specimen'); article.dataset.rowId = row.id; const header = create('div', 'specimen-header');
    header.append(create('h2', '', row.name), create('span', 'specimen-meta', `${reference ? heightValue(row) === 'unknown' ? '字高未核定' : '参考资料' : dimensions(row)} · ${asArray(row.scripts).join(' / ')}`));
    const button = create('a', 'detail-button'); button.href = `fonts/${encodeURIComponent(row.id)}.html`; buttonContent(button, '详情', 'external', false, true); button.setAttribute('aria-label', `查看${row.name}详情`); button.addEventListener('click', event => { if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return; event.preventDefault(); detail(row); }); const actions = create('div', 'row-actions');
    const favorite = create('button', 'favorite-toggle'); favorite.dataset.favoriteId = row.id; favorite.addEventListener('click', () => toggleFavorite(row.id));
    const compare = create('button', 'compare-toggle'); compare.dataset.compareId = row.id; compare.addEventListener('click', () => toggleComparison(row.id));
    actions.append(favorite, compare, button); header.append(actions);
    const panel = create('div', reference ? 'sample-panel reference-panel' : 'sample-panel');
    if (reference) {
      const scroll = create('div', 'image-scroll reference-scroll'); scroll.tabIndex = 0; scroll.setAttribute('aria-label', `${row.name}原始资料图，按可用宽度显示`);
      const image = specimenImage(row, 1); bindSpecimenDetails(image, scroll, row.name, () => detail(row)); scroll.append(image);
      panel.append(create('div', 'sample-label', referenceLabel(row)), scroll); article.append(header, panel, create('p', 'sample-note reference-note', row.referenceNote || referenceWarning));
      return article;
    }
    const enlarged = create('div', 'sample-enlarged'); const label = create('label', 'sample-label', '放大观察 · ');
    const zoom = create('select', 'zoom-control'); zoom.setAttribute('aria-label', `${row.name}放大倍数`);
    for (const scale of [2, 3, 4]) { const option = create('option', '', `${scale}×`); option.value = scale; option.selected = scale === 3; zoom.append(option); }
    label.append(zoom); const enlargedScroll = create('div', 'image-scroll'); enlargedScroll.tabIndex = 0; enlargedScroll.setAttribute('aria-label', `${row.name}放大样张，超宽时可横向滚动`);
    const largeImage = specimenImage(row, 3); bindSpecimenDetails(largeImage, enlargedScroll, row.name, () => detail(row)); enlargedScroll.append(largeImage); enlarged.append(label, enlargedScroll);
    zoom.addEventListener('change', () => largeImage.setScale(Number(zoom.value)));
    const native = create('div', 'sample-native'); const nativeScroll = create('div', 'image-scroll'); nativeScroll.tabIndex = 0; nativeScroll.setAttribute('aria-label', `${row.name}原尺寸样张，超宽时可横向滚动`);
    const nativeImage = specimenImage(row, 1); bindSpecimenDetails(nativeImage, nativeScroll, row.name, () => detail(row)); nativeScroll.append(nativeImage); native.append(create('div', 'sample-label', row.gridReconstruction ? '设计格点 · 1×' : '原尺寸 · 1×'), nativeScroll);
    panel.append(enlarged, native); article.append(header, panel);
    if (isVariableGrid(row)) article.append(create('p', 'sample-note variable-grid-note', variableGridNote));
    if (row.sampleLabel) article.append(create('p', 'sample-note', row.sampleLabel));
    else if (row.sampleKind === 'historical') article.append(create('p', 'sample-note', '历史样张 · 字符范围与统一样文可能不同，详见详情。'));
    const missingText = missingNotice(row);
    if (missingText) article.append(create('p', 'missing-hint', missingText));
    return article;
  }
  function render() {
    const results = visibleCatalog(rows, selections, $('family').value, $('sort').value, favoritesView, favoriteIds);
    const fragment = document.createDocumentFragment(); results.forEach(row => fragment.append(card(row)));
    $('catalog').replaceChildren(fragment); $('empty').hidden = results.length > 0;
    $('result-count').textContent = favoritesView ? `${results.length} 个收藏` : `${results.length} 个字样`;
    document.querySelector('.layout').classList.toggle('favorites-view', favoritesView);
    $('favorites-back').hidden = !favoritesView; $('favorites-privacy').hidden = !favoritesView;
    $('family-control').hidden = favoritesView; $('active-filters').hidden = favoritesView; $('filters-open').hidden = favoritesView;
    $('empty').querySelector('p').textContent = favoritesView ? '还没有收藏。点击字样旁的收藏按钮，即可在这里查看。' : '没有符合这些条件的字样。';
    $('empty-reset').textContent = favoritesView ? '浏览全部字样' : '清空筛选，查看全部';
    const active = document.createDocumentFragment();
    for (const group of groups) for (const value of selections[group.key]) {
      const button = create('button'); buttonContent(button, group.key === 'height' ? `字高 ${heightLabel(value)}` : value, 'close', false, true); button.setAttribute('aria-label', `移除筛选：${group.title} ${group.key === 'height' ? heightLabel(value) : value}`);
      button.addEventListener('click', () => { selections[group.key] = selections[group.key].filter(item => item !== value); syncInputs(); render(); }); active.append(button);
    }
    if ($('family').value) { const button = create('button'); buttonContent(button, $('family').value, 'close', false, true); button.setAttribute('aria-label', '移除字体家族筛选'); button.addEventListener('click', () => { $('family').value = ''; render(); }); active.append(button); }
    $('active-filters').replaceChildren(active);
    const count = Object.values(selections).reduce((sum, values) => sum + values.length, 0); $('filter-count').textContent = count ? `(${count})` : '';
    $('reset-filters').disabled = !count && !$('family').value;
    refreshStateControls();
    if (!rows.length) { $('empty').querySelector('p').textContent = '字样目录未能载入，请确认 data/catalog.js 文件完整。'; $('empty-reset').hidden = true; }
  }
  function announce(text) { $('action-notice').textContent = text; $('action-notice').hidden = !text; }
  function headerFocusTarget() { return $('favorites-open').hidden ? $('about-open') : $('favorites-open'); }
  function refreshStateControls() {
    updateFavoriteEntryVisibility($('favorites-open'), favoriteIds.length, document.activeElement, favoritesView ? $('favorites-back') : $('about-open'));
    $('favorites-count').textContent = favoriteIds.length;
    $('favorites-open').setAttribute('aria-pressed', String(favoritesView));
    $('favorites-clear').hidden = !favoritesView || !favoriteIds.length;
    if (!favoriteIds.length) $('favorites-confirm').hidden = true;
    $('storage-notice').hidden = !favoritesStore.sessionOnly;
    $('storage-notice').textContent = favoritesStore.sessionOnly ? '无法读取或保存浏览器收藏数据。当前收藏仅在本页会话内有效，刷新或关闭后可能丢失。' : '';
    document.querySelectorAll('[data-favorite-id]').forEach(button => {
      const row = rows.find(row => row.id === button.dataset.favoriteId), selected = favoriteIds.includes(row.id);
      buttonContent(button, selected ? '已收藏' : '收藏', 'bookmark', selected); button.setAttribute('aria-pressed', String(selected));
      button.setAttribute('aria-label', `${selected ? '取消收藏' : '收藏'}${row.name}`); button.title = button.getAttribute('aria-label');
    });
    document.querySelectorAll('[data-compare-id]').forEach(button => {
      const row = rows.find(row => row.id === button.dataset.compareId), selected = comparisonIds.includes(row.id);
      buttonContent(button, selected ? '已选对比' : '对比', 'compare'); button.setAttribute('aria-pressed', String(selected));
      button.setAttribute('aria-label', `${selected ? '移出对比' : '加入对比'}${row.name}`); button.title = button.getAttribute('aria-label');
    });
  }
  function toggleFavorite(id) {
    favoriteIds = favoritesStore.save(toggleId(favoriteIds, id));
    if (favoritesView) {
      const oldIndex = [...$('catalog').children].findIndex(element => element.dataset.rowId === id);
      render();
      const next = $('catalog').children[Math.max(0, Math.min(oldIndex, $('catalog').children.length - 1))];
      (next?.querySelector('.favorite-toggle') || $('favorites-back')).focus({ preventScroll: true });
    } else refreshStateControls(); // Do not recreate specimens or move scroll/focus when starring a row.
  }
  function setFavoritesView(next) {
    favoritesView = next; $('favorites-confirm').hidden = true; announce(''); render();
  }
  function toggleComparison(id) {
    if (comparisonIds.includes(id)) comparisonIds = comparisonIds.filter(value => value !== id);
    else {
      const result = addComparison(comparisonIds, id, validIds);
      if (result.limitReached) { announce('最多同时对比 4 个字样，请先移除一个。'); $('compare-count').textContent = '最多 4 项，请先移除'; return; }
      comparisonIds = result.ids;
    }
    announce(''); refreshStateControls(); renderTray();
  }
  function removeComparison(id, fromDialog = false) {
    comparisonIds = comparisonIds.filter(value => value !== id); announce(''); refreshStateControls(); renderTray();
    if (fromDialog) { renderComparison(); ($('compare-content').querySelector('button') || $('compare-dialog').querySelector('.close-button')).focus({ preventScroll: true }); }
  }
  function renderTray() {
    $('compare-tray').hidden = comparisonIds.length === 0;
    document.body.classList.toggle('has-comparison', comparisonIds.length > 0);
    const items = document.createDocumentFragment();
    for (const id of comparisonIds) {
      const row = rows.find(row => row.id === id);
      const button = create('button', 'compare-chip'); buttonContent(button, row.name, 'close', false, true); button.setAttribute('aria-label', `移出对比：${row.name}`);
      button.addEventListener('click', () => { removeComparison(id); ($('compare-items').querySelector('button') || headerFocusTarget()).focus({ preventScroll: true }); }); items.append(button);
    }
    $('compare-items').replaceChildren(items);
    $('compare-count').textContent = `${comparisonIds.length} / 4`;
    $('compare-open').disabled = comparisonIds.length < 2;
    $('compare-open').textContent = comparisonIds.length < 2 ? '再选 1 个开始对比' : '打开对比';
  }
  function renderComparison() {
    const content = document.createDocumentFragment(), scale = Number($('compare-zoom').value);
    const selectedRows = comparisonIds.map(id => rows.find(row => row.id === id)), hasReference = selectedRows.some(isReference), hasNative = selectedRows.some(row => !isReference(row)), hasVariableGrid = selectedRows.some(isVariableGrid);
    const warnings = [];
    if (hasReference) warnings.push(referenceWarning + '。');
    if (hasVariableGrid) warnings.push(variableGridWarning);
    if (selectedRows.some(row => row.sampleKind === 'osd')) warnings.push(`${selectedRows.some(row => row.sampleKind === 'osd' && row.sampleLabel) ? '包含来源限定设备样张' : '包含 OSD 来源限定样张'}，其文字与普通字体不同，请勿将不同文字当作同字比较。`);
    $('compare-warning').textContent = warnings.join(' '); $('compare-warning').hidden = !warnings.length; $('compare-warning').classList.toggle('reference-warning', hasReference);
    $('compare-warning').classList.toggle('variable-grid-warning', hasVariableGrid && !hasReference);
    const toolbar = document.querySelector('.compare-toolbar'); toolbar.hidden = !hasNative;
    toolbar.querySelector('label').textContent = hasReference ? '原生字样放大' : '统一放大';
    toolbar.querySelector('span').textContent = hasReference ? '倍率仅用于原生字样；资料图按可用宽度显示' : '保留原生比例，不归一化字高';
    for (const id of comparisonIds) {
      const row = rows.find(row => row.id === id), reference = isReference(row), article = create('article', reference ? 'comparison-row reference-specimen' : isVariableGrid(row) ? 'comparison-row variable-grid-specimen' : 'comparison-row');
      const header = create('div', 'specimen-header');
      header.append(create('h3', '', row.name), create('span', 'specimen-meta', `${reference ? row.referenceType || '参考资料' : dimensions(row)} · ${asArray(row.scripts).join(' / ')}`));
      const remove = create('button', 'quiet-button'); buttonContent(remove, '移除', 'close', false, true); remove.setAttribute('aria-label', `移出对比：${row.name}`); remove.addEventListener('click', () => removeComparison(id, true)); header.append(remove);
      const scroll = create('div', reference ? 'image-scroll reference-scroll' : 'image-scroll'); scroll.tabIndex = 0; scroll.setAttribute('aria-label', reference ? `${row.name}原始资料图，按可用宽度显示` : `${row.name}对比样张，可横向滚动`);
      const img = specimenImage(row, scale); img.loading = 'eager'; scroll.append(img); article.append(header);
      if (reference) article.append(create('p', 'sample-label', referenceLabel(row)));
      article.append(scroll);
      if (reference && row.referenceNote) article.append(create('p', 'sample-note reference-note', row.referenceNote));
      if (isVariableGrid(row)) article.append(create('p', 'sample-note variable-grid-note', variableGridNote));
      if (row.sampleKind === 'osd') article.append(create('p', 'sample-note', `${row.sampleLabel || 'OSD 来源限定文字'}，与其他普通字体样文不同。`));
      const missing = missingNotice(row); if (missing) article.append(create('p', 'missing-hint', missing)); content.append(article);
    }
    if (!comparisonIds.length) content.append(create('p', 'muted', '对比列表已清空。关闭此窗口后，可重新选择字样。'));
    $('compare-content').replaceChildren(content);
  }
  $('favorites-open').addEventListener('click', () => setFavoritesView(!favoritesView));
  $('favorites-back').addEventListener('click', () => { setFavoritesView(false); headerFocusTarget().focus(); });
  $('favorites-clear').addEventListener('click', () => { $('favorites-confirm').hidden = false; $('favorites-cancel-clear').focus(); });
  $('favorites-cancel-clear').addEventListener('click', () => { $('favorites-confirm').hidden = true; $('favorites-clear').focus(); });
  $('favorites-confirm-clear').addEventListener('click', () => { favoriteIds = favoritesStore.save([]); $('favorites-confirm').hidden = true; render(); $('favorites-back').focus(); });
  $('compare-clear').addEventListener('click', () => { comparisonIds = []; announce(''); refreshStateControls(); renderTray(); headerFocusTarget().focus({ preventScroll: true }); });
  $('compare-open').addEventListener('click', () => { if (comparisonIds.length < 2) return; $('compare-zoom').value = '3'; renderComparison(); showDialog($('compare-dialog')); });
  $('compare-zoom').addEventListener('change', () => { document.querySelectorAll('#compare-content .specimen-image:not(.reference-image)').forEach(image => image.setScale(Number($('compare-zoom').value))); });
  function syncInputs() { document.querySelectorAll('#filter-groups input').forEach(input => { input.checked = input.dataset.group === 'height' && input.value === '' ? selections.height.length === 0 : selections[input.dataset.group].includes(input.value); }); }
  function reset() { Object.keys(selections).forEach(key => { selections[key] = []; }); $('family').value = ''; syncInputs(); render(); }
  $('reset-filters').addEventListener('click', reset); $('empty-reset').addEventListener('click', () => { if (favoritesView) { setFavoritesView(false); headerFocusTarget().focus(); } else reset(); });
  $('family').addEventListener('change', render); $('sort').addEventListener('change', render);
  function closeDrawer() { $('filters').classList.remove('is-open'); $('drawer-backdrop').hidden = true; $('filters-open').setAttribute('aria-expanded', 'false'); document.body.style.overflow = ''; $('main').inert = false; $('compare-tray').inert = false; document.querySelector('.site-header').inert = false; $('filters-open').focus(); }
  $('filters-open').addEventListener('click', () => { $('filters').classList.add('is-open'); $('drawer-backdrop').hidden = false; $('filters-open').setAttribute('aria-expanded', 'true'); document.body.style.overflow = 'hidden'; $('main').inert = true; $('compare-tray').inert = true; document.querySelector('.site-header').inert = true; $('filters-close').focus(); });
  $('filters-close').addEventListener('click', closeDrawer); $('drawer-backdrop').addEventListener('click', closeDrawer);
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && $('filters').classList.contains('is-open')) closeDrawer(); });
  window.matchMedia('(max-width:700px)').addEventListener('change', event => { if (!event.matches && $('filters').classList.contains('is-open')) closeDrawer(); });
  $('about-open').addEventListener('click', () => showDialog($('about-dialog')));
  document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => $(button.dataset.close).close()));
  document.querySelectorAll('dialog').forEach(dialog => { dialog.addEventListener('close', () => { const target = returnFocus?.isConnected && !returnFocus.disabled && !returnFocus.closest('[hidden]') ? returnFocus : headerFocusTarget(); target.focus({ preventScroll: true }); }); dialog.addEventListener('click', event => { if (event.target === dialog) { const bounds = dialog.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close(); } }); });
  render(); renderTray();
})();
