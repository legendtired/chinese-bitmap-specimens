from approved_alcatel715 import before_alcatel_data, before_alcatel_file_sha
from approved_unionway_name import before_name_file_sha
from approved_recommendation_update import before_recommendations
"""Exactly one P802 addition, immutable prior rows/pages/PNGs, and strict source chain."""
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import p802_specimen as p802
import phone_gdr_specimens as phones
from approved_p908_merge import former_catalog


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())


manifest = read('data/release-p802.json')
rows = before_recommendations(before_alcatel_data('data/catalog.json', read('data/catalog.json')))
ident = 'sony_ericsson_p802_12'
assert manifest['addedIds'] == [ident]
assert len(rows) == len({r['id'] for r in rows}) == manifest['totalRows'] == 239
base = former_catalog(rows)
preserved = [r for r in rows if r['id'] in manifest['preservedIds']]
assert len(preserved) == 237 and digest(preserved) == manifest['preservedRowsSha256']
added = [r for r in rows if r['id'] not in manifest['baseIds']]
assert len(base) == manifest['baseRows'] == 239
assert [r['id'] for r in base] == manifest['baseIds']
assert digest(base) == manifest['baseRowsSha256']
assert len(added) == 1 and digest(added) == manifest['addedRowsSha256']
assert digest({r['id']: before_name_file_sha('fonts/' + r['id'] + '.html') for r in preserved}) == manifest['basePagesSha256']
assert digest({r['id']: sha((ROOT / r['specimen']).read_bytes()) for r in base}) == manifest['baseSpecimensSha256']
assert [r['id'] for r in rows if r.get('priority', 0) > 0] == manifest['preservedRecommendedIds']
assert len(manifest['preservedRecommendedIds']) == 13
for path, expected in manifest['preservedFilesSha256'].items():
    assert before_alcatel_file_sha(path) == expected, path
row = added[0]
assert row['id'] == ident and row['priority'] == 0 and row['sourceIndex'] == 276
assert (row['width'], row['height'], row['cellWidth'], row['cellHeight']) == (12, 14, 12, 14)
assert (row['inkWidth'], row['inkHeight']) == (11, 12)
assert (row['specimenWidth'], row['specimenHeight']) == (300, 40)
assert row['text'] == p802.CHINESE and row['asciiText'] == p802.ASCII
assert row['missing'] == row['hanMissing'] == row['asciiMissing'] == []
assert row['asciiOrigin'] == 'native' and row['nativeEvidence']['big5Han'] == 6998
assert row['nativeEvidence']['big5ExpectedHan'] == 13061
assert sha((ROOT / row['specimen']).read_bytes()) == row['specimenSha256']
assert before_alcatel_data('data/collection-history.json', read('data/collection-history.json'))['batches'][-1] == {'sourceManifest': 'release-p802.json', 'ids': [ident]}
assert not set(r['id'] for r in rows) & set(read('data/curation.json')['removedIds'])
summary = before_alcatel_data('data/summary.json', read('data/summary.json'))
assert (summary['rows'], summary['nativePngCount'], summary['referenceRows']) == (239, 238, 1)
for key in ['standardAsciiComplete', 'ordinaryAsciiRows', 'standardChineseComplete']:
    assert summary[key] == manifest['previousSummary'][key]
assert not summary['glyphDataIncluded'] and summary['fontFilesIncluded'] == 0
audit = read('data/p802-decode-audit.json')
assert audit['status'] == 'passed' and audit['mappedGlyphsCompared'] == 10406
assert audit['binaryPixelValuesCompared'] == 1278322 and audit['binaryPixelMismatches'] == 0
assert audit['sample']['sha256'] == row['specimenSha256'] and audit['sample']['pixelMismatches'] == 0
assert audit['scriptSha256'] == sha((ROOT / 'scripts/p802_specimen.py').read_bytes())
assert audit['sharedDecoderSha256'] == sha((ROOT / 'scripts/phone_gdr_specimens.py').read_bytes())
coverage = read('data/p802-coverage.json')
assert coverage['mappedCharacters'] == 10406 and coverage['nonblankCjkU3400U9fff'] == 9587
assert coverage['gb2312']['nonblankHan'] == 6763 and coverage['big5']['nonblankHan'] == 6998
assert coverage['fixedSampleMissing'] == [] and coverage['hanAdvances'] == {'12': 9587}
dedup = read('data/p802-dedup.json')
assert dedup['historicalIndexSummary']['eligible_records'] == 202
for scope in ['common_han', 'gb2312_han']:
    result = dedup['historicalComparisons'][scope]
    assert result['checkedRecords'] == len(result['results']) == 202 and result['notReadyCount'] == 0
assert dedup['fixedSampleSummary']['nativePngsChecked'] == 238
assert dedup['fixedSampleSummary']['specimensWithExactHits'] == 0
assert dedup['fixedSampleSummary']['withdrawnSourcesChecked'] == 23
assert dedup['sunGbkSupplement']['sun12_gb2312']['exact_cropped'] == 52
assert dedup['sunGbkSupplement']['sun12_gb2312']['translation_allowed_dice_at_least']['0.95'] == 265
for path in ROOT.glob('data/p802-*.json'):
    text = path.read_text()
    assert '/workspace/' not in text and '/download/' not in text
    assert not any('"' + key + '"' in text for key in ['glyphs', 'bitmaps', 'rows', 'source_cache', 'source_zip', 'source_path'])

with tempfile.TemporaryDirectory() as tmp:
    bad = Path(tmp) / 'bad'
    bad.write_bytes(b'not a font')
    for container in ['gdr', 'pd2', 'zip']:
        try:
            p802.source_bytes(bad, container)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + container)
    try:
        p802.decode(bad.read_bytes())
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid GDR accepted')
    assert 'p802' not in phones.SOURCES
    out = Path(tmp) / 'exists'
    out.mkdir()
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/p802_specimen.py'), str(bad), '--output', str(out)], capture_output=True, text=True)
    assert result.returncode != 0 and 'Output must not already exist' in result.stderr

source_runs = []
for container, variable in [('gdr', 'P802_GDR'), ('pd2', 'P802_PD2'), ('zip', 'P802_ZIP')]:
    if not os.environ.get(variable):
        print(variable + ': private-source integration not run; input not supplied.')
        continue
    data = p802.source_bytes(Path(os.environ[variable]), container)
    face = p802.decode(data)
    assert json.loads(json.dumps(p802.coverage(face))) == coverage
    stream = io.BytesIO()
    p802.render(face).save(stream, format='PNG')
    assert stream.getvalue() == (ROOT / row['specimen']).read_bytes()
    mutated = data[:-1] + bytes([data[-1] ^ 1])
    try:
        p802.decode(mutated)
    except ValueError:
        pass
    else:
        raise AssertionError('Mutated GDR accepted')
    assert 'p802' not in phones.SOURCES
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / 'out'
        subprocess.run([sys.executable, str(ROOT / 'scripts/p802_specimen.py'), os.environ[variable], '--container', container, '--output', str(output)], check=True)
        assert set(p.name for p in output.iterdir()) == {ident + '.png', 'coverage.json'}
        assert (output / (ident + '.png')).read_bytes() == (ROOT / row['specimen']).read_bytes()
    source_runs.append(container)
print('P802 exact input/render checks:', source_runs)
print('P802: one approved addition; 237 unchanged rows/pages, all prior PNGs and 13 recommendations preserved; P908 merged into Sun14.')
