from approved_simsun import IDS as SIMSUN_IDS, before_simsun_bytes
"""Approved fixed PSP preview, source-to-pixel regression and immutable 241-row baseline."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from PIL import Image
from approved_psp_bwfont import before_psp_file_sha
from approved_mrobe_mr100 import before_mrobe_data, ID as MROBE_ID
from approved_samsung_ypt6 import ID as YPT6_ID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import psp_bwfont_specimen as psp
sha = lambda b: hashlib.sha256(b).hexdigest()
digest = lambda value: sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
read = lambda path: before_mrobe_data(path, json.loads((ROOT / path).read_text()))
rows = read('data/catalog.json')
m = read('data/release-psp-bwfont.json')
ident = 'sony_psp_bwfont_16x18'
assert m['addedIds'] == [ident] and m['baseRows'] == 241 and m['totalRows'] == 242
assert len(rows) == len({r['id'] for r in rows}) == 242
old = [r for r in rows if r['id'] != ident]
assert len(old) == 241 and digest(old) == m['baseRowsSha256']
assert digest({r['id']: sha((ROOT/r['specimen']).read_bytes()) for r in old}) == m['baseSpecimensSha256']
assert digest({r['id']: sha(before_simsun_bytes(f"fonts/{r['id']}.html")) for r in old}) == m['basePagesSha256']
for path, expected in m['baseFilesSha256'].items():
    assert before_psp_file_sha(path) == expected, path
recommended = [r['id'] for r in sorted(rows, key=lambda r: -r['priority']) if r['priority'] > 0]
assert recommended == m['baseRecommendedIds'] and len(recommended) == 17
r = next(r for r in rows if r['id'] == ident)
assert digest(r) == m['addedRowSha256']
assert r['priority'] == 0 and r['sourceIndex'] == 279
assert (r['width'], r['height'], r['cellWidth'], r['cellHeight']) == (16, 18, 16, 18)
assert (r['inkWidth'], r['inkHeight']) == (15, 18)
assert r['asciiOrigin'] == 'absent' and r['asciiText'] == ''
assert r['asciiMissing'] == list(map(chr, range(32, 127)))
assert r['text'].splitlines() == psp.LINES and not r['hanMissing']
assert r['nativeEvidence']['source_sha256'] == psp.SOURCE_SHA256
assert r['nativeEvidence']['mappingSourceSha256'] == psp.MAPPING_SHA256
assert r['nativeEvidence']['firmwareSampleYear'] == 2015
assert read('data/summary.json')['rows'] == 242
assert len([p for p in (ROOT/'fonts').glob('*.html') if p.stem not in SIMSUN_IDS and p.stem not in (MROBE_ID, YPT6_ID, 'sc_song_13', 'ms_song_14', 'siemens_xelibri_14', 'hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')]) == 242
assert read('data/collection-history.json')['batches'][-1] == {'sourceManifest': 'release-psp-bwfont.json', 'ids': [ident]}
order = json.loads(subprocess.check_output(['node', '-e', "console.log(JSON.stringify(require('./app.js').filterCatalog(require('./data/catalog.json'), {}, '', 'recent').map(r=>r.id)))"], cwd=ROOT))
assert [value for value in order if value not in SIMSUN_IDS and value not in (MROBE_ID, YPT6_ID, 'sc_song_13', 'ms_song_14', 'siemens_xelibri_14', 'hitech_adp3_24','windows31_mingli20','deadf_game_16','richwin_42_song_16','asiasurf_tm16')][0] == ident
png = ROOT / r['specimen']
image = Image.open(png)
assert image.mode == '1' and image.size == (192, 38)
assert sha(png.read_bytes()) == r['specimenSha256']
assert all(image.getpixel((x,y)) == 255 for y in (18,19) for x in range(192))
source, mapping = os.environ.get('PSP_BWFONT_SOURCE'), os.environ.get('PSP_MAPPING_SOURCE')
assert bool(source) == bool(mapping), 'Set both PSP source input variables, or neither'
with tempfile.TemporaryDirectory() as td:
    bad = Path(td)/'bad'; bad.write_bytes(b'not an input')
    output = Path(td)/'fixed.png'
    try:
        psp.render(bad, bad, output)
    except ValueError:
        pass
    else:
        raise AssertionError('Incorrect BWFont SHA accepted')
    assert not output.exists()
    if source:
        try:
            psp.render(source, bad, output)
        except ValueError:
            pass
        else:
            raise AssertionError('Incorrect mapping SHA accepted')
        assert not output.exists()
        psp.render(source, mapping, output)
        assert output.read_bytes() == png.read_bytes()
        raw = Path(source).read_bytes()
        # Audited fixed sample slot numbers from the pinned intraFont Unicode table.
        # Independent byte/bit addressing, without calling the renderer's mapping/row code.
        slots = [[22628, 24684, 13438, 25838, 11549, 28338, 18741, 10164, 13735, 21371, 10183, 475], [22580, 24684, 16319, 25838, 11649, 28338, 18741, 10164, 13735, 21611, 10183, 475]]
        expected = Image.new('1', (192,38), 1)
        for li, line in enumerate(slots):
            for ci, slot in enumerate(line):
                for y in range(18):
                    for x in range(16):
                        value = (raw[slot*36 + y*2 + x//8] >> (7-x%8)) & 1
                        expected.putpixel((ci*16+x,li*20+y), 0 if value else 255)
        assert expected.tobytes() == image.tobytes()
        print('PSP exact source-to-PNG and independent byte-to-pixel regression passed.')
    else:
        print('PSP private source regression not run; set PSP_BWFONT_SOURCE and PSP_MAPPING_SOURCE.')
print('PSP: 242 entries, 17 recommendations; all prior 241 rows, PNGs and detail pages unchanged.')
