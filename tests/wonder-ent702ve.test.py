"""Verify this exact one-entry Wonder release and its public artifact boundary."""
from approved_zhenhan import before_zhenhan_rows, before_zhenhan_data, before_zhenhan_bytes, MANIFEST as ZHENHAN
import copy
import json
import unittest
from pathlib import Path
from PIL import Image

from approved_wonder import (
    ROOT, MANIFEST, MANIFEST_NAME, IDS, sha, digest,
    before_wonder_rows, before_wonder_data, before_wonder_bytes,
)


class Wonder(unittest.TestCase):
    def test_reviewed_release_scope(self):
        self.assertEqual(MANIFEST['baseCommit'], 'c20a8723a2b9fee7b2dc4024c987c2c3ad39fda6')
        self.assertEqual(IDS, ['wonder_ent702ve_16'])
        self.assertEqual(MANIFEST['batch'], {'sourceManifest': MANIFEST_NAME, 'ids': IDS})
        rows = before_zhenhan_rows(json.loads((ROOT / 'data/catalog.json').read_text()))
        self.assertEqual(len(rows), 259)
        self.assertEqual(len(before_wonder_rows(rows)), 258)
        self.assertEqual(digest(before_wonder_rows(rows)), MANIFEST['baseRowsSha256'])
        self.assertEqual(rows[-1]['id'], IDS[0])
        self.assertEqual(rows[-1]['priority'], 0)
        self.assertEqual(sum(row['priority'] > 0 for row in rows), 20)
        history = before_zhenhan_data('data/collection-history.json',json.loads((ROOT / 'data/collection-history.json').read_text()))
        self.assertEqual(history['batches'][-1], MANIFEST['batch'])
        for path, expected in MANIFEST['baseFilesSha256'].items():
            self.assertEqual(sha(before_wonder_bytes(path)), expected, path)
        for path, expected in MANIFEST['newFileHashes'].items():
            self.assertEqual(sha(before_zhenhan_bytes(path)), expected, path)
        new = set(MANIFEST['newPaths'])
        self.assertEqual(new - {f'data/{MANIFEST_NAME}'}, set(MANIFEST['newFileHashes']))
        base = set(MANIFEST['baseFilesSha256'])
        self.assertFalse(base & new)
        actual = {
            str(p.relative_to(ROOT)) for p in ROOT.rglob('*')
            if p.is_file() and '.git' not in p.relative_to(ROOT).parts
            and '__pycache__' not in p.relative_to(ROOT).parts
        }
        self.assertEqual(actual - set(ZHENHAN['newPaths']), base | new)
        for path in actual:
            f = ROOT / path
            self.assertFalse(f.is_symlink(), path)
            self.assertEqual(f.stat().st_nlink, 1, path)
            self.assertNotIn(f.suffix.lower(), {'.bdf', '.rom', '.bin', '.fnt', '.woff', '.woff2',
                '.ttf', '.otf', '.zip', '.7z'}, path)

    def test_immutable_release_rejects_tampering(self):
        rows = before_zhenhan_rows(json.loads((ROOT / 'data/catalog.json').read_text()))
        changed = copy.deepcopy(rows)
        changed[-1]['name'] += ' changed'
        with self.assertRaises(AssertionError):
            before_wonder_rows(changed)
        with self.assertRaises(AssertionError):
            before_wonder_rows([*rows[:-2], rows[-1], rows[-2]])
        history = before_zhenhan_data('data/collection-history.json',json.loads((ROOT / 'data/collection-history.json').read_text()))
        history['batches'][-1]['ids'].append('other')
        with self.assertRaises(AssertionError):
            before_wonder_data('data/collection-history.json', history)
        summary = json.loads((ROOT / 'data/summary.json').read_text())
        summary['unreviewed'] = True
        with self.assertRaises(AssertionError):
            before_wonder_data('data/summary.json', summary)

    def test_native_fixed_specimen(self):
        row = before_zhenhan_rows(json.loads((ROOT / 'data/catalog.json').read_text()))[-1]
        self.assertEqual((row['width'], row['height'], row['cellWidth'], row['cellHeight']), (16, 16, 16, 16))
        self.assertEqual(set(row['scripts']), {'简体', '繁体'})
        self.assertNotEqual(row.get('sampleKind'), 'reference')
        png = Path(row['specimen'])
        self.assertEqual(png.suffix, '.png')
        self.assertEqual(png.parent, Path('assets/specimens'))
        self.assertEqual(sha((ROOT / png).read_bytes()), row['specimenSha256'])
        with Image.open(ROOT / png) as im:
            self.assertEqual(im.size, (row['specimenWidth'], row['specimenHeight']))
            self.assertLessEqual(len(set(im.getdata())), 2)
            self.assertNotEqual(im.getbbox(), None)


if __name__ == '__main__':
    unittest.main(verbosity=2)
