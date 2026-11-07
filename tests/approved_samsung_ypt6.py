"""Reverse only the approved YP-T6 addition for immutable historical audits.
Never used by the site/builder. samsung-ypt6.test.py locks the 243 retained rows and files.
"""
from approved_sc_song13 import before_sc13_rows, before_sc13_data, before_sc13_bytes
from pathlib import Path
import copy
import hashlib
import json
import re
ROOT = Path(__file__).resolve().parents[1]
ID = 'samsung_ypt6_14x16'


def before_ypt6_rows(rows):
    return [r for r in before_sc13_rows(rows) if r['id'] != ID]


def before_ypt6_data(path, value, *, sc13_reversed=False):
    if not sc13_reversed:
        value = before_sc13_data(path, value)
    if path == 'data/catalog.json':
        return before_ypt6_rows(value)
    if path == 'data/collection-history.json':
        value = copy.deepcopy(value)
        batch = {'sourceManifest': 'release-samsung-ypt6.json', 'ids': [ID]}
        if batch in value['batches']:
            assert value['batches'][-1] == batch
            value['batches'].pop()
    elif path == 'data/summary.json':
        value = copy.deepcopy(value)
        for key in ('rows', 'nativePngCount', 'standardChineseComplete', 'ordinaryRows', 'standardAsciiComplete', 'ordinaryAsciiRows'):
            value[key] -= 1
        value['sampleKinds']['standard'] -= 1
        for script in ('简体', '繁体'):
            value['scripts'][script] -= 1
    return value


def before_ypt6_bytes(path, root=ROOT):
    data = before_sc13_bytes(path, root)
    if path in ('data/catalog.json', 'data/collection-history.json', 'data/summary.json'):
        return (json.dumps(before_ypt6_data(path, json.loads(data), sc13_reversed=True), ensure_ascii=False, indent=2) + '\n').encode()
    if path in ('data/catalog.js', 'data/collection-history.js'):
        prefix, payload = data.decode().split(' = ', 1)
        original = before_ypt6_data(path.replace('.js', '.json'), json.loads(payload.rstrip().removesuffix(';')), sc13_reversed=True)
        return (prefix + ' = ' + json.dumps(original, ensure_ascii=False, indent=2) + ';\n').encode()
    if path == 'sitemap.xml':
        text, count = re.subn(r'<url><loc>https://legendtired.github.io/chinese-bitmap-specimens/fonts/' + ID + r'\.html</loc></url>\n', '', data.decode())
        assert count == 1
        return text.encode()
    if path == 'index.html':
        text = data.decode()
        # Restore precise content hashes for the prior catalog/history, never remove versions.
        for asset in ('data/catalog.js', 'data/collection-history.js', 'app.js'):
            current = hashlib.sha256(before_sc13_bytes(asset, root)).hexdigest()[:16]
            previous = hashlib.sha256(before_ypt6_bytes(asset, root)).hexdigest()[:16]
            tag = f'src="{asset}?v={current}"'
            assert text.count(tag) == 1
            text = text.replace(tag, f'src="{asset}?v={previous}"', 1)
        text, count = re.subn(r'<article class="specimen" data-row-id="' + ID + r'">.*?</article>\n', '', text, flags=re.S)
        assert count == 1 and text.count('>244 个字样</span>') == 1
        return text.replace('>244 个字样</span>', '>243 个字样</span>', 1).encode()
    return data


def before_ypt6_file_sha(path):
    return hashlib.sha256(before_ypt6_bytes(path)).hexdigest()
