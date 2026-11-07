"""Exactly three recommendation changes; all 239 rows otherwise remain byte-equivalent."""
from approved_unionway_name import before_name_row, before_name_file_sha
from pathlib import Path
import hashlib
import json
from approved_recommendation_update import before_recommendations

ROOT = Path(__file__).resolve().parents[1]
read = lambda path: json.loads((ROOT / path).read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()
digest = lambda data: sha(json.dumps(data, ensure_ascii=False, sort_keys=True).encode())
update = read('data/update-recommendations-20261107.json')
rows = [before_name_row(row) for row in read('data/catalog.json')]
before = before_recommendations(rows)
assert update['baseCommit'] == '015392f1c913614801dd1f85405fe8a78405b57f'
assert len(rows) == len({r['id'] for r in rows}) == update['totalRows'] == 239
expected = [
    {'id': 'nokia_dct3_1999', 'before': 0, 'after': 5},
    {'id': 'wqx_pc505_14x15', 'before': 0, 'after': 4},
    {'id': 'samsung_r208_16', 'before': 0, 'after': 3},
]
assert update['changes'] == expected
assert digest(before) == update['beforeRowsSha256']
assert digest(rows) == update['afterRowsSha256']
assert [r['id'] for r, old in zip(rows, before) if r != old] == [c['id'] for c in expected]
for new, old in zip(rows, before):
    assert {k: v for k, v in new.items() if k != 'priority'} == {k: v for k, v in old.items() if k != 'priority'}
for change in expected:
    assert next(r['priority'] for r in rows if r['id'] == change['id']) == change['after']
recommended = lambda data: [r['id'] for r in sorted(data, key=lambda r: -r['priority']) if r['priority'] > 0]
assert recommended(before) == update['beforeRecommendedIds']
assert recommended(rows) == update['afterRecommendedIds'] == update['beforeRecommendedIds'] + [c['id'] for c in expected]
assert len(update['beforeRecommendedIds']) == 13 and len(update['afterRecommendedIds']) == 16
assert digest({r['id']: before_name_file_sha('fonts/' + r['id'] + '.html') for r in rows}) == update['preservedPagesSha256']
assert digest({r['id']: sha((ROOT / r['specimen']).read_bytes()) for r in rows}) == update['preservedSpecimensSha256']
for path, expected_sha in update['preservedFilesSha256'].items():
    assert sha((ROOT / path).read_bytes()) == expected_sha, path
assert set(update['updatedHistoricalTestFiles']) == {'tests/pc505.test.py'}
for path, change in update['updatedHistoricalTestFiles'].items():
    data = (ROOT / path).read_bytes()
    assert {'bytes': len(data), 'sha256': sha(data)} == change['after']
    original = next(item for item in read('data/pc505-public-files.json') if item['path'] == path)
    assert change['before'] == {'bytes': original['bytes'], 'sha256': original['sha256']}
assert next(r['priority'] for r in rows if r['id'] == 'casio_xda10000_24') == 0
assert next(r['id'] for r in rows if r['id'] == 'sony_ericsson_p802_12')
assert 'sony_ericsson_p908_14' not in {r['id'] for r in rows}
print('Recommendation update: exactly Nokia DCT3/PC505/R208 added after original 13; all 239 rows otherwise unchanged, all pages/PNGs/history/curation preserved.')
