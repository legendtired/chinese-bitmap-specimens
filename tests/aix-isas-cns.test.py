from approved_alcatel715 import before_alcatel_data
from approved_recommendation_update import before_recommendations
from approved_p908_merge import restore_sun, historical_file_sha
"""One approved traditional AIX addition with exact immutable baseline and redraw."""
import hashlib
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parents[1]
def read(path): return json.loads((R / path).read_text())
def sha(blob): return hashlib.sha256(blob).hexdigest()
def digest(value): return sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())

rows = before_recommendations(before_alcatel_data('data/catalog.json', read('data/catalog.json')))
m = read('data/release-aix-isas-cns.json')
base = [r for r in rows if r['id'] in m['baseIds']]
added = [r for r in rows if r['id'] in m['addedIds']]
assert len(rows) == len({r['id'] for r in rows}) == 239
assert m['totalRows'] == 235
assert len(base) == m['baseRows'] == 234 and digest(restore_sun(base)) == m['baseRowsSha256']
assert [r['id'] for r in base] == m['baseIds']
assert digest({r['id']: historical_file_sha('fonts/' + r['id'] + '.html') for r in base}) == m['basePagesSha256']
for path, expected in m['preservedFilesSha256'].items():
    assert historical_file_sha(path) == expected, path
assert len(added) == 1 and digest(added) == m['addedRowsSha256']
assert [r['id'] for r in rows if r.get('priority', 0) > 0] == m['preservedRecommendedIds']
assert len(m['preservedRecommendedIds']) == 13
for r in rows:
    assert sha((R / r['specimen']).read_bytes()) == r['specimenSha256'], r['id']
r = added[0]
assert r['id'] == 'aix_isas_cns_24' and r['priority'] == 0 and r['sourceIndex'] == 271
assert (r['width'], r['height'], r['cellWidth'], r['cellHeight']) == (26, 27, 26, 27)
assert r['heightBasis'] == 'han-ink-grid' and r['designHeight'] == 24
assert r['inkWidth'] == r['inkHeight'] == 24
assert r['asciiOrigin'] == 'native' and r['missing'] == r['hanMissing'] == r['asciiMissing'] == []
assert all(c not in r['text'] + r['asciiText'] for c in '[]')
assert struct.unpack_from('>II', (R / r['specimen']).read_bytes(), 16) == (359, 66)
assert r['nativeEvidence']['hanUnicodeCount'] == 13061
assert r['nativeEvidence']['asciiWidth'] == 13
assert (r['nativeEvidence']['fontAscent'], r['nativeEvidence']['fontDescent']) == (26, 1)
assert {'sourceManifest': 'release-aix-isas-cns.json', 'ids': m['addedIds']} in before_alcatel_data('data/collection-history.json', read('data/collection-history.json'))['batches']
s = before_alcatel_data('data/summary.json', read('data/summary.json'))
assert s['rows'] == 239 and s['nativePngCount'] == 238
for key in ['standardAsciiComplete', 'ordinaryAsciiRows', 'standardChineseComplete']:
    assert s[key] == m['previousSummary'][key] + 5
for key in ['partialAscii', 'ordinaryWithoutAsciiEvaluation', 'referenceRows', 'variableGridRows']:
    assert s[key] == m['previousSummary'][key]
assert s['fontFilesIncluded'] == 0 and s['glyphDataIncluded'] is False
assert not set(m['addedIds']) & set(read('data/curation.json')['removedIds'])
page = (R / 'fonts/aix_isas_cns_24.html').read_text()
assert '24px字面 · 存储 26×27' in page and '实物提取样张' not in page
assert 'Roman' in page and '32.57%' in page

a = read('data/aix-isas-cns-independent-audit.json')
assert a['status'] == 'passed' and a['totalGlyphsCompared'] == 13642 and a['totalSourcePixelsCompared'] == 9532107
assert a['nonblankHanUnion'] == 13061 and not a['hanPlaneOverlap']
assert a['big5HanCovered'] == 13060 and a['big5HanCount'] == 13061
assert a['missingBig5Han'] == ['U+5F5D 彝'] and a['extraHanOutsideBig5'] == ['U+5F5E 彞']
assert [f['nonblankHan'] for f in a['files']] == [5411, 7650, 0]
assert all(f['mismatchingPixels'] == 0 for f in a['files'])
assert {c['code'] for c in a['conflictingDuplicateUnicode']} == {'U+005B', 'U+005D'}
assert a['hanInkMeasurement']['cns1ucsMax'] == a['hanInkMeasurement']['cns2ucsMax'] == [24, 24]
assert a['sample']['sha256'] == r['specimenSha256']
d = read('data/aix-isas-cns-dedup.json')
# Public dedup evidence is deliberately aggregate-only, not the private inventory.
assert set(d) == {'scope', 'method', 'nonblankHan', 'historicalReferenceSummary',
                  'namedComparisons', 'isasRelationship', 'mappingSupplement',
                  'sampleOnlySummary', 'limits'}
