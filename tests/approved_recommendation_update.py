"""Restore only approved recommendation weights for historical release checks.

Current weights and every original row/file are independently checked by
recommendations-update.test.py and priority.test.cjs. Never used by the site.
"""
from pathlib import Path
import json
import hashlib
ROOT = Path(__file__).resolve().parents[1]
UPDATE = json.loads((ROOT / 'data/update-recommendations-20261107.json').read_text())
CHANGES = {change['id']: change for change in UPDATE['changes']}


def before_recommendations(rows):
    result = []
    for row in rows:
        change = CHANGES.get(row['id'])
        if change:
            assert row['priority'] in (change['before'], change['after']), 'Unreviewed recommendation weight: ' + row['id']
            row = {**row, 'priority': change['before']}
        result.append(row)
    return result


def before_file_fingerprint(path):
    data = (ROOT / path).read_bytes()
    current = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    change = UPDATE.get('updatedHistoricalTestFiles', {}).get(path)
    if change:
        assert current == change['after'], 'Unreviewed historical test change: ' + path
        return change['before']
    return current
