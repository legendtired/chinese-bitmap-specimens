from approved_simsun import before_simsun_bytes
"""Approved metadata-only Sun14 variant merge and legacy favorites compatibility."""
import hashlib
import json
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
read = lambda path: json.loads((ROOT / path).read_text())
merge = read('data/merge-p908-sun14.json')
rows = read('data/catalog.json')
by_id = {r['id']: r for r in rows}
assert 'sony_ericsson_p908_14' not in by_id
assert by_id['sun_gbk_song_14'] == merge['afterSunRow']
old, new = merge['beforeSunRow'], merge['afterSunRow']
for key, value in old.items():
    if key == 'acquisitionGuide':
        for field, original in value.items():
            if field == 'links':
                assert new[key][field][:-1] == original
            else:
                assert new[key][field] == original
    else:
        assert new[key] == value, key
assert set(new) - set(old) == {'relatedSources'}
assert len(new['relatedSources']) == 1
variant = new['relatedSources'][0]
assert variant['id'] == 'sony_ericsson_p908_14'
for text in ['35.591%', '36.414%', '不证明', '3299', '3814', '4277']:
    assert text in variant['comparison']
assert '16高' in variant['coverageNote'] and '13061' in variant['coverageNote']
assert merge['comparison']['sun14_gb2312']['exact_cropped'] == 2407
assert merge['comparison']['sun14_all_common_basic_han']['exact_cropped'] == 5740
assert read('data/curation.json')['merged']['sony_ericsson_p908_14'] == 'sun_gbk_song_14'
assert not (ROOT / 'fonts/sony_ericsson_p908_14.html').exists()
assert 'sony_ericsson_p908_14.html' not in (ROOT / 'sitemap.xml').read_text()
assert 'data-row-id="sony_ericsson_p908_14"' not in (ROOT / 'index.html').read_text()
assert hashlib.sha256((ROOT / merge['formerStandaloneRow']['specimen']).read_bytes()).hexdigest() == merge['preservedP908SampleSha256']
for path, expected in merge['afterFilesSha256'].items():
    assert hashlib.sha256(before_simsun_bytes(path)).hexdigest() == expected
assert read('data/summary.json')['curation']['mergedSampleEquivalent'] == 4
assert len(read('data/curation.json')['removedIds']) == 34
assert not any(id.startswith('sun_gb2312_') for id in by_id)
script = """
const assert = require('node:assert/strict');
const fs = require('node:fs');
const api = require('./app.js'), rows = require('./data/catalog.json');
const ids = new Set(rows.map(r => r.id)), aliases = require('./data/curation.json').merged;
const store = api.createFavoriteStore(() => ({getItem: () => JSON.stringify(['sony_ericsson_p908_14','sun_gbk_song_14','nokia_9210c_15']), setItem() {}}), ids, aliases);
assert.deepEqual(store.ids, ['sun_gbk_song_14','nokia_9210c_15']);
assert(fs.readFileSync('app.js', 'utf8').includes("sony_ericsson_p908_14: 'sun_gbk_song_14'"));
assert(!api.filterCatalog(rows, {}).some(r => r.id === 'sony_ericsson_p908_14'));
"""
subprocess.run(['node', '-e', script], cwd=ROOT, check=True)
print('P908 merge: qualified Sun14 source note only, original pixels/metrics intact, old favorite remapped, no independent row/page.')
