"""Fixed RichWin PNG integrity, optional original pixels and fail-closed IO tests."""

import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/richwin_42_song_16_specimen.py'
SPEC = importlib.util.spec_from_file_location('richwin_fixed_preview', SCRIPT)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
SOURCE_ENV = os.environ.get('RICHWIN_42_SOURCES')
EXPECTED_SHA = {
    1: 'a5566e5e840fbb4e9946f87cef2641cdf842616dad07329744886eb757aad61a',
    4: '0954bf116d377000d09fad53980a3af25ee5c477902c4827ff839b3d42736b42',
}
EXPECTED_SOURCES = {
    'GB16ST.RSF': (216664, 'e210c3c3edc359bf9bfd7ffc664946f794962ae85f433e7841225c9b3339933e'),
    'CBST16E1.RSF': (75352, '562a48053bcfe87d53fa8f9e5a9a37c7fb18c95502bebe697ceb2aec993cde5d'),
    'CBST16E2.RSF': (377272, 'f9ff7bd921947fb44600d241a67662b4ccfae70fd2bc0a5f97b36140fe39c46a'),
}


def png_path(scale):
    return ROOT / ('assets/specimens/richwin_42_song_16' + ('' if scale == 1 else '_4x') + '.png')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PublicTests(unittest.TestCase):
    def test_fixed_metadata_pngs_and_integer_pixels(self):
        self.assertEqual(m.TEXT, '視野無限廣窗外有藍天')
        self.assertEqual((m.WIDTH, m.HEIGHT), (16, 16))
        self.assertEqual({k: (v['bytes'], v['sha256']) for k, v in m.SOURCES.items()}, EXPECTED_SOURCES)
        self.assertEqual(m.PNG_SHA256, EXPECTED_SHA)
        self.assertEqual(''.join(item[0] for item in m.FIXED), m.TEXT)
        self.assertEqual([sum(i[1] == name for i in m.FIXED) for name in m.SOURCES], [6, 4, 0])
        with Image.open(png_path(1)) as one, Image.open(png_path(4)) as four:
            self.assertEqual((one.size, one.mode), ((160, 16), 'RGBA'))
            self.assertEqual((four.size, four.mode), ((640, 64), 'RGBA'))
            self.assertEqual(four.tobytes(), one.resize(four.size, Image.Resampling.NEAREST).tobytes())
            self.assertEqual({one.getpixel((x, y)) for x in range(160) for y in range(16)}, {(255, 255, 255, 0), (0, 0, 0, 255)})
        for scale in (1, 4):
            self.assertEqual(sha(png_path(scale)), EXPECTED_SHA[scale])

    def test_wrong_sources_and_unapproved_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            bad, out = d / 'bad', d / 'new.png'
            for name, (size, _) in EXPECTED_SOURCES.items():
                for data in (b'', b'not a font', bytes(size), bytes(size + 1)):
                    bad.write_bytes(data)
                    with self.assertRaises((ValueError, OSError)):
                        m.checked_source(name, bad)
                with self.assertRaises(ValueError):
                    m.fixed_image({name: bytes(size)})
            for options in (['--text', '任意'], ['--all-glyphs'], ['--scale', '2'], ['--scale', '1.0']):
                command = [sys.executable, str(SCRIPT), '--gb-source', str(bad), '--e1-source', str(bad),
                           '--e2-source', str(bad), '--output', str(out), *options]
                result = subprocess.run(command, capture_output=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'unrecognized arguments' if options[0] in ('--text', '--all-glyphs') else b'invalid', result.stderr)
                self.assertFalse(out.exists())
            result = subprocess.run([sys.executable, str(SCRIPT), '--gb-source', str(bad),
                                     '--e1-source', str(bad), '--output', str(out)], capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'--e2-source', result.stderr)
            self.assertFalse(out.exists())


