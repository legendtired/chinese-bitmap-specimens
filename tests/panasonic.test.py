from export_baseline import before_export_guides
"""Approved Panasonic entry; safe export and pixel-preserving tile decoding.
Optional real-input verification: FSUV1_TEST_ROM=/path/to/verified.rom python3 tests/panasonic.test.py
No ROM or full font is included in this test or the repository.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/fsuv1_to_bdf.py'
spec = importlib.util.spec_from_file_location('fsuv1', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
rows = [r for r in json.loads((ROOT / 'data/catalog.json').read_text()) if r['id'] not in ('stone_ms2401h_style1_32','stone_ms2401h_style2_32','stone_ms2401h_style3_32','stone_ms2401h_style4_32')]
manifest = json.loads((ROOT / 'data/release-panasonic-fsuv1.json').read_text())
base = [r for r in rows if r['id'] not in manifest['addedIds']]
assert len(rows) == 203 and len(base) == 202
assert hashlib.sha256(json.dumps([before_export_guides(r) for r in base], ensure_ascii=False, sort_keys=True).encode()).hexdigest() == manifest['baseRowsSha256']
row = next(r for r in rows if r['id'] == 'panasonic_fsuv1_16')
assert row['priority'] == 0 and (row['width'], row['height']) == (16, 16)
assert row['cellWidth'] == row['cellHeight'] == 16
assert row['hanMissing'] == ['廣', '窗'] and row['asciiOrigin'] == 'fullwidth-native'
assert row['specimenWidth'] == 320 and row['specimenHeight'] == 80
assert hashlib.sha256((ROOT / row['specimen']).read_bytes()).hexdigest() == row['specimenSha256']
assert '未独立' in row['notes'] and '暂映射' in row['nativeEvidence']['summary']
assert row['acquisitionGuide']['links'][0]['url'].endswith('/docs/panasonic-fs-uv1.md')
assert (ROOT / 'fonts/panasonic_fsuv1_16.html').exists()
assert module.slot_for(16, 1) == 1025 and module.slot_for(1, 1) == 97
# Each tile contains unique synthetic row bytes. No font pixels embedded.
pattern = bytes(range(32))
assert module.decode_slot(pattern, 0) == [y * 256 + y + 8 for y in range(8)] + [y * 256 + y + 8 for y in range(16, 24)]
for bad_slot in (-1, 4096):
    try:
        module.decode_slot(pattern, bad_slot)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid slot accepted')
with tempfile.TemporaryDirectory() as directory:
    p = Path(directory)
    for size in (10, module.EXPECTED_SIZE):
        source = p / f'wrong-{size}.rom'
        source.write_bytes(bytes(size))
        output = p / f'out-{size}.bdf'
        report = p / f'out-{size}.json'
        result = subprocess.run([sys.executable, str(SCRIPT), str(source), str(output), '--report', str(report)], capture_output=True, text=True)
        assert result.returncode and 'does not match' in result.stderr
        assert not output.exists() and not report.exists()
    output.write_text('preserve me')
    result = subprocess.run([sys.executable, str(SCRIPT), str(source), str(output)], capture_output=True, text=True)
    assert result.returncode and 'already exists' in result.stderr and output.read_text() == 'preserve me'
    report.write_text('preserve report')
    other = p / 'other.bdf'
    result = subprocess.run([sys.executable, str(SCRIPT), str(source), str(other), '--report', str(report)], capture_output=True, text=True)
    assert result.returncode and not other.exists() and report.read_text() == 'preserve report'

source = os.environ.get('FSUV1_TEST_ROM')
if source:
    data = Path(source).read_bytes()
    sys.path.insert(0, str(ROOT / 'scripts'))
    from render_bdf import read_bdf
    for symbols, expected, blanks in [(False, 2966, 0), (True, 3489, 15)]:
        glyphs = module.recover(data, symbols)
        assert len(glyphs) == expected and sum(not any(g['rows']) for g in glyphs) == blanks
        assert sum(g['ku'] >= 16 for g in glyphs) == 2965
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'verified.bdf'
            report = Path(directory) / 'report.json'
            command = [sys.executable, str(SCRIPT), source, str(output), '--report', str(report)]
            if symbols:
                command.append('--include-symbols')
            subprocess.run(command, check=True, capture_output=True)
            props, parsed, _ = read_bdf(output)
            assert props['FONTBOUNDINGBOX'] == '16 16 0 0' and len(parsed) == expected
            for glyph in glyphs:
                saved = parsed[glyph['unicode']]
                # Independent tile placement, all rows and columns compared.
                raw = data[glyph['slot'] * 32:(glyph['slot'] + 1) * 32]
                reference = bytearray(32)
                for tile in range(4):
                    for y in range(8):
                        reference[(tile // 2 * 8 + y) * 2 + tile % 2] = raw[tile * 8 + y]
                assert b''.join(bytes.fromhex(line) for line in saved['rows']) == reference
                assert saved['bbx'] == [16, 16, 0, 0] and saved['advance'] == 16
            assert all(ord(c) in parsed for c in '仝亜愛永国語漢字画面編集')
            assert all(ord(c) not in parsed for c in '廣窗Aa09')
            summary = json.loads(report.read_text())
            assert summary['glyphs'] == expected and summary['nonempty'] == expected - blanks
            assert summary['outputSha256'] == hashlib.sha256(output.read_bytes()).hexdigest()
    print('Panasonic real ROM: both exports, all pixels/metrics, coverage, reports and parser round trip passed.')
else:
    print('Panasonic: exact202 baseline, guarded new entry, synthetic tiles, wrong inputs and overwrite refusal passed; real ROM test not run.')
