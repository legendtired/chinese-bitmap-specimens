"""Reverse only the approved MR-100 addition for historical release audits.
Never imported by the site or builder. mrobe-mr100.test.py locks retained rows/pixels/pages.
"""
from pathlib import Path
import copy
import hashlib
import json
import re
ROOT = Path(__file__).resolve().parents[1]
ID = 'olympus_mrobe_mr100_12'


def before_mrobe_rows(rows):
    return [r for r in rows if r['id'] != ID]


def before_mrobe_data(path, value):
    if path == 'data/catalog.json':
        return before_mrobe_rows(value)
    if path == 'data/collection-history.json':
        value = copy.deepcopy(value)
        batch = {'sourceManifest': 'release-mrobe-mr100.json', 'ids': [ID]}
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


def before_mrobe_bytes(path):
    data = (ROOT / path).read_bytes()
    if path == 'scripts/generate_static.py':
        # The release manifests predate content-versioned scripts. Reverse only
        # this exact reviewed builder change; unknown edits still fail closed.
        assert hashlib.sha256(data).hexdigest() == 'd2f6bf5d0a92e52d277f955b6533b960822852bf32686490c4d6db21b33d48d1'
        text = data.decode()
        text = text.replace('import hashlib,json,re,html,subprocess,sys\nfrom html.parser import HTMLParser', 'import json,re,html,subprocess,sys', 1)
        start = text.index('MANAGED_SCRIPTS=')
        end = text.index('def main():', start)
        text = text[:start] + text[end:]
        start = text.index(' # Validate all managed references before writing any generated output.\n')
        end = text.index(" folder=ROOT/'fonts'", start)
        text = text[:start] + text[end:]
        text = text.replace(" for name in MANAGED_SCRIPTS[:2]:(ROOT/name).write_bytes(assets[name])", " (ROOT/'data/catalog.js').write_text('window.FONT_CATALOG = '+json.dumps(rows,ensure_ascii=False,indent=2)+';\\n')\n history=json.loads((ROOT/'data/collection-history.json').read_text())\n (ROOT/'data/collection-history.js').write_text('window.FONT_COLLECTION_HISTORY = '+json.dumps(history,ensure_ascii=False,indent=2)+';\\n')", 1)
        text = text.replace(" if '<!-- STATIC_CATALOG_START -->' not in h:", " p=ROOT/'index.html';h=p.read_text()\n if '<!-- STATIC_CATALOG_START -->' not in h:", 1)
        data = text.encode()
        assert hashlib.sha256(data).hexdigest() == '7d4ebcc6e622d103cdbf2b7b54ff08df1aa98fb200f0e5d3a11c6ea6a57dc6a4'
        return data
    if path in ('data/catalog.json', 'data/collection-history.json', 'data/summary.json'):
        return (json.dumps(before_mrobe_data(path, json.loads(data)), ensure_ascii=False, indent=2) + '\n').encode()
    if path in ('data/catalog.js', 'data/collection-history.js'):
        prefix, payload = data.decode().split(' = ', 1)
        original = before_mrobe_data(path.replace('.js', '.json'), json.loads(payload.rstrip().removesuffix(';')))
        return (prefix + ' = ' + json.dumps(original, ensure_ascii=False, indent=2) + ';\n').encode()
    if path == 'sitemap.xml':
        text, count = re.subn(r'<url><loc>https://legendtired.github.io/chinese-bitmap-specimens/fonts/' + ID + r'\.html</loc></url>\n', '', data.decode())
        assert count == 1
        return text.encode()
    if path == 'index.html':
        # Restore only the three verified content versions for historical SHA audits.
        # The current script bytes and versions are checked independently.
        text = data.decode()
        for asset in ('data/catalog.js', 'data/collection-history.js', 'app.js'):
            version = hashlib.sha256((ROOT / asset).read_bytes()).hexdigest()[:16]
            current = f'src="{asset}?v={version}"'
            assert text.count(current) == 1, asset
            text = text.replace(current, f'src="{asset}"', 1)
        text, count = re.subn(r'<article class="specimen" data-row-id="' + ID + r'">.*?</article>\n', '', text, flags=re.S)
        assert count == 1 and text.count('>243 个字样</span>') == 1
        return text.replace('>243 个字样</span>', '>242 个字样</span>', 1).encode()
    return data


def before_mrobe_file_sha(path):
    return hashlib.sha256(before_mrobe_bytes(path)).hexdigest()
