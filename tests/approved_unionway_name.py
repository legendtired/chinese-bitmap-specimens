from approved_alcatel715 import before_alcatel_file_sha
"""Reverse only the verified UnionWay naming correction for historical audits.

Current rows, changed pages and unchanged PNGs are checked independently by
unionway-name.test.py. Never imported by the site or generator.
"""
from pathlib import Path
import hashlib
import json
ROOT = Path(__file__).resolve().parents[1]
UPDATE = json.loads((ROOT / 'data/correction-unionway-name-20261107.json').read_text())


def before_name_row(row):
    result = dict(row)
    for change in UPDATE['changes']:
        if row['id'] == change['id']:
            field = change['field']
            assert result[field] in (change['before'], change['after']), 'Unreviewed UnionWay naming change'
            result[field] = change['before']
    return result


def before_name_file_sha(path):
    current = before_alcatel_file_sha(path)
    change = UPDATE['changedPublicFiles'].get(path)
    if change:
        assert current == change['after'], 'Unreviewed file change: ' + path
        return change['before']
    return current
