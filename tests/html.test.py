"""Static DOM structure checks; these do not simulate a browser."""
from html.parser import HTMLParser
from pathlib import Path
class Document(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids = {}; self.tags = []; self.scripts = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs); self.tags.append((tag,a))
        if 'id' in a:
            assert a['id'] not in self.ids, f"Duplicate id: {a['id']}"
            self.ids[a['id']] = (tag,a)
        if tag == 'script' and a.get('type') != 'application/ld+json': self.scripts.append(a)
root=Path(__file__).resolve().parents[1]
html=(root/'index.html').read_text()
doc=Document(); doc.feed(html)
for tag,a in doc.tags:
    for key in ('aria-labelledby','aria-controls'):
        for target in a.get(key,'').split(): assert target in doc.ids, target
    if tag == 'img':
        assert 'alt' in a
        if a.get('src') == 'assets/wordmark.png': assert (a.get('width'), a.get('height')) == ('192', '48')
    if tag == 'dialog': assert a.get('aria-labelledby')
    if tag == 'script' or (tag == 'link' and a.get('rel') != 'canonical'): assert not a.get('src',a.get('href','')).startswith(('http:','https:','//'))
assert [x['src'] for x in doc.scripts] == ['data/catalog.js','app.js']
assert all('defer' in x for x in doc.scripts)
assert doc.ids['family'][0] == doc.ids['sort'][0] == 'select'
assert any(tag=='a' and a.get('href')=='index.html' for tag,a in doc.tags)
toolbar=html.split('<div class="toolbar">',1)[1].split('<div id="catalog"',1)[0]
assert toolbar.index('id="family"') < toolbar.index('id="result-count"') < toolbar.index('id="active-filters"') < toolbar.index('id="sort"')
assert toolbar.count('id="active-filters"') == 1
css=(root/'styles.css').read_text()
assert '.sizes{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));' in css
assert '.toolbar{display:flex;flex-wrap:wrap;' in css
assert '.active-filters:not(:empty){margin-bottom:' not in css
for id in ('favorites-open','favorites-count','favorites-back','favorites-clear','favorites-confirm','favorites-confirm-clear','favorites-cancel-clear','storage-notice','compare-tray','compare-items','compare-clear','compare-open','compare-dialog','compare-zoom','compare-content'):
    assert id in doc.ids, id
assert doc.ids['favorites-open'][1]['aria-pressed'] == 'false'
assert 'hidden' in doc.ids['favorites-confirm'][1]
assert 'hidden' in doc.ids['compare-tray'][1]
assert doc.ids['compare-dialog'][1]['aria-labelledby'] == 'compare-title'
assert 'disabled' in doc.ids['compare-open'][1]
for tag, attrs in doc.tags:
    if tag == 'svg':
        assert attrs.get('aria-hidden') == 'true'
        assert attrs.get('focusable') == 'false'
        assert attrs.get('stroke-width') == '1.6'
assert 'appearance:none' in css and '--chevron:url("data:image/svg+xml,' in css
assert '.specimen-header h2{font-size:16px;font-weight:400;' in css
assert '.sample-panel{display:grid;' in css
assert 'background:transparent;border-radius:0;padding:0;' in css
app=(root/'app.js').read_text()
for character in ('★','☆','✓','↗','←','↑','↓'):
    assert character not in html and character not in app, character
assert 'createElementNS' in app and 'stroke-linecap' in app
print('Static HTML checks passed: unique IDs, ARIA targets, dialog names, alt text, local scripts and file-safe wordmark link.')
