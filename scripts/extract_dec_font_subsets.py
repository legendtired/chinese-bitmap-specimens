#!/usr/bin/env python3
"""Extract only the two audited font subsets from a local Tru64 5.0A A1 ISO.

No network access, mounting, installation or font redistribution is performed.
The exact subset contents are checked before output. ISO filenames can differ
from Rock Ridge names, so both forms are understood for this audited disc.
"""
import argparse
import hashlib
import json
from pathlib import Path

SUBSETS = {
    'IOSZHSFONTP505': ('fb034d6605b544c6dad77c09a144c60304fbd7690a0cfb2bbfa7a0901bdc5546', 5785600),
    'IOSZHTFONTP505': ('b81673452095df7eb3fda34abd3b8a74d9223fb0ea2840fd49756be250b19bf6', 7024640),
}


def records(data):
    i = 0
    while i < len(data):
        length = data[i]
        if length == 0:
            i = (i // 2048 + 1) * 2048
            continue
        if length > len(data) - i or length > 2048 - (i % 2048):
            raise ValueError('Truncated or crossing ISO directory record.')
        record = data[i:i+length]
        if len(record) < 34:
            raise ValueError('Invalid ISO directory record.')
        count = record[32]
        if count == 0 or 33 + count + (count % 2 == 0) > length:
            raise ValueError('Invalid ISO file identifier length.')
        iso_name = record[33:33+count].decode('ascii').split(';')[0]
        name = iso_name
        pos = 33 + count + (count % 2 == 0)
        while pos + 4 <= len(record):
            field_length = record[pos+2]
            if field_length < 4 or pos + field_length > len(record):
                raise ValueError('Invalid Rock Ridge field.')
            field = record[pos:pos+field_length]
            if field[:2] == b'NM' and len(field) >= 5 and field[4] == 0:
                name = field[5:].decode('ascii')
            pos += field_length
        yield dict(name=name, iso_name=iso_name, extent=int.from_bytes(record[2:6], 'little'), size=int.from_bytes(record[10:14], 'little'), directory=bool(record[25] & 2))
        i += length


def extract(iso, output):
    iso, output = Path(iso), Path(output)
    if any((output / name).exists() or (output / name).is_symlink()
           for name in (*SUBSETS, 'extraction-report.json')):
        raise ValueError('Refusing to overwrite existing extraction files.')
    with iso.open('rb') as stream:
        def read(start, length):
            if length > 8000000 or start < 0:
                raise ValueError('Unexpected extent size.')
            stream.seek(start)
            data = stream.read(length)
            if len(data) != length:
                raise ValueError('ISO is truncated.')
            return data
        pvd = read(32768, 2048)
        if pvd[:7] != b'\x01CD001\x01' or pvd[40:72].rstrip(b' ') != b'V5.0Ar1094_A1':
            raise ValueError('Not the audited Tru64 5.0A Associated Products Volume 1.')
        current = next(records(pvd[156:190]), None)
        if current is None or not current['directory'] or current['iso_name'] != '\x00':
            raise ValueError('Invalid ISO root directory record.')
        for component in ('WORLDWID', 'KIT'):
            listing = list(records(read(current['extent'] * 2048, current['size'])))
            matches = [r for r in listing if r['iso_name'].upper() == component and r['directory']]
            if len(matches) != 1:
                raise ValueError(f'Missing or ambiguous ISO directory: {component}')
            current = matches[0]
        listing = list(records(read(current['extent'] * 2048, current['size'])))
        contents, details = {}, []
        for name, (sha, length) in SUBSETS.items():
            matches = [r for r in listing if r['name'] == name and not r['directory']]
            if len(matches) != 1 or matches[0]['size'] != length:
                raise ValueError(f'Missing or unexpected font subset: {name}')
            r = matches[0]
            data = read(r['extent'] * 2048, length)
            if hashlib.sha256(data).hexdigest() != sha:
                raise ValueError(f'Hash mismatch: {name}')
            contents[name] = data
            details.append(dict(file=name, bytes=length, sha256=sha))
    output.mkdir(parents=True, exist_ok=True)
    for name, data in contents.items():
        with (output/name).open('xb') as f:
            f.write(data)
    with (output/'extraction-report.json').open('x', encoding='utf-8') as f:
        json.dump({'volume':'V5.0Ar1094_A1', 'subsets':details, 'note':'Only selected subset hashes checked, not a whole-ISO hash.'}, f, indent=2)
        f.write('\n')
    return details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iso', help='Local AG-RHB7B-BE.iso')
    parser.add_argument('output', help='Directory for the two compressed tar font subsets')
    args = parser.parse_args()
    try:
        result = extract(args.iso, args.output)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    print(f'Extracted and SHA256-verified {len(result)} font subsets; no fonts installed.')

if __name__ == '__main__':
    main()
