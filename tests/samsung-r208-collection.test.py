"""One approved R208 addition, with unchanged 229-row baseline after integration."""
from pathlib import Path
import hashlib
import json
import struct

R=Path(__file__).resolve().parents[1]
def read(name):return json.loads((R/name).read_text())
def sha(data):return hashlib.sha256(data).hexdigest()
def digest(data):return sha(json.dumps(data,ensure_ascii=False,sort_keys=True).encode())
row=read('data/samsung-r208-catalog-entry.json')
m=read('data/release-samsung-r208.json')
assert isinstance(row,dict) and row['id']=='samsung_r208_16'
assert row['sourceIndex']==266 and row['priority']==0
assert (row['width'],row['height'],row['cellWidth'],row['cellHeight'])==(16,16,16,16)
assert row['asciiOrigin']=='native' and row['asciiMissing']==row['hanMissing']==row['missing']==[]
assert row['text']=='视野无限广，窗外有蓝天。' and row['asciiText']=='0123456789 AaBb GgMm !?:+-.'
assert row['sourceUrl']=='https://archive.org/details/samsung-sgh-r-220'
e=row['nativeEvidence']
assert (e['sourceGlyphSlots'],e['nonblankHan'],e['gb2312Han'],e['printableAscii'],e['exportedGlyphs'])==(15646,15645,6763,95,15742)
assert e['commaWidth']==e['asciiStorageWidth']==8 and e['westernFontIndex']==4
assert e['runtimeBaseline'] is None and e['runtimeAdvance'] is None
assert e['embeddedFirmwareDate']=='2002-09-06'
png=(R/row['specimen']).read_bytes()
assert sha(png)==row['specimenSha256']=='3c907fb8750476b2c59015ea73da90cac2cfafb291b2a2e1bb20bb20402b6b13'
assert struct.unpack_from('>II',png,16)==(row['specimenWidth'],row['specimenHeight'])==(224,44)
audit=read('data/samsung-r208-independent-audit.json')
assert audit['status']=='PASS'
assert audit['exporterSha256']==sha((R/'scripts/samsung_r208_bitmap_export.py').read_bytes())
assert audit['verifierSha256']==sha((R/'scripts/verify_samsung_r208_bitmap_decode.py').read_bytes())
assert audit['checks']['bdfParsedGlyphs']==15742 and audit['checks']['gb2312Han']==6763
assert audit['specimen']['all9856PixelsMatchSource'] and audit['specimen']['researchNativePixelsMatch']
assert audit['specimen']['pngSha256']==row['specimenSha256']
dedup=read('data/samsung-r208-dedup-audit.json')
assert dedup['scope']['catalog_rows']==229 and dedup['scope']['old_sample_pixel_hashes_rechecked']==224
assert dedup['scope']['historical_reference_ids_with_some_trusted_han_mapping']==216
assert dedup['scope']['unresolved_historical_mapping_ids']==['hzk_hzk16f','sony-g90-raw-pattern']
assert {r['id']for r in dedup['recent_references']}=={'win32_simsun_13','win32_simsun_20','ps2_scph50009_24','sunplus_sphe8202l_16x16','sunplus_sphe8202l_20x24'}
assert all(r['independent_crop_check']for r in dedup['recent_references'])
assert m['baseRows']==229 and m['totalRows']==230 and m['addedIds']==[row['id']]
assert m['baseCommit']=='4d5f51f908cc82b553cb958306591b19d6c5ef41'
assert m['addedRowsSha256']==digest([row]) and len(m['preservedRecommendedIds'])==13
if (R/'data/catalog.json').exists():
    rows=read('data/catalog.json')
    base=[r for r in rows if r['id']in m['baseIds']]
    added=[r for r in rows if r['id']in m['addedIds']]
    assert len(rows)==len({r['id']for r in rows})==235
    assert len(base)==229 and [r['id']for r in base]==m['baseIds']
    assert digest(base)==m['baseRowsSha256'] and added==[row]
    assert [r['id']for r in rows if r.get('priority',0)>0]==m['preservedRecommendedIds']
    for r in base:assert sha((R/r['specimen']).read_bytes())==r['specimenSha256'],r['id']
    indices=[r['sourceIndex']for r in rows if r.get('sourceIndex')is not None]
    assert len(indices)==len(set(indices))
    history=read('data/collection-history.json')
    assert next(b for b in history['batches'] if b['sourceManifest']=='release-samsung-r208.json')=={'sourceManifest':'release-samsung-r208.json','ids':['samsung_r208_16']}
    summary=read('data/summary.json')
    assert summary['rows']==235 and summary['nativePngCount']==234
    assert summary['standardAsciiComplete']==m['previousSummary']['standardAsciiComplete']+5
    assert summary['ordinaryWithoutAsciiEvaluation']==m['previousSummary']['ordinaryWithoutAsciiEvaluation']+1
    assert summary['fontFilesIncluded']==0 and summary['glyphDataIncluded']is False
    assert (R/'fonts/samsung_r208_16.html').is_file()
print('R208: one approved 16x16 source entry, native 8px comma/ASCII, exact source audit and preserved release baseline.')
