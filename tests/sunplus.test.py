#!/usr/bin/env python3
"""Synthetic-only fixtures; SUNPLUS_LIBFONT optionally enables private-source tests."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sunplus_export', ROOT / 'scripts/sunplus_bitmap_export.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
GOLD = {
    '12x12': ('9568f47a2e1dbe2a7df494515c8fa832d9dc8306ef7322273d929ddaddead128', 155, 12),
    '16x16': ('2b9d5c4f658ab4ec7735f1f424bfc7d1b8667ee974ed2e92e0096a21ddb21469', 203, 16),
    '20x24': ('eb6ccee4516890b26d671145d9c2b49265d5f50493e40a2fbb00ea4e9ae3658b', 251, 24),
}


def ar_member(name, body):
    header = (name.ljust(16) + '0'.ljust(12) + '0'.ljust(6) + '0'.ljust(6)
              + '100644'.ljust(8) + str(len(body)).ljust(10) + '`\n').encode('ascii')
    return header + body + (b'\n' if len(body) & 1 else b'')


def fake_elf(payload, symbol='synthetic', padding=2):
    shstrings = b'\0.rodata\0.shstrtab\0.symtab\0.strtab\0'
    strings = b'\0' + symbol.encode() + b'\0'
    symbols = bytes(16) + struct.pack('<IIIBBH', 1, 0, len(payload), 0x11, 0, 1)
    sections = [(0,) * 10]
    data = bytearray(52)
    for name, kind, body, link, entry in [('.rodata', 1, payload + bytes(padding), 0, 0),
                                          ('.shstrtab', 3, shstrings, 0, 0),
                                          ('.symtab', 2, symbols, 4, 16),
                                          ('.strtab', 3, strings, 0, 0)]:
        sections.append((shstrings.index(name.encode()), kind, 0, 0, len(data), len(body), link, 0, 1, entry))
        data += body
    offset = len(data)
    for section in sections:
        data += struct.pack('<10I', *section)
    data[:16] = b'\x7fELF\x01\x01\x01' + bytes(9)
    struct.pack_into('<HHIIIIIHHHHHH', data, 16, 1, 8, 1, 0, 0, offset, 0, 52, 0, 0, 40, 5, 2)
    return data


def png_info(data):
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('PNG signature')
    p, body, meta = 8, b'', None
    while p < len(data):
        size = struct.unpack_from('>I', data, p)[0]
        tag = data[p + 4:p + 8]
        chunk = data[p + 8:p + 8 + size]
        if tag == b'IHDR': meta = struct.unpack('>IIBBBBB', chunk)
        if tag == b'IDAT': body += chunk
        p += 12 + size
    return meta, zlib.decompress(body)


def bdf_rows(text, width):
    result, cp, rows, inside = {}, None, [], False
    for line in text.splitlines():
        if line.startswith('ENCODING '): cp = int(line.split()[1])
        elif line == 'BITMAP': rows, inside = [], True
        elif line == 'ENDCHAR': result[cp], inside = tuple(rows), False
        elif inside:
            value = int(line, 16)
            assert value & ((1 << ((-width) % 8)) - 1) == 0
            rows.append(value >> ((-width) % 8))
    return result


class Sunplus(unittest.TestCase):
    def test_scope_and_mapping(self):
        self.assertEqual(set(m.VARIANTS), {'12x12', '16x16', '20x24'})
        self.assertTrue(all('CP_936_' in v['member'] and 'COMMON' not in v['member'] for v in m.VARIANTS.values()))
        gs = m.mapping()
        self.assertEqual(len(gs), 7445)
        self.assertEqual(sum(0x4e00 <= cp <= 0x9fff for cp in gs), 6763)
        self.assertTrue(set(gs).isdisjoint(range(32, 127)))
        for bad in ('cp950', '24x24', '12', 'all'):
            with self.assertRaises(ValueError): m.decode(b'', bad)

    def test_source_slot_boundaries(self):
        for a, b, expected in [(0xa1, 0xa1, 0), (0xa9, 0xfe, 845), (0xb0, 0xa1, 846), (0xf7, 0xfe, 7613)]:
            self.assertEqual(m.slot_index(a, b), expected)
        for a, b in [(0xaa, 0xa1), (0xaf, 0xfe), (0xa1, 0xa0), (0xf8, 0xa1), (0xb0, 0xff), (32, 65)]:
            self.assertIsNone(m.slot_index(a, b))

    def test_ar_long_names_and_alignment(self):
        name = 'a_long_synthetic_filename.o'
        raw = b'!<arch>\n' + ar_member('//', (name + '/\n').encode()) + ar_member('/0', b'abc') + ar_member('short.o/', b'12')
        self.assertEqual(m.parse_ar(raw), {name: b'abc', 'short.o': b'12'})
        for bad in (raw[:-1], raw + b'x', b'!<thin>\n', raw.replace(b'/0 ', b'/1 ', 1),
                    b'!<arch>\n' + ar_member('x.o/', b'a') + ar_member('x.o/', b'b'),
                    b'!<arch>\n' + ar_member('../x/', b'a'),
                    b'!<arch>\n' + ar_member('/0', b'a')):
            with self.assertRaises(ValueError): m.parse_ar(bad)

    def test_elf_symbol_extent_not_section_extent(self):
        payload = b'\x0c\x0c' + bytes(range(18))
        raw = fake_elf(payload)
        self.assertEqual(m.elf_payload(raw, 'synthetic'), payload)
        with self.assertRaises(ValueError): m.elf_payload(raw, 'missing')
        for off, value in [(4, 2), (5, 2), (18, 3), (32, 255), (52 + len(payload), 1)]:
            bad = bytearray(raw); bad[off] = value
            with self.assertRaises(ValueError): m.elf_payload(bad, 'synthetic')
        with self.assertRaises(ValueError): m.elf_payload(fake_elf(payload, padding=4), 'synthetic')
        with self.assertRaises(ValueError): m.elf_payload(raw[:-1], 'synthetic')

    def test_contiguous_bits_cross_row_byte_boundaries(self):
        for w, h in ((12, 12), (16, 16), (20, 24)):
            rows = tuple((1 << (w - 1)) | (1 << (y % w)) for y in range(h))
            bits = ''.join(f'{row:0{w}b}' for row in rows)
            frame = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
            self.assertEqual(m.decode_rows(frame, w, h), rows)
            for bad in (frame[:-1], frame + b'\0'):
                with self.assertRaises(ValueError): m.decode_rows(bad, w, h)

    def test_bdf_synthetic_padding_and_layout(self):
        for w, h in ((12, 12), (16, 16), (20, 24)):
            gs = {65: ((1 << (w - 1)) | 1,) + (0,) * (h - 1)}
            text = m.bdf(gs, w, h)
            self.assertEqual(bdf_rows(text, w), gs)
            self.assertIn(f'SWIDTH {round(w * 960 / h)} 0', text)
            self.assertIn('STORAGE-CELL CONVENTION ONLY', text)
            self.assertIn('runtime advance and baseline are unverified', text)

    def test_png_synthetic_bits_and_missing_rejection(self):
        gs = {65: (0x801,) + (0,) * 11}
        meta, raw = png_info(m.png_data(gs, 12, 12, ['AA']))
        self.assertEqual(meta[:4], (25, 12, 8, 6))
        self.assertEqual(raw[1:5], b'\0\0\0\xff')
        self.assertEqual(raw[1 + 11 * 4:1 + 12 * 4], b'\0\0\0\xff')
        self.assertEqual(raw[1 + 12 * 4:1 + 13 * 4], b'\xff' * 4)
        with self.assertRaises(ValueError): m.png_data(gs, 12, 12, ['B'])

    def test_wrong_source_and_symlinks_rejected(self):
        with self.assertRaises(ValueError): m.validate_source(bytes(m.ARCHIVE_SIZE))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); (p / 'source').write_bytes(b'bad'); (p / 'link').symlink_to(p / 'source')
            for name in ('source', 'link'):
                with self.assertRaises(ValueError): m.read_source(p / name)
            (p / 'directory').mkdir(); (p / 'alias').symlink_to(p / 'directory', target_is_directory=True)
            with self.assertRaises(ValueError): m.write_outputs(p / 'alias', {'x': b'x'})

    def test_output_collision_refuses_entire_batch(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); (p / 'second').write_bytes(b'old')
            with self.assertRaises(ValueError): m.write_outputs(p, {'first': b'new', 'second': b'new'})
            self.assertFalse((p / 'first').exists())
            self.assertEqual((p / 'second').read_bytes(), b'old')
            with self.assertRaises(ValueError): m.write_outputs(p, {'../x': b'x'})
            m.write_outputs(p, {'fresh': b'new'})
            self.assertEqual((p / 'fresh').read_bytes(), b'new')

    def test_fixed_public_specimens(self):
        for name, (digest, w, h) in GOLD.items():
            if name == '12x12':
                continue  # Full HZK12 duplicate; only a local source-comparison output.
            data = (ROOT / f'assets/specimens/sunplus_sphe8202l_{name}.png').read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
            self.assertEqual(png_info(data)[0][:2], (w, h))

    @unittest.skipUnless(os.environ.get('SUNPLUS_LIBFONT'), 'Optional private source not supplied')
    def test_private_source_all_mapped_bdf_and_fixed_png(self):
        data = m.read_source(os.environ['SUNPLUS_LIBFONT'])
        for name, v in m.VARIANTS.items():
            gs = m.decode(data, name)
            self.assertEqual(len(gs), 7445)
            self.assertTrue(all(any(rows) for cp, rows in gs.items() if 0x4e00 <= cp <= 0x9fff))
            self.assertEqual(bdf_rows(m.bdf(gs, v['width'], v['height']), v['width']), gs)
            png = m.png_data(gs, v['width'], v['height'], [m.PHRASE])
            self.assertEqual(hashlib.sha256(png).hexdigest(), GOLD[name][0])
        bad = bytearray(data); bad[-1] ^= 1
        with self.assertRaises(ValueError): m.decode(bad, '12x12')


if __name__ == '__main__':
    unittest.main()
