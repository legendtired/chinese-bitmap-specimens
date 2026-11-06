"""Restore only approved changed rows when checking historical release hashes."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
u=json.loads((R/'data/update-native-latin-20261106.json').read_text())
BEFORE={r['id']:r for r in u['before']}
AFTER={r['id']:r for r in u['after']}
def historical_rows(rows):
    for r in rows:
        if r['id'] in AFTER:
            assert r==AFTER[r['id']], 'Unreviewed change to supplemented row'
    return [BEFORE.get(r['id'],r) for r in rows]
