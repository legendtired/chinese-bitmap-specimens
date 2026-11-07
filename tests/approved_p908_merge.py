"""Restore explicit approved before-values for historical audits, never for the site."""
from approved_unionway_name import before_name_file_sha
from pathlib import Path
import hashlib
import json
ROOT = Path(__file__).resolve().parents[1]
MERGE = json.loads((ROOT / 'data/merge-p908-sun14.json').read_text())


def restore_sun(rows):
    result = []
    for row in rows:
        if row['id'] == MERGE['targetId']:
            assert row in [MERGE['afterSunRow'], MERGE['beforeSunRow']], 'Unreviewed Sun metadata change'
            row = MERGE['beforeSunRow']
        result.append(row)
    return result


def former_catalog(rows):
    rows = restore_sun([r for r in rows if r['id'] != 'sony_ericsson_p802_12'])
    assert not any(r['id'] == 'sony_ericsson_p908_14' for r in rows)
    before = MERGE['formerStandaloneRow']
    insert = next(i for i, r in enumerate(rows) if r['id'] == 'nokia_9210c_15')
    rows.insert(insert, before)
    return rows


def historical_file_sha(path):
    current = before_name_file_sha(path)
    if path in MERGE['afterFilesSha256']:
        assert current == MERGE['afterFilesSha256'][path], 'Unreviewed file change: ' + path
        return MERGE['beforeFilesSha256'][path]
    return current
