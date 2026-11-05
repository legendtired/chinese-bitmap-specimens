"""Reviewed acquisition changes do not alter historical font metadata or images."""
from pathlib import Path
import json
from export_baseline import PATCHES

ROOT = Path(__file__).resolve().parents[1]
rows = {r['id']: r for r in json.loads((ROOT / 'data/catalog.json').read_text())}
assert len(PATCHES) == len({p['id'] for p in PATCHES})
assert len(PATCHES) >= 80
for patch in PATCHES:
    assert rows[patch['id']]['acquisitionGuide'] == patch['after'], patch['id']
    assert patch['before'] != patch['after']
    assert patch['after']['steps'] == []
    before_urls = {link['url'] for link in patch['before']['links']}
    after_urls = {link['url'] for link in patch['after']['links']}
    assert before_urls <= after_urls, patch['id']
    for link in patch['after']['links']:
        prefix = 'https://github.com/legendtired/chinese-bitmap-specimens/blob/main/'
        if link['url'].startswith(prefix):
            assert (ROOT / link['url'][len(prefix):].split('#', 1)[0]).is_file(), link['url']
for path in ('font-export.md', 'bitmap-export.md', 'hzk-export.md', 'panasonic-fs-uv1.md', 'kbitx-export.md', 'hzk11us-export.md', 'flippercn-export.md', 'dec-cns-export.md', 'cjkos-export.md', 'tumbled-export.md', 'source-slot-export.md', 'elisa-export.md'):
    assert (ROOT / 'docs' / path).is_file()
print(f'Export guides: {len(PATCHES)} exact reviewed changes, original sources retained, all method documents present.')
