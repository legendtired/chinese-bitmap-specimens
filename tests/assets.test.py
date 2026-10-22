"""Run from any directory: python tests/assets.test.py. No third-party packages."""
from pathlib import Path
import json, struct, re
ROOT = Path(__file__).resolve().parents[1]
rows = json.loads((ROOT / 'data/catalog.json').read_text())
assert rows, 'Empty catalog'
ids = set()
for row in rows:
    assert row['id'] not in ids, 'Duplicate internal ID'
    ids.add(row['id'])
    assert isinstance(row['specimen'], str)
    p = Path(row['specimen'])
    assert not p.is_absolute() and '..' not in p.parts, 'Nonrelative specimen URL'
    image = (ROOT / p).read_bytes()
    assert image[:8] == b'\x89PNG\r\n\x1a\n'
    width, height = struct.unpack('>II', image[16:24])
    assert width > 0 and height > 0
    if 'specimenWidth' in row: assert row['specimenWidth'] == width
    if 'specimenHeight' in row: assert row['specimenHeight'] == height
    for key in ['scripts','styles','uses']: assert isinstance(row[key], list)
    assert (row.get('sourceUrl') and row['sourceUrl'].startswith(('https://','http://'))) or (row.get('sourceType')=='physical-extraction' and row['sourceUrl'] is None and row.get('sourceLabel'))
wordmark = (ROOT / 'assets/wordmark.png').read_bytes()
assert struct.unpack('>II', wordmark[16:24]) == (192, 48), 'Wordmark must retain 2×3 rectangular pixels'
html = (ROOT / 'index.html').read_text()
for relative in re.findall(r'(?:src|href)="([^"#]+)"', html):
    if not relative.startswith(('https:', 'http:')): assert (ROOT / relative).exists(), relative
for p in ROOT.rglob('*'):
    if p.is_file() and 'local-research' not in p.relative_to(ROOT).parts and '.git' not in p.relative_to(ROOT).parts: assert p.suffix.lower() not in ['.ttf','.otf','.bdf','.pcf','.woff','.woff2','.rom','.bin'], p
print(f'Asset tests passed: {len(rows)} PNG specimens, dimensions, schema, relative page assets, no font/ROM files.')
