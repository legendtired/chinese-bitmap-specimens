"""Reverse only the approved OT-715 and MS Ming 14 additions for historical regression audits.

The current entry and all 239 retained rows/pixels are independently checked by
alcatel715.test.py and msming14.test.py. This helper is never imported by the site or generator.
"""
from approved_psp_bwfont import before_psp_rows, before_psp_data, before_psp_bytes
from pathlib import Path
import copy
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
IDS = ('alcatel_ot715_13x14', 'ms_ming_14')


def before_alcatel_rows(rows):
    return [row for row in before_psp_rows(rows) if row['id'] not in IDS]


def before_alcatel_data(path, value, *, psp_reversed=False):
    if not psp_reversed:
        value = before_psp_data(path, value)
    if path == 'data/catalog.json':
        return before_alcatel_rows(value)
    if path == 'data/collection-history.json':
        value = copy.deepcopy(value)
        batch = {'sourceManifest': 'release-alcatel715.json', 'ids': list(IDS)}
        assert value['batches'][-1] == batch
        value['batches'].pop()
    elif path == 'data/summary.json':
        value = copy.deepcopy(value)
        for key in ('rows', 'nativePngCount', 'standardChineseComplete', 'ordinaryRows'):
            value[key] -= 2
        # Only OT-715 adds native ASCII; MS Ming's selected bitmap has none.
        for key in ('standardAsciiComplete', 'ordinaryAsciiRows', 'ordinaryWithoutAsciiEvaluation'):
            value[key] -= 1
        value['sampleKinds']['standard'] -= 2
        for script in ('简体', '繁体'):
            value['scripts'][script] -= 2
    return value


def before_alcatel_bytes(path):
    data = before_psp_bytes(path)
    if path in ('data/catalog.json', 'data/collection-history.json', 'data/summary.json'):
        return (json.dumps(before_alcatel_data(path, json.loads(data), psp_reversed=True), ensure_ascii=False, indent=2) + '\n').encode()
    if path in ('data/catalog.js', 'data/collection-history.js'):
        prefix, payload = data.decode().split(' = ', 1)
        original = before_alcatel_data(path.replace('.js', '.json'), json.loads(payload.rstrip().removesuffix(';')), psp_reversed=True)
        return (prefix + ' = ' + json.dumps(original, ensure_ascii=False, indent=2) + ';\n').encode()
    if path == 'sitemap.xml':
        text = data.decode()
        for ident in IDS:
            text, count = re.subn(r'<url><loc>https://legendtired.github.io/chinese-bitmap-specimens/fonts/' + ident + r'\.html</loc></url>\n', '', text)
            assert count == 1
        return text.encode()
    if path == 'index.html':
        text = data.decode()
        for ident in IDS:
            text, count = re.subn(r'<article class="specimen" data-row-id="' + ident + r'">.*?</article>\n', '', text, flags=re.S)
            assert count == 1
        assert text.count('>241 个字样</span>') == 1
        return text.replace('>241 个字样</span>', '>239 个字样</span>', 1).encode()
    return data


def before_alcatel_file_sha(path):
    return hashlib.sha256(before_alcatel_bytes(path)).hexdigest()
