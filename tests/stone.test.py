from approved_latin_update import AFTER
from approved_latin_update import historical_rows
"""Four approved Stone styles, exact prior catalog and fixed specimens only."""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[1]
rows = [r for r in json.loads((ROOT / 'data/catalog.json').read_text()) if r['id'] not in ('sunplus_sphe8202l_16x16','sunplus_sphe8202l_20x24','ps2_scph50009_24','win32_simsun_13','win32_simsun_20','san5_dos_16x14','mstar_tv_simp_18','palm_cjkos_fgb12ktf','palm_cjkos_fgb12fsf','palm_cjkos_fb512kbf','palm_cjkos_fb512xmf','psion618c_8','psion618c_11','wqx_pc505_14x15','sharp_x68000_16','ibm_pcdos_kai_24','ibm_pcdos_hei_24','ibm_pcdos_fangsong_24','nokia_dct3_1999','fmtowns_f20_20','sun_gbk_song_12','sun_gbk_song_14','sun_gbk_song_16','sun_gbk_song_20','sun_gbk_song_24','sun_gb2312_song_12','sun_gb2312_song_14','sun_gb2312_song_20')]
manifest = json.loads((ROOT / 'data/release-stone-ms2401h.json').read_text())
ids = [f'stone_ms2401h_style{i}_32' for i in range(1, 5)]
assert manifest['addedIds'] == ids
base = [row for row in rows if row['id'] not in ids]
assert len(base) == 203 and len(rows) == 207
assert hashlib.sha256(json.dumps(historical_rows(base), ensure_ascii=False, sort_keys=True).encode()).hexdigest() == manifest['baseRowsSha256']
new_indices = [row['sourceIndex'] for row in rows if row['id'] in ids]
assert len(set(new_indices)) == 4 and not set(new_indices) & {row['sourceIndex'] for row in base}
by_id = {row['id']: row for row in rows}
for item in manifest['styles']:
    row = by_id[item['id']]
    assert row['priority'] == 0 and row['width'] == row['height'] == row['cellWidth'] == row['cellHeight'] == 32
    assert row['text'] == manifest['sampleText'] == '视野无限广窗外有蓝天'
    assert row['asciiText'] == 'ＡＢＣａｂｃ０１２３' and row['asciiOrigin'] == 'fullwidth-native'
    assert row['missing'] == row['hanMissing'] == row['asciiMissing'] == []
    assert '视觉分类' in row['notes'] and '非全库去重' in row['notes']
    assert '独立认证' in row['provenance'] and '不是24点放大' in row['provenance']
    assert '6763' in row['acquisitionGuide']['notice']
    assert item['hanzi'] == 6763 and item['sourceSlots'] == 6768
    assert row['acquisitionGuide']['links'][0]['url'].endswith('/docs/stone-ms2401h.md')
    png = (ROOT / row['specimen']).read_bytes()
    assert struct.unpack('>II', png[16:24]) == (320, 68)
    assert hashlib.sha256(png).hexdigest() == row['specimenSha256'] == AFTER[row['id']]['specimenSha256']
    assert (ROOT / 'fonts' / (row['id'] + '.html')).is_file()
assert len({item['rowMajorSha256'] for item in manifest['styles']}) == 4
assert len({item['sampleSha256'] for item in manifest['styles']}) == 4
assert (ROOT / 'docs/stone-ms2401h.md').is_file()
assert (ROOT / 'scripts/stone_ms2401h_to_bdf.py').is_file()
assert sum(row['priority'] > 0 for row in rows) == 13
print('Stone: four approved 32px styles, preserved203 baseline, distinct source/sample hashes, source and naming limits, no new recommendation.')
