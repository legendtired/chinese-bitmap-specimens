from approved_hitech_adp3 import before_hitech_adp3_rows, before_hitech_adp3_data, before_hitech_adp3_bytes
"""Reverse precisely the approved Xelibri14 addition for historical SHA audits.
Not imported by the site or builder. Unknown rows/changes are never normalized.
"""
from pathlib import Path
import copy
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ID = 'siemens_xelibri_14'


def before_xelibri14_rows(rows):
    added = [r for r in rows if r['id'] == ID]
    if added:
        m = json.loads((ROOT/'data/release-xelibri14.json').read_text())
        assert len(added) == 1
        assert hashlib.sha256(json.dumps(added[0], ensure_ascii=False, sort_keys=True).encode()).hexdigest() == m['addedRowSha256'], 'Unreviewed Xelibri14 row change'
    return [r for r in before_hitech_adp3_rows(rows) if r['id'] != ID]


def before_xelibri14_data(path, value, *, hitech_reversed=False):
    if not hitech_reversed:
        value = before_hitech_adp3_data(path, value)
    if path == 'data/catalog.json':
        return before_xelibri14_rows(value)
    if path == 'data/collection-history.json':
        value = copy.deepcopy(value)
        batch = {'sourceManifest': 'release-xelibri14.json', 'ids': [ID]}
        matches = [b for b in value['batches'] if b.get('sourceManifest') == batch['sourceManifest']]
        if matches:
            assert matches == [batch] and value['batches'][-1] == batch
            value['batches'].pop()
    elif path == 'data/summary.json':
        value = copy.deepcopy(value)
        for key in ('rows', 'nativePngCount', 'standardChineseComplete', 'ordinaryRows', 'standardAsciiComplete', 'ordinaryAsciiRows'):
            value[key] -= 1
        value['sampleKinds']['standard'] -= 1
        for script in ('简体', '繁体'):
            value['scripts'][script] -= 1
    return value


def before_xelibri14_bytes(path, root=ROOT):
    data = before_hitech_adp3_bytes(path, root)
    if path in ('data/catalog.json', 'data/collection-history.json', 'data/summary.json'):
        return (json.dumps(before_xelibri14_data(path, json.loads(data), hitech_reversed=True), ensure_ascii=False, indent=2)+'\n').encode()
    if path in ('data/catalog.js', 'data/collection-history.js'):
        prefix, payload = data.decode().split(' = ', 1)
        original = before_xelibri14_data(path.replace('.js', '.json'), json.loads(payload.rstrip().removesuffix(';')), hitech_reversed=True)
        return (prefix+' = '+json.dumps(original, ensure_ascii=False, indent=2)+';\n').encode()
    if path == 'sitemap.xml':
        text, count = re.subn(r'<url><loc>https://legendtired.github.io/chinese-bitmap-specimens/fonts/'+ID+r'\.html</loc></url>\n', '', data.decode())
        assert count == 1
        return text.encode()
    if path == 'index.html':
        text = data.decode()
        for asset in ('data/catalog.js', 'data/collection-history.js', 'app.js'):
            current = hashlib.sha256(before_hitech_adp3_bytes(asset, root)).hexdigest()[:16]
            previous = hashlib.sha256(before_xelibri14_bytes(asset, root)).hexdigest()[:16]
            tag = f'src="{asset}?v={current}"'
            assert text.count(tag) == 1
            text = text.replace(tag, f'src="{asset}?v={previous}"', 1)
        text, count = re.subn(r'<article class="specimen" data-row-id="'+ID+r'">.*?</article>\n', '', text, flags=re.S)
        assert count == 1 and text.count('>247 个字样</span>') == 1
        return text.replace('>247 个字样</span>', '>246 个字样</span>', 1).encode()
    return data


def before_xelibri14_file_sha(path):
    return hashlib.sha256(before_xelibri14_bytes(path)).hexdigest()
