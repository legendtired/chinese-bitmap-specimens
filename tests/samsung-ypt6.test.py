"""Approved fixed YP-T6 preview, original-byte regression and immutable 243-entry baseline."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from PIL import Image
from approved_samsung_ypt6 import before_ypt6_file_sha, ID
from approved_sc_song13 import before_sc13_data, ID as SC13_ID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import samsung_ypt6_specimen as ypt6
sha = lambda b: hashlib.sha256(b).hexdigest()
digest = lambda value: sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
read = lambda path: before_sc13_data(path, json.loads((ROOT/path).read_text()))
rows = read('data/catalog.json')
m = read('data/release-samsung-ypt6.json')
assert m['addedIds'] == [ID] and m['baseRows'] == 243 and m['totalRows'] == 244
assert m['baseCommit'] == 'fd8d647f494489ace22cca96312b2b0e5e7d8603'
assert m['baseTree'] == 'efe60bc3929064a34cf2d8205ae5edbb7f4225d4'
assert len(rows) == len({r['id'] for r in rows}) == 244
old = [r for r in rows if r['id'] != ID]
assert len(old) == 243 and digest(old) == m['baseRowsSha256']
assert digest({r['id']: sha((ROOT/r['specimen']).read_bytes()) for r in old}) == m['baseSpecimensSha256']
assert digest({r['id']: sha((ROOT/'fonts'/f"{r['id']}.html").read_bytes()) for r in old}) == m['basePagesSha256']
for path, expected in m['baseFilesSha256'].items():
    assert before_ypt6_file_sha(path) == expected, path
recommended = [r['id'] for r in sorted(rows, key=lambda r: -r['priority']) if r['priority'] > 0]
assert recommended == m['baseRecommendedIds'] and len(recommended) == 17
r = next(r for r in rows if r['id'] == ID)
assert digest(r) == m['addedRowSha256']
assert r['priority'] == 0 and r['sourceIndex'] == 281
assert (r['width'], r['height'], r['cellWidth'], r['cellHeight']) == (14,16,14,16)
assert r['asciiOrigin'] == 'native' and r['asciiText'] == ypt6.LINES[2]
assert not r['asciiMissing'] and not r['hanMissing']
assert r['text'].splitlines() == ypt6.LINES[:2]
assert r['nativeEvidence']['source_sha256'] == ypt6.SOURCE_SHA256
assert r['nativeEvidence']['firmwareSampleYear'] == 2004
assert r['nativeEvidence']['nativeGlyphSlots'] == 33894
assert r['nativeEvidence']['mappedCharacters'] == 33893
assert r['nativeEvidence']['nonblankCjk'] == 20902
summary = read('data/summary.json')
assert summary['rows'] == 244 and summary['nativePngCount'] == 243
assert len([p for p in (ROOT/'fonts').glob('*.html') if p.stem not in (SC13_ID, 'ms_song_14', 'siemens_xelibri_14', 'hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')]) == 244
assert read('data/collection-history.json')['batches'][-1] == {'sourceManifest': 'release-samsung-ypt6.json', 'ids': [ID]}
order = json.loads(subprocess.check_output(['node', '-e', "console.log(JSON.stringify(require('./app.js').filterCatalog(require('./data/catalog.json'), {}, '', 'recent').map(r=>r.id)))"], cwd=ROOT))
assert [ident for ident in order if ident not in (SC13_ID, 'ms_song_14', 'siemens_xelibri_14', 'hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')][:3] == [ID, 'olympus_mrobe_mr100_12', 'sony_psp_bwfont_16x18']
png = ROOT/r['specimen']
image = Image.open(png)
assert image.mode == 'RGBA' and image.size == (211,56)
assert sha(png.read_bytes()) == r['specimenSha256'] == '32fde0f66433fa615794b0a5bc117017ff48f3fe61f488d00c2b7cd463b8c322'
assert set(image.getdata()) == {(0,0,0,0),(0,0,0,255)}
assert sum(pixel[3] == 255 for pixel in image.getdata()) == 2057
assert all(image.getpixel((x,y)) == (0,0,0,0) for y in (*range(16,20),*range(36,40)) for x in range(211))
with tempfile.TemporaryDirectory() as td:
    bad = Path(td)/'bad'; bad.write_bytes(b'not a firmware resource')
    output = Path(td)/'fixed.png'
    try:
        ypt6.render(bad, output)
    except ValueError:
        pass
    else:
        raise AssertionError('Incorrect source SHA accepted')
    assert not output.exists()
    source = os.environ.get('SAMSUNG_YPT6_SOURCE')
    if source:
        ypt6.render(source, output)
        assert output.read_bytes() == png.read_bytes()
        raw = Path(source).read_bytes()
        # Independent random access directly in the wrapped source. No renderer helpers.
        def payload_bytes(address, size):
            return bytes(raw[67 + (i//510)*512 + i%510] for i in range(address,address+size))
        def word(address):
            a,b,c = payload_bytes(address,3)
            return a + 256*b + 65536*c
        def child(directory, ident):
            matches = [i for i in range(word(directory)) if word(directory+3+6*i) == ident]
            assert len(matches) == 1
            address = directory + 3*word(directory+6+6*matches[0])
            assert word(address) == ident
            return address+9
        first, second, pages = (child(0, ident) for ident in (1047,1048,1050))
        expected = Image.new('RGBA', image.size, (0,0,0,0))
        for li,line in enumerate(ypt6.LINES):
            x0 = 0
            for ch in line:
                cp = ord(ch)
                page = word(first+(cp//256)*3)
                assert page & 0x10000
                mapped = word(child(second,(page & 65535)+1)+(cp%256)*3)
                assert mapped != 1
                bitmap = child(child(pages,mapped//256+1),mapped%256+1)
                width,height = word(bitmap),word(bitmap+3)
                assert height == 16
                assert word(bitmap-6) == 6+width*2 and word(bitmap-3) == 3
                # Iterate original column bytes, then the eight low-to-high bits.
                for band in range(2):
                    for x,value in enumerate(payload_bytes(bitmap+6+band*width,width)):
                        for bit in range(8):
                            if (value//(2**bit))%2:
                                expected.putpixel((x0+x,li*20+band*8+bit),(0,0,0,255))
                x0 += width
        assert expected.tobytes() == image.tobytes()
        print('YP-T6 exact source-to-PNG and independent wrapped-byte pixel regression passed.')
    else:
        print('YP-T6 private source regression not run; set SAMSUNG_YPT6_SOURCE.')
print('YP-T6: 244 entries, 17 recommendations; all prior 243 rows, PNGs, detail pages and content-version builder unchanged.')
