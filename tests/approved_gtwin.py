"""Exact reversal of one reviewed GTWIN batch for immutable historical audits."""
from pathlib import Path
import copy
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = 'release-gtwin.json'
MANIFEST = json.loads((ROOT / 'data' / MANIFEST_NAME).read_text())
IDS = MANIFEST['addedIds']
JSON_PATHS = ('data/catalog.json', 'data/collection-history.json', 'data/summary.json')
JS_PATHS = ('data/catalog.js', 'data/collection-history.js')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())


def before_gtwin_rows(rows):
    found = [r for r in rows if r['id'] in IDS]
    if found:
        assert [r['id'] for r in found] == IDS and rows[-len(IDS):] == found, 'Unreviewed GTWIN rows/order'
        assert {r['id']: digest(r) for r in found} == MANIFEST['rowSha256ById'], 'Unreviewed GTWIN row'
    assert len({r['id'] for r in rows}) == len(rows), 'Duplicate catalog row'
    return [r for r in rows if r['id'] not in IDS]


def before_gtwin_data(path, value):
    if path == 'data/catalog.json':
        return before_gtwin_rows(value)
    value = copy.deepcopy(value)
    if path == 'data/collection-history.json':
        found = [b for b in value['batches'] if b.get('sourceManifest') == MANIFEST_NAME or any(i in IDS for i in b['ids'])]
        if found:
            assert found == [MANIFEST['batch']] and value['batches'][-1] == MANIFEST['batch'], 'Unreviewed GTWIN batch'
            value['batches'].pop()
    elif path == 'data/summary.json' and value.get('rows') == 264:
        assert value == MANIFEST['summary'], 'Unreviewed GTWIN summary'
        value = copy.deepcopy(MANIFEST['baseSummary'])
    return value


def before_gtwin_bytes(path, root=ROOT):
    data = (root/path).read_bytes()
    if path not in MANIFEST['changedFileHashes']:
        return data
    assert sha(data) == MANIFEST['changedFileHashes'][path], 'Unreviewed GTWIN change: ' + path
    if path in JSON_PATHS:
        value = before_gtwin_data(path, json.loads(data))
        original = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    elif path in JS_PATHS:
        prefix, payload = data.decode().split(' = ', 1)
        value = before_gtwin_data(path.replace('.js', '.json'), json.loads(payload.rstrip().removesuffix(';')))
        original = (prefix + ' = ' + json.dumps(value, ensure_ascii=False, indent=2) + ';\n').encode()
    elif path == 'sitemap.xml':
        original = data.decode()
        for ident in IDS:
            original, count = re.subn(
                r'<url><loc>https://legendtired\.github\.io/chinese-bitmap-specimens/fonts/' + re.escape(ident) + r'\.html</loc></url>\n',
                '', original)
            assert count == 1, ident
        original = original.encode()
    elif path == 'index.html':
        original = data.decode()
        for asset in (*JS_PATHS, 'app.js'):
            current = sha((root/asset).read_bytes())[:16]
            previous = sha(before_gtwin_bytes(asset, root))[:16]
            tag = f'src="{asset}?v={current}"'
            assert original.count(tag) == 1, asset
            original = original.replace(tag, f'src="{asset}?v={previous}"', 1)
        for ident in IDS:
            original, count = re.subn(r'<article class="specimen" data-row-id="' + re.escape(ident) + r'">.*?</article>\n', '', original, flags=re.S)
            assert count == 1, ident
        assert original.count('>264 个字样</span>') == 1
        original = original.replace('>264 个字样</span>', '>263 个字样</span>', 1).encode()
    else:
        original = MANIFEST['baseChangedFiles'][path].encode()
    assert sha(original) == MANIFEST['baseFilesSha256'][path], 'Incorrect GTWIN reversal: ' + path
    return original
