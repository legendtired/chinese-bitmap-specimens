#!/usr/bin/env python3
"""Re-encode the verified ELISA 10x8 BDF to Unicode without changing pixels.

The source package and fonts are not included. Personal-use export only, subject
 to the original license. No raw-FNT guessing or approximate substitutions.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tarfile

ARCHIVE_SHA256 = "bb62d48db7a26339313947b623376bb18d92196424ee1545ef54ed8b0200dfba"
ARCHIVE_SIZE = 125292
SOURCE_SHA256 = "5f1c61f4d2962d3bfc4128708eb48b3885e26eb797ebe986027eb8ddab39d524"
SOURCE_SIZE = 852905
GLYPH_COUNT = 6877
SAMPLE_HAN = "視野無限廣，窗外有藍天。"
SAMPLE_FULLWIDTH = "０１２３４５６７８９　ＡａＢｂ　ＧｇＭｍ"
GLYPH_RE = re.compile(r"^STARTCHAR ([^\n]+)\n(.*?)^ENDCHAR\n", re.M | re.S)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_verified_source(path: Path) -> tuple[bytes, str, str]:
    """Accept only the audited original BDF or its complete original archive."""
    if path.stat().st_size > SOURCE_SIZE:
        raise ValueError("Input is larger than either verified ELISA source.")
    payload = path.read_bytes()
    digest = sha256(payload)
    if len(payload) == SOURCE_SIZE and digest == SOURCE_SHA256:
        return payload, "elisau10.bdf", digest
    if len(payload) != ARCHIVE_SIZE or digest != ARCHIVE_SHA256:
        raise ValueError("Unverified input: expected original elisau10.tgz or elisau10.bdf with documented SHA256.")
    # Read only a regular member in memory; never extract paths from the archive.
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        members = [m for m in archive.getmembers() if m.name == "elisau10.bdf"]
        if len(members) != 1 or not members[0].isfile() or members[0].size != SOURCE_SIZE:
            raise ValueError("Archive does not contain exactly one expected regular BDF.")
        stream = archive.extractfile(members[0])
        if stream is None:
            raise ValueError("Cannot read BDF member.")
        data = stream.read(SOURCE_SIZE + 1)
    if len(data) != SOURCE_SIZE or sha256(data) != SOURCE_SHA256:
        raise ValueError("Archive BDF checksum mismatch.")
    return data, "elisau10.tgz", digest


def jis_to_unicode(code: int) -> int:
    """Strict JIS X 0208 mapping, not CP932 and not JIS X 0213."""
    if not (0x21 <= code >> 8 <= 0x7E and 0x21 <= code & 0xFF <= 0x7E):
        raise ValueError(f"Invalid two-byte JIS code: {code:#x}")
    encoded = b"\x1b$B" + code.to_bytes(2, "big") + b"\x1b(B"
    try:
        char = encoded.decode("iso2022_jp", errors="strict")
    except UnicodeError as exc:
        raise ValueError(f"Unassigned JIS X 0208 code: {code:#x}") from exc
    if len(char) != 1 or char.encode("iso2022_jp", errors="strict") != encoded:
        raise ValueError(f"JIS code does not round-trip: {code:#x}")
    return ord(char)


def convert_bdf(data: bytes) -> tuple[bytes, dict]:
    """Guard hash even for API callers; preserve every bitmap/metric verbatim."""
    if len(data) != SOURCE_SIZE or sha256(data) != SOURCE_SHA256:
        raise ValueError("Source BDF SHA256 mismatch.")
    text = data.decode("ascii")
    records = list(GLYPH_RE.finditer(text))
    if len(records) != GLYPH_COUNT or f"CHARS {GLYPH_COUNT}\n" not in text:
        raise ValueError("Unexpected glyph count.")
    seen = set()
    empty = []

    def convert_glyph(match: re.Match) -> str:
        name, body = match.groups()
        encodings = re.findall(r"^ENCODING (\d+)$", body, re.M)
        if len(encodings) != 1:
            raise ValueError(f"Invalid ENCODING in {name}.")
        jis = int(encodings[0])
        if int(name, 16) != jis:
            raise ValueError("Glyph name and JIS code disagree.")
        cp = jis_to_unicode(jis)
        if cp in seen:
            raise ValueError("Duplicate Unicode mapping.")
        seen.add(cp)
        if "BBX 10 8 0 -2\n" not in body or "DWIDTH 10 0\n" not in body:
            raise ValueError("Unexpected glyph metrics.")
        rows = body.split("BITMAP\n", 1)[1].splitlines()
        if len(rows) != 8 or any(not re.fullmatch(r"[0-9a-fA-F]{4}", row) for row in rows):
            raise ValueError("Invalid bitmap rows.")
        # All eight original columns precede the two cell-margin columns.
        if any(int(row, 16) & 0xFF for row in rows):
            raise ValueError("Unexpected pixels outside the original 8-column glyph.")
        if not any(int(row, 16) for row in rows):
            empty.append(f"U+{cp:04X}")
        body = re.sub(r"^ENCODING \d+$", f"ENCODING {cp}", body, flags=re.M)
        return f"STARTCHAR uni{cp:04X}\n{body}ENDCHAR\n"

    text = GLYPH_RE.sub(convert_glyph, text)
    changes = {
        "-JISX0208.1983-0\n": "-ISO10646-1\n",
        'CHARSET_REGISTRY "JISX0208.1983"\n': 'CHARSET_REGISTRY "ISO10646"\n',
        'CHARSET_ENCODING "0"\n': 'CHARSET_ENCODING "1"\n',
        "DEFAULT_CHAR 8481\n": f"DEFAULT_CHAR {jis_to_unicode(8481)}\n",
    }
    for old, new in changes.items():
        if text.count(old) != 1:
            raise ValueError(f"Unexpected BDF header field: {old.strip()}")
        text = text.replace(old, new, 1)
    text = text.replace("STARTFONT 2.1\n", "STARTFONT 2.1\nCOMMENT Unicode re-encoding only; all source bitmaps and metrics preserved.\n", 1)
    output = text.encode("ascii")
    report = {
        "format": "BDF 2.1",
        "source_bdf_sha256": SOURCE_SHA256,
        "output_sha256": sha256(output),
        "glyph_count": len(seen),
        "blank_glyphs": empty,
        "source_encoding": "JISX0208.1983-0",
        "output_encoding": "ISO10646-1",
        "mapping": "Python iso2022_jp strict, bidirectional round-trip checked",
        "font_bounding_box": [10, 8, 0, -2],
        "original_glyph_grid": [8, 8],
        "advance": [10, 0],
        "ascent": 6,
        "descent": 2,
        "baseline": "Source convention preserved: y=-2..5, ascent=6, descent=2; no vertical translation.",
        "original_size_and_pixel_size": 10,
        "size_note": "The source XLFD/SIZE/PIXEL_SIZE say 10; the actual stored height is 8 pixels.",
        "bitmap_and_metrics_changed": False,
        "sample_missing": {
            "han": [c for c in SAMPLE_HAN if ord(c) not in seen],
            "fullwidth": [c for c in SAMPLE_FULLWIDTH if ord(c) not in seen],
        },
        "ascii_codepoints_present": sum(cp in seen for cp in range(32, 127)),
        "license_notice": "Personal use only under the original ELISA terms. Retain the complete original package. Do not distribute this re-encoded font or subsets; no commercial-use permission is granted.",
    }
    return output, report


def preflight_outputs(output: Path, report_path: Path, source: Path | None = None) -> tuple[Path, Path]:
    """Check destinations and both parents before creating either output."""
    paths = (output, report_path)
    resolved = [p.resolve() for p in paths]
    if resolved[0] == resolved[1]:
        raise ValueError("Font and report must have different destinations, including resolved aliases.")
    for path, real in zip(paths, resolved):
        if source is not None and real == source.resolve():
            raise ValueError("Output/report must not replace the input.")
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Refusing to overwrite: {path}")
        if not path.parent.is_dir():
            raise ValueError(f"Output/report parent directory does not exist: {path.parent}")
    return paths


def write_outputs(output: Path, report_path: Path, data: bytes, report: dict,
                  source: Path | None = None) -> None:
    """Create exclusively; rollback only files whose dev/inode we still own."""
    paths = preflight_outputs(output, report_path, source)
    payloads = (data, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    opened = []
    try:
        for path in paths:
            stream = path.open("xb")
            stat = os.fstat(stream.fileno())
            opened.append((path, stream, (stat.st_dev, stat.st_ino)))
        for (_, stream, _), payload in zip(opened, payloads):
            stream.write(payload)
            stream.flush()
        for _, stream, _ in opened:
            stream.close()
    except BaseException:
        for path, stream, identity in opened:
            try:
                stream.close()
            except OSError:
                pass
            try:
                stat = path.lstat()
                if (stat.st_dev, stat.st_ino) == identity:
                    path.unlink()
            except OSError:
                pass
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Verified elisau10.tgz (preferred) or original elisau10.bdf")
    parser.add_argument("--output", required=True, type=Path, help="New local Unicode BDF path; never overwritten")
    parser.add_argument("--report", type=Path, help="New JSON report (default: OUTPUT.json)")
    args = parser.parse_args(argv)
    report_path = args.report or Path(str(args.output) + ".json")
    try:
        preflight_outputs(args.output, report_path, args.source)
        data, kind, digest = read_verified_source(args.source)
        output, report = convert_bdf(data)
        report.update(input_kind=kind, input_sha256=digest)
        write_outputs(args.output, report_path, output, report, args.source)
    except (ValueError, OSError, tarfile.TarError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {report['glyph_count']} Unicode glyphs: {args.output}")
    print(f"Report: {report_path}")
    print("Personal use only; retain the original complete package and license.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