assert d['nonblankHan'] == {'plane1': 5411, 'plane2': 7650, 'union': 13061}
h = d['historicalReferenceSummary']
assert h == {'referencesChecked': 221, 'referencesWithMappedHan': 211,
             'referencesWithoutMappedHan': 10, 'currentCatalogCount': 234,
             'currentCatalogEntriesAbsentFromArchive': 49}
named = d['namedComparisons']
assert len(named) == 5
assert [x['id'] for x in named] == ['isas_song_24', 'eten_taipei_24', 'hpux_sung_24',
                                  'dec_sung_cns11643_24', 'dec_sung_cns11643_32']
assert [x['commonHan'] for x in named] == [4382, 13060, 13061, 13061, 13061]
assert [x['croppedEqual'] for x in named] == [1427, 1, 1, 1, 0]
assert [x['wholeEqual'] for x in named] == [0, 0, None, 0, 0]
assert all(set(x) <= {'id', 'name', 'commonHan', 'wholeEqual', 'croppedEqual', 'note'} for x in named)
assert d['isasRelationship']['sharedHan'] == 4382
assert d['isasRelationship']['croppedEqual'] == 1427
assert d['isasRelationship']['croppedEqualPercent'] == 32.57
assert d['isasRelationship']['outsideSimplifiedReferenceHan'] == 8679
assert d['mappingSupplement']['decMappedHanPerSize'] == 13064
assert d['mappingSupplement']['decUnmappedSourceSlotsPerSize'] == 219
p = d['sampleOnlySummary']
assert p['currentCatalogCount'] == 234 and p['publicNativeSpecimensChecked'] == 233
assert (p['referenceImagesExcluded'], p['withdrawnImagesAvailable']) == (1, 0)
assert (p['specimensWithAnyMatchedHan'], p['specimensWithoutMatchedHan']) == (5, 228)
assert (p['matchedHanOccurrences'], p['distinctMatchedHan'], p['maximumMatchedHanPerSpecimen']) == (7, 3, 3)
assert p['wholeSentenceMatches'] == 0
assert all(not isinstance(value, (list, dict)) for value in p.values())
# Prevent restoration of exhaustive IDs, individual PNG records or coordinates.
def check_aggregate(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in {'comparisons', 'results', 'positions', 'coordinates',
                               'currentCatalogAbsentFromArchive', 'matchedHan',
                               'testedHan', 'unavailableHan', 'recipeSha256'}, key
            check_aggregate(child, path + (key,))
    elif isinstance(value, list):
        assert path == ('namedComparisons',), path
        for child in value:
            check_aggregate(child, path)
check_aggregate(d)
for filename in ['aix-isas-cns-sources.json', 'aix-isas-cns-independent-audit.json', 'aix-isas-cns-dedup.json']:
    public = (R / 'data' / filename).read_text()
    assert '/workspace/' not in public and '/download/' not in public
    assert '"pixels"' not in public and '"bitmaps"' not in public

sys.path.insert(0, str(R / 'scripts'))
from render_aix_isas_cns import render, SOURCE_NAMES
with tempfile.TemporaryDirectory() as temp:
    directory = Path(temp)
    (directory / SOURCE_NAMES[0]).write_bytes(b'bad')
    try:
        render(directory)
    except ValueError:
        pass
    else:
        raise AssertionError('Incorrect source accepted')
    output = directory / 'existing'
    output.mkdir()
    proc = subprocess.run([sys.executable, str(R / 'scripts/render_aix_isas_cns.py'), str(directory), str(output)], capture_output=True, text=True)
    assert proc.returncode != 0 and 'Output must not already exist' in proc.stderr
if os.environ.get('AIX_CNS_PCF_DIR'):
    source = Path(os.environ['AIX_CNS_PCF_DIR'])
    image = render(source)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    assert image.size == (359, 66) and buffer.getvalue() == (R / r['specimen']).read_bytes()
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        for name in SOURCE_NAMES:
            shutil.copyfile(source / name, directory / name)
        for name in SOURCE_NAMES:
            original = (directory / name).read_bytes()
            (directory / name).write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
            try:
                render(directory)
            except ValueError:
                pass
            else:
                raise AssertionError('Mutated source accepted: ' + name)
            (directory / name).write_bytes(original)
        out = directory / 'redraw'
        subprocess.run([sys.executable, str(R / 'scripts/render_aix_isas_cns.py'), str(directory), str(out)], check=True)
        assert [p.name for p in out.iterdir()] == ['aix_isas_cns_24.png']
        assert (out / 'aix_isas_cns_24.png').read_bytes() == (R / r['specimen']).read_bytes()
    print('AIX exact three-source redraw, CLI output and per-source mutation rejection passed.')
else:
    print('AIX private source integration not run: PCFs not supplied.')
print('AIX: exactly one addition; 234 prior rows and PNGs, 13 recommendations and exclusions preserved.')
