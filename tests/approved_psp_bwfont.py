"""Reverse only the approved PSP addition for historical release audits.
Never imported by the site or builder. psp-bwfont.test.py locks all retained rows/pixels/pages.
"""
from approved_mrobe_mr100 import before_mrobe_rows, before_mrobe_data, before_mrobe_bytes
from pathlib import Path
import copy
import hashlib
import json
import re
ROOT = Path(__file__).resolve().parents[1]
ID = 'sony_psp_bwfont_16x18'


def before_psp_rows(rows):
    return [r for r in before_mrobe_rows(rows) if r['id'] != ID]


def before_psp_data(path, value, *, mrobe_reversed=False):
    if not mrobe_reversed:
        value = before_mrobe_data(path, value)
    if path == 'data/catalog.json':
        return before_psp_rows(value)
    if path == 'data/collection-history.json':
        value = copy.deepcopy(value)
        batch = {'sourceManifest': 'release-psp-bwfont.json', 'ids': [ID]}
        if batch in value['batches']:
            assert value['batches'][-1] == batch
            value['batches'].pop()
    elif path == 'data/summary.json':
        value = copy.deepcopy(value)
        for key in ('rows', 'nativePngCount', 'standardChineseComplete', 'ordinaryRows', 'ordinaryWithoutAsciiEvaluation'):
            value[key] -= 1
        value['sampleKinds']['standard'] -= 1
        for script in ('简体', '繁体'):
            value['scripts'][script] -= 1
    return value


def before_psp_bytes(path):
    data = before_mrobe_bytes(path)
    if path in ('data/catalog.json', 'data/collection-history.json', 'data/summary.json'):
        return (json.dumps(before_psp_data(path, json.loads(data), mrobe_reversed=True), ensure_ascii=False, indent=2) + '\n').encode()
    if path in ('data/catalog.js', 'data/collection-history.js'):
        prefix, payload = data.decode().split(' = ', 1)
        original = before_psp_data(path.replace('.js', '.json'), json.loads(payload.rstrip().removesuffix(';')), mrobe_reversed=True)
        return (prefix + ' = ' + json.dumps(original, ensure_ascii=False, indent=2) + ';\n').encode()
    if path == 'sitemap.xml':
        text, count = re.subn(r'<url><loc>https://legendtired.github.io/chinese-bitmap-specimens/fonts/' + ID + r'\.html</loc></url>\n', '', data.decode())
        assert count == 1
        return text.encode()
    if path == 'index.html':
        text, count = re.subn(r'<article class="specimen" data-row-id="' + ID + r'">.*?</article>\n', '', data.decode(), flags=re.S)
        assert count == 1 and text.count('>242 个字样</span>') == 1
        return text.replace('>242 个字样</span>', '>241 个字样</span>', 1).encode()
    return data


def before_psp_file_sha(path):
    return hashlib.sha256(before_psp_bytes(path)).hexdigest()
