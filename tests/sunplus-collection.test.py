"""Two new simplified Sunplus entries; 12x12 is an existing HZK12 duplicate."""
from pathlib import Path
import hashlib
import json
import struct

R = Path(__file__).resolve().parents[1]
entries = json.loads((R / 'data/sunplus-catalog-entries.json').read_text())
ids = [f'sunplus_sphe8202l_{s}' for s in ('16x16', '20x24')]
assert [r['id'] for r in entries] == ids
assert [r['sourceIndex'] for r in entries] == [264, 265]
for r, cell, ink in zip(entries, [(16,16), (20,24)], [(16,14), (20,21)]):
    assert r['priority'] == 0 and r['scripts'] == ['简体']
    assert (r['width'], r['height']) == (r['cellWidth'], r['cellHeight']) == cell
    assert (r['inkWidth'], r['inkHeight']) == ink
    assert r['asciiOrigin'] == 'absent' and r['asciiText'] == ''
    assert r['asciiMissing'] == [chr(i) for i in range(32, 127)]
    assert r['missing'] == r['hanMissing'] == []
    assert r['text'] == '视野无限广，窗外有蓝天。'
    assert '非运行时Unicode近似映射复刻' in r['notes']
    assert '不公开完整库' in r['licenseNote']
    assert '最初制作方式' in r['provenance'] and '尚未独立证实' in r['provenance']
    e = r['nativeEvidence']
    assert (e['sourceGlyphSlots'], e['gb2312Doublebyte'], e['basicHan'], e['printableAscii']) == (7614, 7445, 6763, 0)
    assert e['runtimeAdvance'] is None and e['runtimeBaseline'] is None
    blob = (R / r['specimen']).read_bytes()
    assert hashlib.sha256(blob).hexdigest() == r['specimenSha256']
    assert struct.unpack('>II', blob[16:24]) == (r['specimenWidth'], r['specimenHeight'])
    assert r['specimenHeight'] == cell[1]  # No empty ASCII row.

audit = json.loads((R / 'data/sunplus-independent-audit.json').read_text())
assert audit['passed'] and audit['all_source_slot_checks'] == 22842
assert audit['all_source_pixel_checks'] == 6700320
assert audit['traditional_bitmap_members_examined'] == 0
assert not audit['full_glyph_data_written'] and not audit['library_or_firmware_executed']
assert audit['exporter_sha256'] == hashlib.sha256((R / 'scripts/sunplus_bitmap_export.py').read_bytes()).hexdigest()
assert audit['verifier_sha256'] == hashlib.sha256((R / 'scripts/verify_sunplus_bitmap_decode.py').read_bytes()).hexdigest()
source = audit['source_mapping_metadata']
assert source['different_source_code_count'] == 24 and source['different_han_source_code_count'] == 11
assert source['passed'] and source['contiguous_table_range_coverage']
scale = json.loads((R / 'data/sunplus-ps2-scale-audit.json').read_text())
assert scale['sample_glyphs_verified_against_original_rom'] == 14
assert scale['bitmap_comparisons_including_bold'] == 15120
assert all(not r['matching_models'] for r in scale['results'])
duplicate = json.loads((R / 'data/sunplus-hzk12-duplicate-audit.json').read_text())
assert duplicate['original_hzk12_same_source_code_full_cell_checks'] == 7445
assert duplicate['original_hzk12_same_source_code_full_cell_han_checks'] == 6763
assert not (R / 'assets/specimens/sunplus_sphe8202l_12x12.png').exists()

if (R / 'data/catalog.json').exists():
    rows = json.loads((R / 'data/catalog.json').read_text())
    selected = [r for r in rows if r['id'] in ids]
    assert selected == entries
    assert not any('sunplus' in r['id'] and r['id'] not in ids for r in rows)
    for identity in ids:
        assert (R / f'fonts/{identity}.html').is_file()

print('Sunplus: exactly two new simplified entries; 12x12 duplicates HZK12, no ASCII substitution, audited source-slot mapping preserved.')
