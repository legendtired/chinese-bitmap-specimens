"""Restore only approved changed rows when checking historical release hashes."""
from approved_unionway_name import before_name_row
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
u=json.loads((R/'data/update-native-latin-20261106.json').read_text())
BEFORE={r['id']:r for r in u['before']}
AFTER={r['id']:r for r in u['after']}
palm=json.loads((R/'data/update-palm-latin-20261106.json').read_text())
from approved_p908_merge import restore_sun
def historical_rows(rows):
    rows = restore_sun([before_name_row(row) for row in rows])
    for r in rows:
        if r['id']==palm['after']['id']:
            assert r==palm['after'], 'Unreviewed change to Palm supplemented row'
    rows=[palm['before'] if r['id']==palm['after']['id'] else r for r in rows]
    for r in rows:
        if r['id'] in AFTER:
            assert r==AFTER[r['id']], 'Unreviewed change to supplemented row'
    return [BEFORE.get(r['id'],r) for r in rows]
