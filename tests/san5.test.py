from approved_recommendation_update import before_recommendations
from approved_p908_merge import restore_sun, historical_file_sha
"""Approved SAN5 addition, exact prior catalog, fullwidth and source boundaries."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'scripts'))
import render_san5_specimen as san5

rows = [r for r in before_recommendations(json.loads((R / 'data/catalog.json').read_text())) if r['id'] not in ('sony_ericsson_p802_12','sony_ericsson_p908_14','nokia_9210c_15','nokia_9210c_17','nokia_9210c_19','aix_isas_cns_24','hpux_song_40','hpux_sung_24','hpux_sung_34','hpux_sung_42','samsung_r208_16','sunplus_sphe8202l_16x16','sunplus_sphe8202l_20x24','ps2_scph50009_24','win32_simsun_13','win32_simsun_20')]
manifest = json.loads((R / 'data/release-san5.json').read_text())
by_id = {row['id']: row for row in rows}
base = [row for row in rows if row['id'] in manifest['baseIds']]
new = [row for row in rows if row['id'] in manifest['addedIds']]

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

assert len(rows) == len(by_id) == manifest['totalRows']
assert [row['id'] for row in base] == manifest['baseIds']
assert digest(restore_sun(base)) == manifest['baseRowsSha256']
assert [row['id'] for row in new] == manifest['addedIds'] == ['san5_dos_16x14']
assert digest(new) == manifest['addedRowsSha256']
assert [row['id'] for row in rows if row.get('priority', 0) > 0] == manifest['preservedRecommendedIds']
assert len(manifest['preservedRecommendedIds']) == 13
indices = [row['sourceIndex'] for row in rows if row.get('sourceIndex') is not None]
assert len(indices) == len(set(indices))
for row in base:
    assert hashlib.sha256((R / row['specimen']).read_bytes()).hexdigest() == row['specimenSha256']

row = new[0]
assert row['priority'] == 0 and row['scripts'] == ['繁体']
assert (row['width'], row['height'], row['cellWidth'], row['cellHeight']) == (16, 14, 16, 14)
assert row['text'] == san5.CHINESE and row['asciiText'] == san5.FULLWIDTH
assert row['asciiOrigin'] == 'fullwidth-native'
assert row['missing'] == row['hanMissing'] == row['asciiMissing'] == []
assert all(ord(c) > 127 for c in row['asciiText'])
assert len(san5.CHINESE) == len(san5.CHINESE_SLOTS) == 12
assert len(san5.FULLWIDTH) == len(san5.FULLWIDTH_SLOTS) == 27
native = row['nativeEvidence']
assert native['mainHan'] == native['commonHan'] + native['rareHan'] + 1 == 13052
assert native['sourceSlots'] == native['mainHan'] + native['prefixSlots'] == 13736
assert native['sourceBytes'] == native['sourceSlots'] * native['bytesPerGlyph'] + native['uninterpretedTailBytes'] == 384704
assert native['source_sha256'] == san5.SOURCE_SHA256
assert not native['allSymbolMappingsVerified'] and not native['physicalDumpVerified'] and not native['gameEncodingVerified']
assert native['uninterpretedTailBytes'] == 96
assert native['metricsStatus'] == 'preview-convention-not-verified-game-metrics'
assert '游戏字距和基线未验证' in row['layoutNote']
assert '彞U+5F5E' in row['notes'] and '非221套完整字库' in row['notes']
assert 'U+2024' in row['layoutNote'] and 'U+FF0E' in row['layoutNote']

png = (R / row['specimen']).read_bytes()
assert hashlib.sha256(png).hexdigest() == row['specimenSha256']
assert struct.unpack('>II', png[16:24]) == (row['specimenWidth'], row['specimenHeight']) == (432, 30)
page = (R / 'fonts/san5_dos_16x14.html').read_text()
assert '全角英数样文（非ASCII）' in page and '三国志Ⅴ' in page
history = json.loads((R / 'data/collection-history.json').read_text())
assert next(b for b in history['batches'] if b['sourceManifest'] == 'release-san5.json') == {'sourceManifest': 'release-san5.json', 'ids': manifest['addedIds']}
summary = json.loads((R / 'data/summary.json').read_text())
# Fullwidth SAN5 increases ordinary rows but never ordinary ASCII coverage.
for key in ('standardAsciiComplete', 'partialAscii', 'ordinaryAsciiRows'):
    assert summary[key] == manifest['previousSummary'][key] + (12 if key != 'partialAscii' else 0)
assert summary['ordinaryWithoutAsciiEvaluation'] == manifest['previousSummary']['ordinaryWithoutAsciiEvaluation'] + 4
curation = json.loads((R / 'data/curation.json').read_text())
assert not set(curation['removedIds']).intersection(by_id)
assert 'mstar_tv_simp_18' in by_id  # Concurrent approved addition must remain present.

for data in (b'', bytes(san5.SOURCE_BYTES)):
    try:
        san5.validate_source(data)
    except ValueError:
        pass
    else:
        raise AssertionError('Missing strict source hash check')
# Synthetic row boundary/bit-order test, no embedded proprietary bitmap.
pattern = bytes([0x80, 0x01] + [0, 0] * 12 + [0x01, 0x80])
glyph = san5.decode_glyph(pattern, 0)
assert glyph[0][0] and glyph[0][15] and glyph[13][7] and glyph[13][8]
assert sum(sum(line) for line in glyph) == 4
for index in (-1, san5.SLOTS):
    try:
        san5.decode_glyph(pattern, index)
    except ValueError:
        pass
    else:
        raise AssertionError('Missing slot range check')
with tempfile.TemporaryDirectory() as tmp:
    bad = Path(tmp) / 'invalid.16P'
    output = Path(tmp) / 'preview.png'
    bad.write_bytes(b'not a verified source')
    result = subprocess.run([sys.executable, str(R / 'scripts/render_san5_specimen.py'), '--source', str(bad), '--output', str(output)], capture_output=True)
    assert result.returncode != 0 and not output.exists()

source = os.environ.get('SAN5_SOURCE')
if source:
    from PIL import Image
    data = Path(source).read_bytes()
    san5.validate_source(data)
    actual = Image.open(R / row['specimen']).convert('RGBA')
    generated = san5.render(data)
    assert generated.tobytes() == actual.tobytes()
    # Independent integer-row implementation checks every pixel and line gap.
    expected = Image.new('RGBA', (432, 30), (255, 255, 255, 0))
    for top, slots in ((0, san5.CHINESE_SLOTS), (16, san5.FULLWIDTH_SLOTS)):
        for column, slot in enumerate(slots):
            for y in range(14):
                bits = int.from_bytes(data[slot * 28 + y * 2:slot * 28 + y * 2 + 2], 'big')
                for x in range(16):
                    if (bits >> (15 - x)) & 1:
                        expected.putpixel((column * 16 + x, top + y), (0, 0, 0, 255))
    assert actual.tobytes() == expected.tobytes()
    assert all(actual.getpixel((x, y))[3] == 0 for y in (14, 15) for x in range(432))
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / 'existing.png'
        output.write_bytes(b'keep me')
        result = subprocess.run([sys.executable, str(R / 'scripts/render_san5_specimen.py'), '--source', source, '--output', str(output)], capture_output=True)
        assert result.returncode != 0 and output.read_bytes() == b'keep me'
    print('SAN5 private-source checks passed: exact pixels, independent decoding, spacing and overwrite guard.')
else:
    print('SAN5 private-source checks not run; set SAN5_SOURCE for exact-input pixel verification.')
print('SAN5: one fixed-preview addition; all previous rows, specimen hashes and 13 priorities retained; no ASCII coverage inflation.')
