#!/usr/bin/env python3
"""Export the verified 1999 Nokia 6150 PPM E bitmap to local-research BDF.

Offline, standard-library only, exact size/SHA-256 allowlist. Reads firmware
as data, never executes it. No source glyphs are embedded in this script.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

SOURCE_SIZE = 656080
SOURCE_SHA256 = '6fc1ac3669091c615d22ebccb39ee0e056239fd1a0ab99a44053a52ad26cc444'
INDEXED_SHA256 = '4bc83b493ad6fd9855abf9adea471ecfa9ab9a5d542fbb706633cc57dd18925a'
SOURCE_PAGE = 'https://archive.org/details/Nokia_DCT3_firmwares'
FORMAT_REFERENCE = 'https://pjmor.com/extract-nokia-dct3-fonts/'
PPM_HEADER = b'PPM\x00V  5.17\n01-07-99\nNSM-1\n(c) NMP.'
SAFE_DIR_FD = (hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY') and hasattr(os, 'O_NONBLOCK')
               and os.open in os.supports_dir_fd and os.mkdir in os.supports_dir_fd
               and os.stat in os.supports_dir_fd and os.stat in os.supports_follow_symlinks
               and os.unlink in os.supports_dir_fd)


class ConversionError(ValueError):
    pass


def require(ok, message):
    # Deliberately not assert: every check also runs under python -O.
    if not ok:
        raise ConversionError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def reject_symlinks(path):
    for component in (Path(path).absolute(), *Path(path).absolute().parents):
        require(not component.is_symlink(), f'Symbolic links are not accepted: {component}')


def load_font(path):
    """Open every path component without following links; read a regular file."""
    require(SAFE_DIR_FD, 'Safe file access requires POSIX O_NOFOLLOW and dir_fd support')
    path = Path(path).absolute()
    reject_symlinks(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, flags, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=parent)
        with os.fdopen(fd, 'rb') as handle:
            info = os.fstat(handle.fileno())
            require(stat.S_ISREG(info.st_mode), 'Input must be a regular file')
            require(info.st_size == SOURCE_SIZE, 'Unsupported input size')
            data = handle.read(SOURCE_SIZE + 1)
    except FileNotFoundError as error:
        raise ConversionError('Missing input file') from error
    finally:
        os.close(parent)
    require(len(data) == SOURCE_SIZE and sha256(data) == SOURCE_SHA256,
            'SHA-256 mismatch; unsupported or modified input')
    return data


def integer(data, offset, size):
    require(size in (2, 4) and 0 <= offset <= len(data) - size,
            'Read outside normalized PPM')
    return int.from_bytes(data[offset:offset + size], 'big')


def normalize(data):
    """Remove nine-byte Wintesla headers, checking bounded continuous blocks."""
    require(0 < len(data) <= SOURCE_SIZE, 'Invalid Wintesla input size')
    result, pos, next_address, blocks = bytearray(), 0, None, 0
    while pos < len(data):
        header = data[pos:pos + 9]
        require(len(header) == 9 and header[0] == 11, 'Invalid Wintesla block header')
        address = int.from_bytes(header[1:4], 'big')
        length = int.from_bytes(header[5:8], 'big')
        require(0 < length <= 8192 and pos + 9 + length <= len(data), 'Invalid block length')
        require(address + length <= 1 << 24, 'Wintesla address overflow')
        require(next_address is None or address == next_address, 'Discontinuous block address')
        result.extend(data[pos + 9:pos + 9 + length])
        next_address = address + length
        pos += 9 + length
        blocks += 1
    return bytes(result), blocks


def parse_ppm(data):
    """Bounded low-level parser for tests; public export always hash-gates first."""
    require(len(data) <= 655360 and data.startswith(PPM_HEADER), 'Unexpected PPM header or size')
    require(data.count(b'FONTfconv') == 1, 'Expected one FONT chunk')
    start = data.index(b'FONTfconv') + 28
    count = integer(data, start, 4)
    require(count == 4, 'Unexpected number of font records')
    records_end = start + 4 + 44 * count
    require(records_end <= len(data), 'Truncated font records')
    fonts, spacers, previous_end = [], 0, records_end
    for i in range(count):
        offset = start + 4 + 44 * i
        index = offset + integer(data, offset + 8, 4)
        groups = integer(data, offset + 14, 2) + 1
        require(previous_end <= index and index + 8 * groups <= len(data),
                'Character index outside PPM or overlapping records')
        try:
            name = (data[offset + 24:offset + 35].split(b'\0', 1)[0].decode('ascii') + '-'
                    + data[offset + 35:offset + 41].split(b'\0', 1)[0].decode('ascii'))
        except UnicodeDecodeError as error:
            raise ConversionError('Invalid font record name') from error
        fonts.append((name, index, groups))
        spacers += integer(data, offset + 12, 2) + 1
        previous_end = index + 8 * groups
    cursor = previous_end + spacers * 8
    matrices, descriptors_end = {}, cursor + 12 * 12
    require(descriptors_end <= len(data), 'Truncated width matrix descriptors')
    previous_end = descriptors_end
    for i in range(12):
        offset = cursor + 12 * i
        require(data[offset + 4:offset + 7] == b'\x00\x01\x00', 'Invalid width matrix descriptor')
        origin = offset + integer(data, offset, 4)
        width = integer(data, offset + 6, 2)
        height = integer(data, offset + 8, 4)
        require(1 <= width <= 12 and 0 < height < 1000000 and height % 8 == 0,
                'Invalid matrix dimensions')
        require(width not in matrices, 'Duplicate width matrix')
        end = origin + width * (height // 8)
        require(previous_end <= origin and end <= len(data), 'Matrix outside PPM or overlapping data')
        matrices[width] = (origin, height)
        previous_end = end
    require(set(matrices) == set(range(1, 13)), 'Unexpected matrix widths')
    selected = [font for font in fonts if font[0] == 'large-bold']
    require(len(selected) == 1, 'Expected one large-bold font')
    _, index, groups = selected[0]
    glyphs = {}
    for j in range(groups):
        offset = index + j * 8
        first, last = integer(data, offset, 2), integer(data, offset + 2, 2)
        packed = integer(data, offset + 4, 4)
        width = ((packed >> 10) & 15) + 1
        height, baseline, origin = (packed >> 5) & 31, packed & 31, packed >> 14
        require(first <= last and width in matrices and 0 < height <= 31 and baseline <= height,
                'Invalid character group')
        require(last < 0xD800 or first > 0xDFFF, 'Invalid Unicode surrogate mapping')
        matrix, matrix_height = matrices[width]
        require(origin + (last - first + 1) * height <= matrix_height,
                'Glyph outside width matrix')
        for codepoint in range(first, last + 1):
            require(codepoint not in glyphs, 'Duplicate Unicode mapping')
            y = origin + (codepoint - first) * height
            rows = []
            for dy in range(height):
                row = 0
                for x in range(width):
                    value = data[matrix + ((y + dy) // 8) * width + x]
                    row = (row << 1) | ((value >> ((y + dy) % 8)) & 1)
                rows.append(row)
            glyphs[codepoint] = {'width': width, 'height': height,
                                 'baseline': baseline, 'rows': rows}
    return glyphs, start


def indexed_digest(glyphs):
    """Digest codepoint, source metrics and row-MSB integer values, not BDF text."""
    return sha256(b''.join(cp.to_bytes(4, 'big') + bytes((g['width'], g['height'], g['baseline']))
                          + b''.join(row.to_bytes((g['width'] + 7) // 8, 'big') for row in g['rows'])
                          for cp, g in sorted(glyphs.items())))


def gb2312_hanzi():
    result = set()
    for high in range(0xB0, 0xF8):
        for low in range(0xA1, 0xFF):
            try:
                char = bytes((high, low)).decode('gb2312', errors='strict')
            except UnicodeDecodeError:
                continue
            require(len(char) == 1 and 0x4E00 <= ord(char) <= 0x9FFF, 'Unexpected GB2312 mapping')
            result.add(ord(char))
    require(len(result) == 6763, 'Unexpected GB2312 Hanzi count')
    return result


def validate_glyphs(glyphs):
    cjk = {cp: g for cp, g in glyphs.items() if 0x4E00 <= cp <= 0x9FFF}
    require(len(glyphs) == 9385 and len(cjk) == 9004, 'Unexpected Unicode coverage')
    require(all((g['width'], g['height'], g['baseline']) == (11, 12, 11)
                and any(g['rows']) for g in cjk.values()), 'Unexpected Chinese dimensions or blank glyph')
    require(gb2312_hanzi() <= cjk.keys(), 'Missing GB2312 Hanzi')
    require(indexed_digest(glyphs) == INDEXED_SHA256, 'Decoded native bitmap checksum mismatch')


def decode(data):
    require(len(data) == SOURCE_SIZE and sha256(data) == SOURCE_SHA256,
            'Unsupported input: supply verified nsm1ny_5.17e, not an EXE, ZIP or another version')
    normalized, blocks = normalize(data)
    require(blocks == 80 and len(normalized) == 655360, 'Unexpected normalized PPM size or block count')
    glyphs, start = parse_ppm(normalized)
    validate_glyphs(glyphs)
    return glyphs, {
        'source_file': 'nsm1ny_5.17e', 'source_bytes': len(data), 'source_sha256': SOURCE_SHA256,
        'source_page': SOURCE_PAGE, 'format_reference': FORMAT_REFERENCE,
        'firmware_version': '5.17', 'firmware_date': '1999-07-01', 'device_code': 'NSM-1',
        'language_pack': 'E', 'wintesla_blocks': blocks, 'normalized_bytes': len(normalized),
        'font_data_offset': start, 'font_record_name': 'large-bold', 'glyphs': len(glyphs),
        'cjk_hanzi': 9004, 'gb2312_hanzi': 6763, 'cjk_cell': [11, 12],
        'indexed_bitmap_sha256': INDEXED_SHA256,
        'encoding': 'Original Unicode range records, no charset guessing',
        'storage': 'Width-specific matrices; each byte holds eight vertical pixels, LSB at top',
        'metrics': 'DWIDTH is matrix width; the source low-five-bit metric is interpreted as baseline. '
                   'BBX y offset is that field minus height. '
                   'No additional device spacing or hardware line height is inferred.',
        'license_notice': 'Historical proprietary glyphs; export does not establish redistribution permission.'}


def make_bdf(glyphs):
    require(bool(glyphs), 'Cannot export an empty font')
    for cp, g in glyphs.items():
        require(type(cp) is int and 0 <= cp <= 0xFFFF and not 0xD800 <= cp <= 0xDFFF,
                'Invalid Unicode mapping')
        require(isinstance(g, dict) and set(g) == {'width', 'height', 'baseline', 'rows'},
                'Invalid glyph fields')
        w, h, baseline, rows = g['width'], g['height'], g['baseline'], g['rows']
        require(all(type(v) is int for v in (w, h, baseline)) and 1 <= w <= 12
                and 1 <= h <= 31 and 0 <= baseline <= h, 'Invalid glyph dimensions or baseline')
        require(isinstance(rows, (tuple, list)) and len(rows) == h
                and all(type(row) is int and 0 <= row < 1 << w for row in rows),
                'Invalid glyph row count or pixels')
    ascent = max(g['baseline'] for g in glyphs.values())
    descent = max(g['height'] - g['baseline'] for g in glyphs.values())
    width, height = max(g['width'] for g in glyphs.values()), ascent + descent
    lines = [
        'STARTFONT 2.1', 'COMMENT Direct stored pixels; no fallback, scaling or glyph alteration.',
        f'COMMENT SOURCE_SHA256 {SOURCE_SHA256}',
        'COMMENT DWIDTH is matrix width; device inter-character spacing is not inferred.',
        'COMMENT Source low-five-bit metric is interpreted as baseline; BBX y = field - height.',
        'COMMENT SIZE is the exported ascent/descent envelope, not proven hardware line height.',
        f'FONT -archive-nokia_dct3_1999-medium-r-normal--{height}-{height * 10}-72-72-P-0-ISO10646-1',
        f'SIZE {height} 72 72', f'FONTBOUNDINGBOX {width} {height} 0 {-descent}',
        'STARTPROPERTIES 8', f'FONT_ASCENT {ascent}', f'FONT_DESCENT {descent}',
        f'PIXEL_SIZE {height}', f'POINT_SIZE {height * 10}', 'RESOLUTION_X 72', 'RESOLUTION_Y 72',
        'CHARSET_REGISTRY "ISO10646"', 'CHARSET_ENCODING "1"', 'ENDPROPERTIES', f'CHARS {len(glyphs)}']
    for cp, g in sorted(glyphs.items()):
        w, h = g['width'], g['height']
        stride = (w + 7) // 8
        lines.extend([f'STARTCHAR uni{cp:04X}', f'ENCODING {cp}', f'SWIDTH {round(w / height * 1000)} 0',
                      f'DWIDTH {w} 0', f'BBX {w} {h} 0 {g["baseline"] - h}', 'BITMAP'])
        lines.extend(f'{row << (stride * 8 - w):0{stride * 2}X}' for row in g['rows'])
        lines.append('ENDCHAR')
    return ('\n'.join(lines + ['ENDFONT', ''])).encode('ascii')


def output_path(path, suffix):
    path = Path(path).absolute()
    require('..' not in path.parts, 'Output traversal components are not accepted')
    reject_symlinks(path)
    root = Path.cwd() / 'local-research'
    reject_symlinks(root)
    require(root in path.parents, 'Output must be inside local-research under the current working directory')
    require(path.suffix.lower() == suffix, f'Output must have a {suffix} extension')
    require(not path.exists() and not path.is_symlink(),
            'Output must not exist; existing files are never overwritten')
    return path


def write_outputs(output, content, report, report_content):
    """Exclusive creations through held directory handles; remove only our files on failure."""
    require(SAFE_DIR_FD, 'Safe output requires POSIX O_NOFOLLOW and dir_fd support')
    output, report = output_path(output, '.bdf'), output_path(report, '.json')
    require(output != report, 'Output BDF and report must differ')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open('.', flags)
    created = []
    try:
        for path, value in ((output, content), (report, report_content)):
            parent = os.dup(root)
            try:
                for part in path.relative_to(Path.cwd()).parts[:-1]:
                    try:
                        os.mkdir(part, mode=0o700, dir_fd=parent)
                    except FileExistsError:
                        pass
                    child = os.open(part, flags, dir_fd=parent)
                    os.close(parent)
                    parent = child
                fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=parent)
                with os.fdopen(fd, 'wb') as handle:
                    info = os.fstat(handle.fileno())
                    created.append((os.dup(parent), path.name, info.st_dev, info.st_ino))
                    handle.write(value)
            finally:
                os.close(parent)
    except BaseException:
        for parent, name, device, inode in created:
            try:
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if (info.st_dev, info.st_ino) == (device, inode):
                    os.unlink(name, dir_fd=parent)
            except OSError:
                pass
        raise
    finally:
        for parent, _, _, _ in created:
            os.close(parent)
        os.close(root)


def export(source, output, report=None, cjk_only=False):
    source, output = Path(source), Path(output)
    report = Path(report) if report is not None else output.with_suffix('.json')
    require(source.absolute() not in (output.absolute(), report.absolute()), 'Output cannot overwrite the input')
    output, report = output_path(output, '.bdf'), output_path(report, '.json')
    require(output != report, 'Output BDF and report must differ')
    glyphs, info = decode(load_font(source))
    if cjk_only:
        glyphs = {cp: g for cp, g in glyphs.items() if 0x4E00 <= cp <= 0x9FFF}
    content = make_bdf(glyphs)
    info.update({'exported_glyphs': len(glyphs), 'cjk_only': cjk_only,
                 'bdf_sha256': sha256(content),
                 'bdf_ascent_descent': [max(g['baseline'] for g in glyphs.values()),
                                        max(g['height'] - g['baseline'] for g in glyphs.values())]})
    # No output creation until all parsing, coverage, native-pixel and BDF checks pass.
    write_outputs(output, content, report, (json.dumps(info, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    return info


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path, required=True, help='local verified nsm1ny_5.17e')
    parser.add_argument('--output', type=Path, required=True, help='new .bdf inside ./local-research')
    parser.add_argument('--report', type=Path, help='new .json inside ./local-research; default: output stem.json')
    parser.add_argument('--cjk-only', action='store_true', help='export only the 9004 original Hanzi records')
    args = parser.parse_args(argv)
    try:
        info = export(args.font, args.output, args.report, args.cjk_only)
    except (OSError, ValueError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