@unittest.skipUnless(SOURCE_ENV, 'Original source tests not run: set RICHWIN_42_SOURCES to a local directory')
class OriginalSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = [Path(SOURCE_ENV).absolute() / name for name in EXPECTED_SOURCES]
        cls.data = {name: m.checked_source(name, path) for name, path in zip(EXPECTED_SOURCES, cls.paths)}
        cls.before = [sha(p) for p in cls.paths]

    def assert_originals_unchanged(self):
        self.assertEqual([sha(p) for p in self.paths], self.before)

    def test_independent_original_pixels(self):
        # Rebuild source positions from original code grids, not renderer offsets.
        target_codes = [0x89ce, 0xd2b0, 0x8adf, 0xcfde, 0x83f2,
                        0xb4b0, 0xcde2, 0xd3d0, 0x86a3, 0xccec]
        gb_grid = [(lead << 8) | trail for lead in range(0xb0, 0xf8) for trail in range(0xa1, 0xff)]
        e1_grid = [(lead << 8) | trail for lead in range(0x81, 0x9b) for trail in range(0xa1, 0xff)]
        e1_grid = e1_grid[:2352]
        independent = Image.new('RGBA', (160, 16), (255, 255, 255, 0))
        for index, code in enumerate(target_codes):
            name, grid = ('GB16ST.RSF', gb_grid) if code in gb_grid else ('CBST16E1.RSF', e1_grid)
            slot = grid.index(code)
            raw = self.data[name][88 + slot * 32:120 + slot * 32]
            alpha = Image.frombytes('1', (16, 16), raw).convert('L')
            cell = Image.new('RGBA', (16, 16), (255, 255, 255, 0))
            cell.paste((0, 0, 0, 255), (0, 0, 16, 16), alpha)
            independent.paste(cell, (index * 16, 0))
        with Image.open(png_path(1)) as expected:
            self.assertEqual(independent.tobytes(), expected.tobytes())
        with Image.open(png_path(4)) as expected:
            self.assertEqual(independent.resize((640, 64), Image.Resampling.NEAREST).tobytes(), expected.tobytes())
        self.assertEqual(m.fixed_image(self.data).tobytes(), independent.tobytes())
        self.assert_originals_unchanged()

    def test_both_pngs_exact_and_encoder_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            for scale in (1, 4):
                output = Path(directory) / f'fixed{scale}.png'
                m.render(*self.paths, output, scale)
                self.assertEqual(output.read_bytes(), png_path(scale).read_bytes())
            output = Path(directory) / 'bad-encoder.png'
            with patch.dict(m.PNG_SHA256, {1: '0' * 64}):
                with self.assertRaisesRegex(ValueError, 'encoder'):
                    m.render(*self.paths, output)
            self.assertFalse(output.exists())
        self.assert_originals_unchanged()

    def test_each_source_tamper_and_header_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            out = d / 'new.png'
            for index, (name, data) in enumerate(self.data.items()):
                for offset in (0, 0x10, 0x14, 0x18, 0x20, 0x48, 0x50, 0x52, len(data) - 1):
                    changed = bytearray(data)
                    changed[offset] ^= 1
                    bad = d / f'changed-{index}'
                    bad.write_bytes(changed)
                    paths = self.paths.copy()
                    paths[index] = bad
                    with self.assertRaises(ValueError):
                        m.render(*paths, out)
                    payloads = dict(self.data)
                    payloads[name] = bytes(changed)
                    with self.assertRaises(ValueError):
                        m.fixed_image(payloads)
                    if offset != len(data) - 1:
                        with self.assertRaises(ValueError):
                            m.validate_layout(name, changed)
                    self.assertFalse(out.exists())
            for scale in (0, 2, -1, True, False, 1.0, 4.0, '4'):
                with self.assertRaises(ValueError):
                    m.render(*self.paths, out, scale)
            with self.assertRaises(ValueError):
                m.render(*self.paths, d / 'not-png.txt')
        self.assert_originals_unchanged()

    def test_existing_outputs_and_all_source_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            copies = []
            for index, data in enumerate(self.data.values()):
                p = d / f'source-{index}.png'
                p.write_bytes(data)
                copies.append(p)
            target = d / 'exists.png'
            target.write_bytes(b'preserve this')
            for out in (*copies, target):
                with self.assertRaises((ValueError, OSError)):
                    m.render(*copies, out)
            self.assertEqual([p.read_bytes() for p in copies], list(self.data.values()))
            self.assertEqual(target.read_bytes(), b'preserve this')
        self.assert_originals_unchanged()

    def test_links_fifos_directories_and_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            out = d / 'new.png'
            parent_link = d / 'parent-link'
            parent_link.symlink_to(d, target_is_directory=True)
            real_nested = d / 'real'
            real_nested.mkdir()
            for index, (name, data) in enumerate(self.data.items()):
                source = d / f'source-{index}.png'
                source.write_bytes(data)
                nested = real_nested / name
                nested.write_bytes(data)
                link = d / f'link-{index}'
                link.symlink_to(source)
                hard = d / f'hard-{index}'
                os.link(source, hard)
                fifo = d / f'fifo-{index}'
                os.mkfifo(fifo)
                invalid = (link, source, hard, fifo, d, parent_link / 'real' / name,
                           str(d) + '/real/../' + source.name)
                for item in invalid:
                    paths = self.paths.copy()
                    paths[index] = item
                    with self.assertRaises((ValueError, OSError)):
                        m.render(*paths, out)
                    self.assertFalse(out.exists())
                self.assertEqual(source.read_bytes(), data)
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
                           str(d) + '/real/../new.png'):
                with self.assertRaises((ValueError, OSError)):
                    m.render(*self.paths, output)
            self.assertEqual(target.read_bytes(), b'unchanged')
            for absent in (out, d / 'absent.png', real_nested / 'new.png'):
                self.assertFalse(absent.exists())
        self.assert_originals_unchanged()


if __name__ == '__main__':
    unittest.main(verbosity=2)
