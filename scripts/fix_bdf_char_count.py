#!/usr/bin/env python3
"""Repair a BDF CHARS count without changing any glyph or metadata bytes."""
import argparse
from pathlib import Path
import re


def fix_count(data):
    lines = data.splitlines(keepends=True)
    counts = [i for i, line in enumerate(lines) if re.match(rb'^CHARS[ \t]+[0-9]+\s*$', line)]
    starts = sum(line.startswith(b'STARTCHAR ') for line in lines)
    ends = sum(line.rstrip(b'\r\n') == b'ENDCHAR' for line in lines)
    if not data.startswith(b'STARTFONT ') or len(counts) != 1 or not starts or starts != ends:
        raise ValueError('Expected one BDF font, one CHARS line and balanced nonempty glyph records')
    if sum(line.rstrip(b'\r\n') == b'ENDFONT' for line in lines) != 1:
        raise ValueError('Expected exactly one ENDFONT')
    i = counts[0]
    old = int(lines[i].split()[1])
    # Replace only decimal digits, retaining all other bytes and original line endings.
    lines[i] = re.sub(rb'^(CHARS[ \t]+)[0-9]+', lambda m: m[1] + str(starts).encode(), lines[i])
    return b''.join(lines), old, starts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error('Use a different output path; preserve the original converter output')
    try:
        data, old, new = fix_count(args.input.read_bytes())
        with args.output.open('xb') as output:
            output.write(data)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'{exc}\n')
    print(f'CHARS {old} -> {new}; all other bytes unchanged')


if __name__ == '__main__':
    main()
