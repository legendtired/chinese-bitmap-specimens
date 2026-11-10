from approved_simsun import IDS as SIMSUN_IDS, before_simsun_bytes
"""Fixed MR-100 preview, independent source-to-pixel regression, immutable 242-row baseline."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from PIL import Image
from approved_mrobe_mr100 import before_mrobe_file_sha
from approved_samsung_ypt6 import before_ypt6_data, ID as YPT6_ID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import mrobe_mr100_specimen as mrobe
sha = lambda b: hashlib.sha256(b).hexdigest()
digest = lambda value: sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
read = lambda path: before_ypt6_data(path, json.loads((ROOT / path).read_text()))
rows = read('data/catalog.json')
m = read('data/release-mrobe-mr100.json')
ident = 'olympus_mrobe_mr100_12'
assert m['addedIds'] == [ident] and m['baseRows'] == 242 and m['totalRows'] == 243
assert len(rows) == len({r['id'] for r in rows}) == 243
old = [r for r in rows if r['id'] != ident]
assert len(old) == 242 and digest(old) == m['baseRowsSha256']
assert digest({r['id']: sha((ROOT/r['specimen']).read_bytes()) for r in old}) == m['baseSpecimensSha256']
assert digest({r['id']: sha(before_simsun_bytes(f"fonts/{r['id']}.html")) for r in old}) == m['basePagesSha256']
for path, expected in m['baseFilesSha256'].items():
    assert before_mrobe_file_sha(path) == expected, path
recommended = [r['id'] for r in sorted(rows, key=lambda r: -r['priority']) if r['priority'] > 0]
assert recommended == m['baseRecommendedIds'] and len(recommended) == 17
r = next(r for r in rows if r['id'] == ident)
assert digest(r) == m['addedRowSha256']
assert r['priority'] == 0 and r['sourceIndex'] == 280
assert (r['width'], r['height'], r['cellWidth'], r['cellHeight']) == (12,12,12,12)
assert (r['inkWidth'], r['inkHeight']) == (11,12)
assert r['asciiOrigin'] == 'native' and r['asciiText'] == mrobe.LINES[2]
assert not r['asciiMissing'] and not r['hanMissing']
assert r['text'].splitlines() == mrobe.LINES[:2]
assert r['nativeEvidence']['source_sha256'] == mrobe.SOURCE_SHA256
assert r['nativeEvidence']['firmwareSampleYear'] == 2005
assert r['nativeEvidence']['completeCharacters'] == 20277
assert r['nativeEvidence']['excludedIncompleteCodepoints'] == ['U+3164']
assert read('data/summary.json')['rows'] == 243
assert read('data/summary.json')['nativePngCount'] == 242
assert len([p for p in (ROOT/'fonts').glob('*.html') if p.stem not in SIMSUN_IDS and p.stem not in (YPT6_ID, 'sc_song_13', 'ms_song_14', 'siemens_xelibri_14', 'hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')]) == 243
assert read('data/collection-history.json')['batches'][-1] == {'sourceManifest': 'release-mrobe-mr100.json', 'ids': [ident]}
order = json.loads(subprocess.check_output(['node', '-e', "console.log(JSON.stringify(require('./app.js').filterCatalog(require('./data/catalog.json'), {}, '', 'recent').map(r=>r.id)))"], cwd=ROOT))
assert [value for value in order if value not in SIMSUN_IDS and value not in (YPT6_ID, 'sc_song_13', 'ms_song_14', 'siemens_xelibri_14', 'hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')][:2] == [ident, 'sony_psp_bwfont_16x18']
png = ROOT / r['specimen']
image = Image.open(png)
assert image.mode == 'RGBA' and image.size == (171,44)
assert sha(png.read_bytes()) == r['specimenSha256']
assert set(image.getdata()) == {(255,255,255,0),(0,0,0,255)}
assert all(image.getpixel((x,y)) == (255,255,255,0) for y in (*range(12,16),*range(28,32)) for x in range(171))
with tempfile.TemporaryDirectory() as td:
    bad = Path(td)/'bad'; bad.write_bytes(b'not a font')
    output = Path(td)/'fixed.png'
    try:
        mrobe.render(bad, output)
    except ValueError:
        pass
    else:
        raise AssertionError('Incorrect FNT SHA accepted')
    assert not output.exists()
    source = os.environ.get('MROBE_MR100_SOURCE')
    if source:
        mrobe.render(source, output)
        assert output.read_bytes() == png.read_bytes()
        raw = Path(source).read_bytes()
        u = lambda off: int.from_bytes(raw[off:off+4], 'little')
        info, mapping, records = u(4), u(8), u(12)
        count = (info-mapping)//8
        assert count == 20278
        # Independent original-pointer-table + Pillow raw decoder, not renderer helpers.
        wanted = {ord(c) for line in mrobe.LINES for c in line}
        addresses = {}
        for i in range(count):
            cp, gid = u(mapping+i*8), u(mapping+i*8+4)
            if cp not in wanted:
                continue
            rec = records+gid*52
            width, height, offset = u(rec+4), u(rec+8), u(16+gid*4)
            assert height == 12 and offset == u(rec+20)
            addresses[cp] = (width,height,offset)
        expected = Image.new('RGBA', (171,44), (255,255,255,0))
        for li,line in enumerate(mrobe.LINES):
            x0 = 0
            for char in line:
                width,height,offset = addresses[ord(char)]
                stride = (width+7)//8
                glyph = raw[offset:offset+stride*height]
                mask = Image.frombytes('1',(width,height),glyph,'raw','1',stride,1)
                assert mask.tobytes() == glyph
                expected.paste((0,0,0,255),(x0,li*16,x0+width,li*16+height),mask)
                x0 += width
        assert expected.tobytes() == image.tobytes()
        print('MR-100 exact source-to-PNG and independent pointer/Pillow pixel regression passed.')
    else:
        print('MR-100 private source regression not run; set MROBE_MR100_SOURCE.')
print('MR-100: 243 entries, 17 recommendations; all prior 242 rows, PNGs and detail pages unchanged.')
