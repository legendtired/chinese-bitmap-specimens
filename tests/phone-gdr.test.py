"""Exactly four approved phone additions; preserved baseline, native previews and bounds."""
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
from phone_gdr_specimens import SOURCES, ASCII, CHINESE, coverage, decode, render, source_bytes

def read(path):
    return json.loads((ROOT / path).read_text())

def sha(data):
    return hashlib.sha256(data).hexdigest()

def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())

manifest = read('data/release-phone-gdr.json')
rows = read('data/catalog.json')
ids = ['sony_ericsson_p908_14', 'nokia_9210c_15', 'nokia_9210c_17', 'nokia_9210c_19']
assert manifest['addedIds'] == ids
assert len(rows) == len({r['id'] for r in rows}) == 239
base = [r for r in rows if r['id'] in manifest['baseIds']]
added = [r for r in rows if r['id'] in ids]
assert len(base) == 235 and digest(base) == manifest['baseRowsSha256']
assert len(added) == 4 and digest(added) == manifest['addedRowsSha256']
assert [r['id'] for r in rows if r.get('priority', 0) > 0] == manifest['preservedRecommendedIds']
assert len(manifest['preservedRecommendedIds']) == 13
assert digest({r['id']: sha((ROOT / 'fonts' / (r['id'] + '.html')).read_bytes()) for r in base}) == manifest['basePagesSha256']
for path, expected in manifest['preservedFilesSha256'].items():
    assert sha((ROOT / path).read_bytes()) == expected, path
assert len({r['sourceIndex'] for r in rows if r.get('sourceIndex') is not None}) == len([r for r in rows if r.get('sourceIndex') is not None])
for row in rows:
    assert sha((ROOT / row['specimen']).read_bytes()) == row['specimenSha256'], row['id']
for row, width, height, ink in zip(added, [14, 16, 18, 20], [16, 16, 18, 20], [14, 15, 17, 19]):
    assert (row['width'], row['height'], row['cellWidth'], row['cellHeight']) == (width, height, width, height)
    assert row['inkHeight'] == ink and row['priority'] == 0
    assert row['text'] == CHINESE and row['asciiText'] == ASCII
    assert row['scripts'] == ['简体', '繁体'] and row['asciiOrigin'] == 'native'
    assert row['missing'] == row['hanMissing'] == row['asciiMissing'] == []
    assert row['nativeEvidence']['gb2312Han'] == 6763 and row['nativeEvidence']['big5Han'] == 13061
    assert row['nativeEvidence']['printableAscii'] == 95
    assert (ROOT / ('fonts/' + row['id'] + '.html')).exists()
assert not set(ids) & set(read('data/curation.json')['removedIds'])
assert read('data/collection-history.json')['batches'][-1] == {'sourceManifest': 'release-phone-gdr.json', 'ids': ids}
summary = read('data/summary.json')
assert (summary['rows'], summary['nativePngCount'], summary['referenceRows']) == (239, 238, 1)
for key in ['standardAsciiComplete', 'ordinaryAsciiRows', 'standardChineseComplete']:
    assert summary[key] == manifest['previousSummary'][key] + 4
assert summary['fontFilesIncluded'] == 0 and summary['glyphDataIncluded'] is False
audit = read('data/phone-gdr-sample-audit.json')
assert audit['source_commit'] == manifest['fixedSampleAuditBaseCommit'] and audit['tested_native_count'] == 233
assert len(audit['positive_controls']) == 4
assert audit['integrationSupplement']['baseCommit'] == manifest['baseCommit']
assert all(x['testedCharacters'] == 10 and x['exactPatternHits'] == 0 for x in audit['integrationSupplement']['checks'])
decoded_audit = read('data/phone-gdr-decode-audit.json')
assert decoded_audit['status'] == 'passed' and decoded_audit['glyphsCompared'] == 83616
assert decoded_audit['pixelsCompared'] == 21498570 and all(x['mismatches'] == 0 for x in decoded_audit['layers'])
assert decoded_audit['scriptSha256'] == sha((ROOT / 'scripts/phone_gdr_specimens.py').read_bytes())
dedup = read('data/phone-gdr-dedup.json')['nokia9210cNamedResults']
assert len(dedup) == 3 and all(len(layer['results']) == 47 for layer in dedup)
for layer in dedup:
    assert sum(x['GB2312']['common'] == 6763 for x in layer['results']) == 45
assert max(x['GB2312']['exact'] for x in dedup[0]['results']) == 6
assert all(x['GB2312']['exact'] == 0 for layer in dedup[1:] for x in layer['results'])

with tempfile.TemporaryDirectory() as tmp:
    bad = Path(tmp) / 'bad.gdr'
    bad.write_bytes(b'not a font')
    for device in SOURCES:
        for function in [lambda: decode(bad.read_bytes(), device), lambda: source_bytes(bad, device)]:
            try:
                function()
            except ValueError:
                pass
            else:
                raise AssertionError('Unverified input accepted')
    out = Path(tmp) / 'exists'
    out.mkdir()
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/phone_gdr_specimens.py'), str(bad), '--device', 'p908', '--output', str(out)], capture_output=True, text=True)
    assert result.returncode != 0 and 'Output must not already exist' in result.stderr
for device, variable in [('p908', 'P908_GDR'), ('9210c', 'NOKIA9210C_GDR')]:
    if os.environ.get(variable):
        data = source_bytes(Path(os.environ[variable]), device)
        decoded = decode(data, device)
        reports = {x['id']: x for x in read('data/phone-gdr-coverage.json')}
        for face in decoded:
            # JSON normalizes integer object keys in the advance histogram.
            assert json.loads(json.dumps(coverage(face))) == reports[face['id']]
            image = render(face)
            stream = io.BytesIO()
            image.save(stream, format='PNG')
            row = next(r for r in added if r['id'] == face['id'])
            assert stream.getvalue() == (ROOT / row['specimen']).read_bytes()
        mutated = bytearray(data)
        mutated[-1] ^= 1
        try:
            decode(bytes(mutated), device)
        except ValueError:
            pass
        else:
            raise AssertionError('Mutated source accepted')
        print(device + ': exact private-source decode, coverage, PNG and mutation rejection passed.')
    else:
        print(device + ': private-source integration not run; input not supplied.')
print('Phone GDR: exactly four additions; 235 prior rows/PNGs, 13 recommendations and exclusions preserved.')
