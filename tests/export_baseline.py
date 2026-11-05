"""Restore only the explicitly reviewed export-guide change for historical hashes."""
from pathlib import Path
import json

PATCHES = json.loads((Path(__file__).parent / 'fixtures/export-guides.json').read_text())
BEFORE = {patch['id']: patch['before'] for patch in PATCHES}


def before_export_guides(row):
    result = dict(row)
    if row['id'] in BEFORE:
        result['acquisitionGuide'] = BEFORE[row['id']]
    return result
