"""Restore only the explicitly reviewed export-guide change for historical hashes."""
from approved_unionway_name import before_name_row
from pathlib import Path
import json

PATCHES = json.loads((Path(__file__).parent / 'fixtures/export-guides.json').read_text())
BEFORE = {patch['id']: patch['before'] for patch in PATCHES}


def before_export_guides(row):
    result = before_name_row(row)
    if row['id'] in BEFORE:
        result['acquisitionGuide'] = BEFORE[row['id']]
    return result
