"""Fixed PNG integrity, independent original pixels, and fail-closed path tests."""

import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/deadf_game_16_specimen.py'
SPEC = importlib.util.spec_from_file_location('deadf_fixed_source', SCRIPT)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
SOURCE_ENV = os.environ.get('DEADF_GAME_16_SOURCE')
EXPECTED_SHA = {
    1: '023a138be5fe1df233fd8dccafb4e35b41ee0180287255b467d353f5062d3293',
    4: '35f04e67d53acec55146b72018860103bbf568673eec331e488e01334209232a',
}


def png_path(scale):
    return ROOT / ('assets/specimens/deadf_game_16' + ('' if scale == 1 else '_4x') + '.png')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PublicFixedTests(unittest.TestCase):
    def test_approved_pngs_and_integer_pixels(self):
        self.assertEqual(m.TEXT, '視野無限廣，窗外有藍天。')
        self.assertEqual((m.WIDTH, m.HEIGHT), (16, 16))
        self.assertEqual(m.SOURCE_BYTES, 452832)
        self.assertEqual(m.SOURCE_SHA256, '438ac6da4f212fbdf2098e0828786177ffdd25ec1d93225d9113298be7e43967')
        self.assertEqual(m.PNG_SHA256, EXPECTED_SHA)
        with Image.open(png_path(1)) as one, Image.open(png_path(4)) as four:
            self.assertEqual((one.size, one.mode), ((192, 16), 'RGBA'))
            self.assertEqual((four.size, four.mode), ((768, 64), 'RGBA'))
            self.assertEqual(four.tobytes(), one.resize(four.size, Image.Resampling.NEAREST).tobytes())
            self.assertEqual({one.getpixel((x, y)) for x in range(one.width) for y in range(one.height)},
                             {(0, 0, 0, 0), (0, 0, 0, 255)})
        for scale in (1, 4):
            self.assertEqual(sha(png_path(scale)), EXPECTED_SHA[scale])

    def test_wrong_input_and_unapproved_cli_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            bad, out = d / 'wrong-source', d / 'output.png'
            for data in (b'', b'not the original source', bytes(m.SOURCE_BYTES), bytes(m.SOURCE_BYTES + 1)):
                bad.write_bytes(data)
                with self.assertRaises((ValueError, OSError)):
                    m.render(bad, out)
                with self.assertRaises(ValueError):
                    m.fixed_image(data)
                self.assertFalse(out.exists())
            for options in (['--text', 'not approved'], ['--scale', '2'], ['--scale', '1.0'], ['--all-glyphs']):
                process = subprocess.run([sys.executable, str(SCRIPT), '--source', str(bad),
                                          '--output', str(out), *options], capture_output=True, timeout=10)
                self.assertNotEqual(process.returncode, 0)
                self.assertFalse(out.exists())


@unittest.skipUnless(SOURCE_ENV, 'Private source tests not run: set DEADF_GAME_16_SOURCE')
class PrivateSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(SOURCE_ENV).absolute()
        cls.data = m.checked_source(cls.source)
        cls.before = sha(cls.source)

    def test_independent_physical_slots_and_original_pixels(self):
        # Enumerate the 159 physical trails instead of repeating the renderer formula.
        physical_trails = list(range(0x40, 0x80)) + list(range(0xa0, 0xff))
        self.assertEqual(len(physical_trails), 159)
        independent = Image.new('RGBA', (192, 16), (0, 0, 0, 0))
        for index, char in enumerate('視野無限廣，窗外有藍天。'):
            lead, trail = char.encode('big5')
            rows_before = list(range(0xa1, 0xfa)).index(lead)
            slot = rows_before * len(physical_trails) + physical_trails.index(trail)
            cell = Image.frombytes('1', (16, 16), self.data[slot * 32:(slot + 1) * 32])
            alpha = cell.convert('L')
            ink = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            ink.putalpha(alpha)
            independent.paste(ink, (16 * index, 0))
        with Image.open(png_path(1)) as expected:
            self.assertEqual(independent.tobytes(), expected.tobytes())
        self.assertEqual(m.fixed_image(self.data).tobytes(), independent.tobytes())

    def test_both_approved_pngs_byte_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            for scale in (1, 4):
                output = Path(directory) / f'fixed{scale}.png'
                m.render(self.source, output, scale)
                self.assertEqual(output.read_bytes(), png_path(scale).read_bytes())
                self.assertEqual(sha(output), EXPECTED_SHA[scale])
        self.assertEqual(sha(self.source), self.before)

    def test_negative_source_tampering_and_output_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            out = d / 'new.png'
            changed = bytearray(self.data)
            changed[len(changed) // 2] ^= 1
            bad = d / 'same-size-tampered'
            bad.write_bytes(changed)
            with self.assertRaises(ValueError):
                m.render(bad, out)
            self.assertFalse(out.exists())
            source_copy = d / 'source.png'
            source_copy.write_bytes(self.data)
            existing = d / 'existing.png'
            existing.write_bytes(b'keep existing bytes')
            for target in (source_copy, existing):
                with self.assertRaises((ValueError, OSError)):
                    m.render(source_copy, target)
            self.assertEqual(source_copy.read_bytes(), self.data)
            self.assertEqual(existing.read_bytes(), b'keep existing bytes')
            for scale in (0, 2, -1, True, False, 1.0, 4.0, '4'):
                with self.assertRaises(ValueError):
                    m.render(self.source, out, scale)
                self.assertFalse(out.exists())
            with self.assertRaises(ValueError):
                m.render(self.source, d / 'not-png.txt')

    def test_no_links_fifos_directories_or_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            out = d / 'new.png'
            source_link = d / 'source-link'
            source_link.symlink_to(self.source)
            parent_link = d / 'parent-link'
            parent_link.symlink_to(d, target_is_directory=True)
            source_copy = d / 'source-copy.png'
            source_copy.write_bytes(self.data)
            hardlink = d / 'hardlink.png'
            os.link(source_copy, hardlink)
            fifo = d / 'input-fifo'
            os.mkfifo(fifo)
            for source in (source_link, parent_link / 'source-copy.png', source_copy, hardlink, fifo, d):
                with self.assertRaises((ValueError, OSError)):
                    m.render(source, out)
                self.assertFalse(out.exists())
            target = d / 'target.png'
            target.write_bytes(b'do not change')
            output_link = d / 'output-link.png'
            output_link.symlink_to(target)
            dangling = d / 'dangling.png'
            dangling.symlink_to(d / 'absent.png')
            output_fifo = d / 'output-fifo.png'
            os.mkfifo(output_fifo)
            output_dir = d / 'output-directory.png'
            output_dir.mkdir()
            for output in (output_link, dangling, parent_link / 'other.png', hardlink, output_fifo, output_dir):
                with self.assertRaises((ValueError, OSError)):
                    m.render(self.source, output)
            for source, output in ((str(parent_link) + '/../source-copy.png', out),
                                   (self.source, str(parent_link) + '/../new.png')):
                with self.assertRaises(ValueError):
                    m.render(source, output)
            self.assertEqual(target.read_bytes(), b'do not change')
            self.assertEqual(source_copy.read_bytes(), self.data)
            self.assertFalse(out.exists())
            self.assertFalse((d / 'other.png').exists())
            self.assertFalse((d / 'absent.png').exists())
        self.assertEqual(sha(self.source), self.before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
