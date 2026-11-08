"""Fixed AsiaSurf PNG integrity; optional original-source pixels and fail-closed IO."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageOps

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/asiasurf_tm16_specimen.py'
SPEC = importlib.util.spec_from_file_location('asiasurf_fixed_preview', SCRIPT)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
SOURCE_ENV = os.environ.get('ASIASURF_TM16_SOURCE')
EXPECTED_SOURCE = (790002, '669c1e9acf8d20eb1598355387ebdb1234af9e5900095f9904e858cdc23c6e55')
EXPECTED_SHA = {
    1: '2effe5e9f6f64d1ace4e34f70ba740ad0da5cf4be5f7acc9e77314007d03a321',
    4: '7341fe4087afc67fcdf3d4e99e588834b1121a0125b79aceff04379c3e9de57f',
}


def png_path(scale):
    return ROOT / ('assets/specimens/asiasurf_tm16' + ('' if scale == 1 else '_4x') + '.png')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PublicTests(unittest.TestCase):
    def test_fixed_identity_pngs_and_integer_pixels(self):
        self.assertEqual(m.TEXT, '視野無限廣窗外有藍天')
        self.assertEqual((m.WIDTH, m.HEIGHT), (16, 16))
        self.assertEqual((m.SOURCE_BYTES, m.SOURCE_SHA256), EXPECTED_SOURCE)
        self.assertEqual(m.PNG_SHA256, EXPECTED_SHA)
        self.assertEqual(''.join(item[0] for item in m.FIXED), m.TEXT)
        with Image.open(png_path(1)) as one, Image.open(png_path(4)) as four:
            self.assertEqual((one.size, one.mode), ((160, 16), 'RGBA'))
            self.assertEqual((four.size, four.mode), ((640, 64), 'RGBA'))
            self.assertEqual(four.tobytes(), one.resize(four.size, Image.Resampling.NEAREST).tobytes())
            self.assertEqual({one.getpixel((x, y)) for x in range(160) for y in range(16)}, {(0, 0, 0, 0), (0, 0, 0, 255)})
        for scale in (1, 4):
            self.assertEqual(sha(png_path(scale)), EXPECTED_SHA[scale])

    def test_wrong_source_and_unapproved_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            bad, out = d / 'bad', d / 'new.png'
            for data in (b'', b'not a font', bytes(EXPECTED_SOURCE[0]), bytes(EXPECTED_SOURCE[0] + 1)):
                bad.write_bytes(data)
                with self.assertRaises((ValueError, OSError)):
                    m.checked_source(bad)
                with self.assertRaises(ValueError):
                    m.fixed_image(data)
            for options in (['--text', '任意'], ['--all-glyphs'], ['--scale', '2'], ['--scale', '1.0']):
                result = subprocess.run([sys.executable, str(SCRIPT), '--source', str(bad),
                                         '--output', str(out), *options], capture_output=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'unrecognized arguments' if options[0] in ('--text', '--all-glyphs') else b'invalid', result.stderr)
                self.assertFalse(out.exists())
            result = subprocess.run([sys.executable, str(SCRIPT), '--output', str(out)], capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'--source', result.stderr)
            self.assertFalse(out.exists())

    @unittest.skipUnless((ROOT / 'data/catalog.json').is_file(), 'No integrated catalog in this standalone preparation')
    def test_catalog_when_integrated(self):
        rows = json.loads((ROOT / 'data/catalog.json').read_text())
        matches = [r for r in rows if r['id'] == 'asiasurf_tm16']
        self.assertEqual(len(matches), 1)
        row = matches[0]
        self.assertEqual(row['priority'], 0)
        self.assertIs(type(row['sourceIndex']), int)
        self.assertEqual((row['width'], row['height'], row['cellWidth'], row['cellHeight']), (16, 16, 16, 16))
        self.assertEqual((row['specimenWidth'], row['specimenHeight']), (160, 16))
        self.assertEqual(row['specimenSha256'], EXPECTED_SHA[1])
        self.assertEqual(row['text'], m.TEXT)
        self.assertEqual(row['asciiOrigin'], 'unknown')
        self.assertEqual(row['asciiText'], '')
        self.assertEqual([row[k] for k in ('missing', 'hanMissing', 'asciiMissing', 'renderOmitted')], [[], [], [], []])
        e = row['nativeEvidence']
        self.assertEqual((e['big5Han'], e['compatibilityHan'], e['basicBig5OriginalCodes']), (13061, 2, 13065))
        self.assertEqual((e['cp950AdditionalHan'], e['cp950AdditionalSymbols'], e['unmappedNonblankSlots']), (7, 34, 116))
        self.assertEqual(e['asciiPhysicalSlots'], 256)
        self.assertIsNone(e['printableAscii'])
        self.assertIsNone(e['systemAsciiCoverage'])
        self.assertEqual(row['sourceUrl'], 'https://www.ibiblio.org/ccic/software/cnapps/mswcsys.html')


@unittest.skipUnless(SOURCE_ENV, 'Original source not tested: set ASIASURF_TM16_SOURCE to an authorized local WKF')
class OriginalSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(SOURCE_ENV).absolute()
        cls.data = m.checked_source(cls.path)
        cls.before = (cls.path.stat().st_size, sha(cls.path))

    def assert_original_unchanged(self):
        self.assertEqual((self.path.stat().st_size, sha(self.path)), self.before)

    def test_independent_original_pixels(self):
        # Independent lookup by enumerated Big5 grid, not renderer's offsets/formula.
        grid = [(lead << 8) | trail for lead in range(0xa1, 0xfa)
                for trail in (*range(0x40, 0x7f), *range(0xa1, 0xff))]
        self.assertEqual(len(grid), 13973)
        independent = Image.new('RGBA', (160, 16), (0, 0, 0, 0))
        for index, char in enumerate('視野無限廣窗外有藍天'):
            code = int.from_bytes(char.encode('big5'), 'big')
            offset = 338752 + 4114 + grid.index(code) * 32
            raw = self.data[offset:offset + 32]
            alpha = ImageOps.invert(Image.frombytes('1', (16, 16), raw).convert('L'))
            cell = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            cell.putalpha(alpha)
            independent.paste(cell, (index * 16, 0))
        with Image.open(png_path(1)) as expected:
            self.assertEqual(independent.tobytes(), expected.tobytes())
        with Image.open(png_path(4)) as expected:
            self.assertEqual(independent.resize((640, 64), Image.Resampling.NEAREST).tobytes(), expected.tobytes())
        self.assertEqual(m.fixed_image(self.data).tobytes(), independent.tobytes())
        self.assert_original_unchanged()

    def test_exact_pngs_and_encoder_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            for scale in (1, 4):
                output = Path(directory) / f'fixed{scale}.png'
                m.render(self.path, output, scale)
                self.assertEqual(output.read_bytes(), png_path(scale).read_bytes())
            output = Path(directory) / 'bad-encoder.png'
            with patch.dict(m.PNG_SHA256, {1: '0' * 64}):
                with self.assertRaisesRegex(ValueError, 'encoder'):
                    m.render(self.path, output)
            self.assertFalse(output.exists())
        self.assert_original_unchanged()

    def test_source_tamper_header_and_fixed_lookup(self):
        # All changed bytes are made in temporary copies, never the research source.
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            out, bad = d / 'new.png', d / 'changed.wkf'
            header_offsets = (256, 270, 274, 294, 298, 300, 302, 306, 310, 312, 314, 315,
                              316, 318, 320, 324, 338752, 338754, 338756, 338757,
                              338758, 338760, 338762, 338766)
            for offset in (*header_offsets, 448146, len(self.data) - 1):
                changed = bytearray(self.data)
                changed[offset] ^= 1
                bad.write_bytes(changed)
                with self.assertRaises(ValueError):
                    m.render(bad, out)
                with self.assertRaises(ValueError):
                    m.fixed_image(changed)
                if offset in header_offsets:
                    with self.assertRaises(ValueError):
                        m.validate_layout(changed)
                self.assertFalse(out.exists())
            for column, value in ((0, '天'), (1, 0xb580), (2, 3291), (3, 448147)):
                fixed = list(m.FIXED)
                first = list(fixed[0])
                first[column] = value
                fixed[0] = tuple(first)
                with patch.object(m, 'FIXED', tuple(fixed)):
                    with self.assertRaises(ValueError):
                        m.render(self.path, out)
                self.assertFalse(out.exists())
            for scale in (0, 2, -1, True, False, 1.0, 4.0, '4'):
                with self.assertRaises(ValueError):
                    m.render(self.path, out, scale)
            with self.assertRaises(ValueError):
                m.render(self.path, d / 'not-png.txt')
        self.assert_original_unchanged()

    def test_existing_output_and_source_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            source = d / 'source.png'
            source.write_bytes(self.data)
            target = d / 'exists.png'
            target.write_bytes(b'preserve this')
            for out in (source, target):
                with self.assertRaises((ValueError, OSError)):
                    m.render(source, out)
            self.assertEqual(source.read_bytes(), self.data)
            self.assertEqual(target.read_bytes(), b'preserve this')
        self.assert_original_unchanged()

    def test_links_fifos_directories_and_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            out = d / 'new.png'
            real = d / 'real'
            real.mkdir()
            parent_link = d / 'parent-link'
            parent_link.symlink_to(d, target_is_directory=True)
            source = d / 'source.wkf'
            source.write_bytes(self.data)
            nested = real / 'source.wkf'
            nested.write_bytes(self.data)
            link = d / 'source-link'
            link.symlink_to(source)
            hard = d / 'source-hard'
            os.link(source, hard)
            fifo = d / 'source-fifo'
            os.mkfifo(fifo)
            for invalid in (link, source, hard, fifo, d, parent_link / 'real' / 'source.wkf',
                            str(d) + '/real/../source.wkf'):
                with self.assertRaises((ValueError, OSError)):
                    m.render(invalid, out)
                self.assertFalse(out.exists())
            self.assertEqual(source.read_bytes(), self.data)
            target = d / 'target.png'
            target.write_bytes(b'unchanged')
            symlink = d / 'symlink.png'
            symlink.symlink_to(target)
            dangling = d / 'dangling.png'
            dangling.symlink_to(d / 'absent.png')
            hard = d / 'output-hard.png'
            os.link(target, hard)
            fifo = d / 'output-fifo.png'
            os.mkfifo(fifo)
            folder = d / 'directory.png'
            folder.mkdir()
            for output in (symlink, dangling, hard, fifo, folder, parent_link / 'real' / 'new.png',
                           str(d) + '/real/../new.png', d / 'missing-parent' / 'new.png'):
                with self.assertRaises((ValueError, OSError)):
                    m.render(self.path, output)
            self.assertEqual(target.read_bytes(), b'unchanged')
            for absent in (out, d / 'absent.png', real / 'new.png', d / 'missing-parent'):
                self.assertFalse(absent.exists())
        self.assert_original_unchanged()


if __name__ == '__main__':
    unittest.main(verbosity=2)
