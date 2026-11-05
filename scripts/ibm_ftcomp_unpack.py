#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Deark-derived portions: Copyright (C) 2026 Jason Summers.
# Algorithm credit: Dimitriy Ryazantcev and Jason Summers.
# See vendor/ftcomp/COPYING and vendor/ftcomp/README.md.
"""Static, bounded FTCOMP/PACK2 font extractor.
Python reimplementation informed by Deark's MIT-licensed algorithm by
Dimitriy Ryazantcev and Jason Summers. No legacy binary is executed.
Bootstrap tables are numeric data from Deark's foreign/ftcompdata.h.
"""
import re, zlib, struct, hashlib, json
from pathlib import Path
from bisect import bisect_left
HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(str(message))


def u16(b, p=0):
    require(0 <= p <= len(b) - 2, ('u16 bounds', p, len(b)))
    return int.from_bytes(b[p:p + 2], 'little')

def u32(b, p=0):
    require(0 <= p <= len(b) - 4, 'invalid FTCOMP structure')
    return int.from_bytes(b[p:p + 4], 'little')

def ft_sort(q, w, lo=0, hi=None):
    """Original hybrid quick/insertion sorting tie order is codec-significant."""
    if hi is None:
        hi = len(q) - 1
    require(len(q) == len(w) and 0 <= lo <= len(q) and -1 <= hi < len(q),
            'sort bounds')
    stack = [(lo, hi)]
    while stack:
        lo, hi = stack.pop()
        while lo < hi:
            if hi - lo <= 16:
                for p in range(lo + 1, hi + 1):
                    key, kw = (q[p], w[p])
                    j = lo
                    while j < p and w[j] < kw:
                        j += 1
                    q[j + 1:p + 1] = q[j:p]
                    w[j + 1:p + 1] = w[j:p]
                    q[j], w[j] = (key, kw)
                break
            pivot = w[(hi + lo) // 2]
            l, r = (lo, hi)
            while l <= r:
                while w[l] < pivot:
                    l += 1
                while w[r] > pivot:
                    r -= 1
                if l <= r:
                    q[l], q[r] = (q[r], q[l])
                    w[l], w[r] = (w[r], w[l])
                    l += 1
                    r -= 1
            if r - lo < hi - l:
                if l < hi:
                    stack.append((l, hi))
                hi = r
            else:
                if lo < r:
                    stack.append((lo, r))
                lo = l

def tree(weights):
    weights = list(weights)
    require(2 <= len(weights) <= 433 and all(0 <= w <= 65535 for w in weights),
            'Huffman weight bounds')
    q = [0] * 512
    n = 0
    units = 0
    last = 0
    for sym, w in enumerate(weights):
        carry = sym
        if w:
            if w == 1:
                carry = last
                q[n] = q[units]
                n += 1
                q[units] = sym
                units += 1
            else:
                q[n] = sym
                n += 1
        last = carry
    require(n, 'empty Huffman tree')
    if n == 1:
        q[1] = q[units]
        n = 2
        q[units] = last
        units += 1
        weights[last] = 1
    q = q[:n]
    w = [weights[i] for i in q]
    ft_sort(q, w, units, n - 1)
    while len(q) > 1:
        a, b = q[:2]
        merged = w[0] + w[1] & 65535
        del q[:2]
        del w[:2]
        pos = bisect_left(w, merged)
        q.insert(pos, (b, a))
        w.insert(pos, merged)
    return q[0]

class Bits:

    def __init__(self, b, p):
        self.b = b
        self.p = p * 8

    def get(self, n=1):
        require(0 <= n <= 32 and 0 <= self.p and (self.p + n <= len(self.b) * 8), ('bit EOF', self.p, n, len(self.b)))
        v = 0
        for _ in range(n):
            v = v << 1 | self.b[self.p >> 3] >> 7 - (self.p & 7) & 1
            self.p += 1
        return v

    def symbol(self, t):
        for _ in range(64):
            if isinstance(t, int):
                return t
            require(isinstance(t, tuple) and len(t) == 2, 'invalid Huffman node')
            t = t[self.get()]
        raise ValueError('Huffman depth')

class Rank:

    def __init__(self):
        self.a, self.b = (0, 1)

    def get(self, d):
        if d == 256:
            v = self.a
        elif d == 257:
            v = self.b
            self.b = self.a
        else:
            v = d
            lo, hi = sorted((self.a, self.b))
            if lo <= v:
                v += 1
            if hi <= v:
                v += 1
            self.b = self.a
        self.a = v
        return v

def load_tables():
    table = (HERE / 'vendor' / 'ftcomp' / 'ftcompdata.h').read_bytes()
    require(hashlib.sha256(table).hexdigest() == 'b71c7e60880e793f3cf1435df1eba07ebbd19975794a11df3e99a592df3cddf7', 'bootstrap table hash mismatch')
    s = table.decode('ascii').split('{', 1)[1].split('}', 1)[0]
    blob = zlib.decompress(bytes(map(int, re.findall('\\d+', s))))
    require(len(blob) == 7842, 'invalid FTCOMP structure')
    nums = list(struct.unpack('<1428H', blob[:2856]))
    return (nums[:433], nums[433:866], nums[866:1299], nums[1299:], blob[2856:])

class Decoder:

    def __init__(self):
        desc, digit, self.types, self.extra, self.preset = load_tables()
        self.descriptor = tree(desc)
        digit[252] = 4
        digit[253] = 4
        digit[254] = 0
        digit[255] = 0
        digit[257] = 120
        self.types[320] = 1
        self.extra[64] = 2
        self.digit = tree(digit)
        self.ring = bytearray(65536)
        self.ring[:len(self.preset)] = self.preset
        self.hpos = len(self.preset)
        self.streampos = self.hpos
        self.logs = []

    def scaled(self, raw, a, b):
        w = [r * (b if typ else a) & 65535 for r, typ in zip(raw, self.types)]
        m = max(w)
        scale = 65535 // m if m >= 256 else 0
        if scale:
            w = [max(1, x * scale >> 8) if x else 0 for x in w]
        return tree(w)

    def stage1(self, b, p):
        length = u16(b, p)
        if length == 65535:
            n = u16(b, p + 2)
            require(p + 4 + n <= len(b), 'invalid FTCOMP structure')
            return (b[p + 4:p + 4 + n], p + 4 + n)
        require(p + 6 <= len(b), 'stage1 header bounds')
        m0, m1, m2, m3 = b[p + 2:p + 6]
        br = Bits(b, p + 6)
        raw = []
        while len(raw) < 433:
            v = br.symbol(self.descriptor)
            if v == 256:
                raw.extend([0] * min(16, 433 - len(raw)))
            else:
                raw.append(v & 255)
        A = self.scaled(raw, m0, m1)
        B = A if m2 == m1 and m0 == m3 or not (m2 or m3) else self.scaled(raw, m3, m2)
        out = bytearray()
        chain = 0
        table = 0
        est = self.streampos
        lastform = 0
        alt = False
        ranks = [Rank() for _ in range(6)]
        lenpos = [0] * 32
        matchdist = [0] * 32

        def byte(p):
            # The codec initializes unavailable local history to zero.
            return out[p] if 0 <= p < len(out) else 0

        def word(p):
            return byte(p) | byte(p + 1) << 8

        def putword(v):
            out.extend((v & 255, v >> 8 & 255))

        def push(r, v):
            r.insert(0, v & 65535)
            r.pop()

        def promote(r, n, v):
            r.pop(n)
            r.insert(0, v & 65535)
        while len(out) < length:
            delta = 0
            if chain == 0:
                before = len(out)
                sym = br.symbol(B if table else A)
                require(0 <= sym < len(self.types), 'stage1 symbol bounds')
                table = self.types[sym]
                if sym < 256:
                    delta = 1
                    out.append(sym)
                    if sym == 158:
                        out.append(255)
                elif sym < 385:
                    off = sym - 256
                    out.extend((158, off))
                    chain = self.extra[off]
                    if chain:
                        if chain <= 2:
                            delta = (off & 63) + 3
                        alt = off == 64
                        push(lenpos, before + 1)
                elif sym < 401:
                    v = word(before + 383 - sym)
                    putword(v)
                    delta = 1 if v & 255 == 158 else 2
                    push(matchdist, v)
                elif sym >= 417:
                    n = sym - 417
                    src = lenpos[n]
                    out.append(158)
                    pair = word(src)
                    src0 = pair & 255
                    putword(pair)
                    if src0 == 128:
                        putword(word(src + 2))
                    elif src0 & 64:
                        out.append(byte(src + 2))
                    delta = (src0 & 63) + 3 if src0 <= 128 and self.extra[src0] < 3 else (pair >> 8) + 67
                    promote(lenpos, n, before + 1)
                else:
                    n = sym - 401
                    v = matchdist[n]
                    putword(v)
                    delta = 1 if v & 255 == 158 else 2
                    promote(matchdist, n, v)
            elif chain > 2:
                digit = br.symbol(self.digit)
                chain += 1
                if chain == 6:
                    chain = 0
                    digit = ranks[4].get(digit)
                else:
                    digit = digit + 2 if digit < 256 else digit - 256
                    if chain == 4:
                        delta = digit + 67
                out.append(digit & 255)
            else:
                imm = 0
                form = 0
                if chain == 2:
                    start = br.p
                    v = br.get(9)
                    if alt:
                        imm = v >> 7 & 3
                        width = 2
                        form = lastform
                    elif v & 256 == 0:
                        imm = v >> 4 & 15
                        width = 5
                        form = 0
                    elif est < 20736:
                        imm = v >> 2 & 63
                        width = 7
                        form = 1
                    elif v & 128:
                        if est < 37120:
                            imm = v >> 1 & 63
                            width = 8
                        else:
                            imm = v & 127
                            width = 9
                        form = 2
                    else:
                        imm = v >> 1 & 63
                        width = 8
                        form = 1
                    br.p = start + width
                    lastform = form
                digit = br.symbol(self.digit)
                if chain == 1:
                    out.append(ranks[0].get(digit) & 255)
                else:
                    if alt:
                        unrank = ranks[5].get(digit)
                        shift, base = (2, 64)
                    elif form == 0:
                        unrank = ranks[1].get(digit)
                        shift, base = (4, 16)
                    elif form == 1:
                        unrank = ranks[2].get(digit)
                        shift, base = (6, 68)
                    elif est < 37120:
                        unrank = ranks[3].get(digit)
                        shift, base = (6, 324)
                    else:
                        unrank = ranks[3].get(digit)
                        shift, base = (7, 162)
                    putword((unrank + base << shift) + imm & 65535)
                chain = 0
            est += delta
        require(length <= len(out) <= length + 4, 'invalid FTCOMP structure')
        return (out, (br.p + 7) // 8)

    def stage2(self, b):
        out = bytearray()
        p = 0

        def append(v):
            out.append(v)
            self.ring[self.hpos & 65535] = v
            self.hpos += 1
            require(len(out) < 131072, 'invalid FTCOMP structure')
        while p < len(b):
            n = u16(b, p)
            p += 2
            require(n >= 1 and p + n <= len(b), ('chunk boundary', p, n, len(b), b[:40].hex()))
            body = b[p + 1:p + n]
            flag = b[p]
            p += n
            if flag == 0:
                for v in body:
                    append(v)
                continue
            s = 0
            while s < len(body):
                v = body[s]
                s += 1
                if v != 158:
                    append(v)
                    continue
                require(s < len(body), 'stage2 marker bounds')
                flag = body[s]
                s += 1
                if flag == 255:
                    append(158)
                    continue
                if flag == 128:
                    require(s < len(body), 'stage2 length bounds')
                    n = body[s] + 67
                    dist = u16(body, s + 1)
                    s += 3
                elif flag & 64 == 0:
                    require(s < len(body), 'stage2 distance bounds')
                    n = flag + 3
                    dist = body[s]
                    s += 1
                else:
                    n = (flag & 63) + 3
                    dist = u16(body, s)
                    s += 2
                for _ in range(n):
                    append(self.ring[self.hpos - 1 - dist & 65535])
        self.streampos += len(out)
        return out

    def rle21(self, b):
        require(b, 'empty RLE block')
        marker = b[0]
        if marker == 255:
            return b[1:]
        count = u16(b, 1)
        tail = len(b) - count & 65535
        require(3 <= tail <= len(b), 'invalid FTCOMP structure')
        q = list(range(256))
        weights = [0] * 256
        for v in b[:tail]:
            weights[v] = weights[v] + 1 & 65535
        ft_sort(q, weights)
        ranks = [0] * 256
        for i, v in enumerate(q):
            ranks[v] = 255 - i
        out = bytearray()
        s = 3
        t = tail
        while s < tail:
            v = b[s]
            s += 1
            if v != marker:
                out.append(v)
                continue
            require(t < len(b), 'RLE rank bounds')
            rank = ranks[b[t]]
            t += 1
            if rank == 255:
                out.append(marker)
            else:
                require(s < tail, 'RLE value bounds')
                out.extend([b[s]] * (rank + 4))
                s += 1
        require(len(out) <= 131072, 'RLE output bounds')
        require(s == tail and t == len(b), ('RLE region consumption', s, tail, t, len(b)))
        return out

    def decode(self, b, expected, archive_footer_count=None):
        require(len(b) >= 8, 'invalid FTCOMP structure')
        p = 4
        out = bytearray()
        while p + 4 <= len(b) and b[p:p + 4] in (b'fT19', b'fT21'):
            require(b[p:p + 4] == b'fT21', 'This implementation is deliberately scoped to fT21')
            start = p
            s1, p = self.stage1(b, p + 4)
            s2 = self.stage2(s1)
            part = self.rle21(s2)
            out += part
            self.logs.append({'offset': start, 'compressed_bytes': p - start, 'stage1_bytes': len(s1), 'stage2_bytes': len(s2), 'output_bytes': len(part)})
            require(len(out) <= expected, 'invalid FTCOMP structure')
        self.trailing_bytes = b[p:].hex()
        require(p == len(b) or (archive_footer_count is not None and len(b) - p == 4 and (u32(b, p) == archive_footer_count)), ('unused bytes', p, len(b), b[p:p + 16].hex()))
        require(len(out) == expected, ('output length', len(out), expected))
        return bytes(out)

ARCHIVE_SIZE = 1219357
ARCHIVE_SHA256 = '57268c1137ce589c96957052972dbd58574c17a027ea66f1a12c6fd460a578e3'
EXPECTED = [('prckt24.FNT', 345600, '1cf871b9a37966d779402cb30be9150611ddcf8a7b6598a8e8512ff985eb3fca'), ('prcfs24.FNT', 340992, '789fe69db7497e570a9e7a63434a3a20a4f75ed7e67fe23d72916a49608a0771'), ('prcht24.FNT', 331776, '6b8a3d637a5a92d84259bdd5265c2021f98c43e51e4154a1907151d54b1eb949'), ('prcst24.FNT', 319488, '74196fcf324982c6779507b6ce4bfb625b360d49523d7c2c6e19198c3e0f3d35'), ('prczn24.IBM', 5601, 'ebbc9cd7404469ccf505f94ded9c898516225f138633b0b9f897b0c90a327921')]



DISK_SIZE = 1884160
DISK_SHA256 = 'eb523b67eb860c39538ec9645b1670d56a5ff339105e97c7ad31a521156b2a2a'


def read_fat12_font1(data):
    """Read only the root FONT1 entry using the first FAT; never write a file.

    Kept separate from the whole-disk allowlist for source-free synthetic tests.
    The public disk entry point is font1_from_disk(), which checks the allowlist.
    The known XDF image has differing FAT regions, so do not merge FAT copies.
    """
    require(len(data) >= 512 and data[510:512] == b'\x55\xaa', 'FAT12 boot sector bounds/signature')
    bps, spc, reserved, nfats, nroot, total16, media, spf = struct.unpack_from('<HBHBHHBH', data, 11)
    total = total16 or u32(data, 32)
    require(bps in (512, 1024, 2048, 4096), 'unsupported sector size')
    require(spc in (1, 2, 4, 8, 16, 32, 64, 128), 'invalid cluster size')
    require(reserved >= 1 and 1 <= nfats <= 2 and 1 <= nroot <= 4096 and spf >= 1,
            'invalid FAT12 geometry')
    require(total * bps == len(data), 'disk size disagrees with BPB')
    root_sector = reserved + nfats * spf
    data_sector = root_sector + (nroot * 32 + bps - 1) // bps
    require(data_sector < total, 'FAT12 metadata outside image')
    cluster_count = (total - data_sector) // spc
    require(1 <= cluster_count < 4085, 'not a FAT12 cluster count')
    fat = data[reserved*bps:(reserved+spf)*bps]
    require((cluster_count+1)*3//2 + 2 <= len(fat), 'FAT12 table too short')
    root = root_sector * bps
    entries = []
    for off in range(root, root+nroot*32, 32):
        entry = data[off:off+32]
        require(len(entry) == 32, 'root entry bounds')
        if entry[0] == 0:
            break
        if entry[0] == 0xe5 or entry[11] & 0x18:
            continue
        if entry[:11] == b'FONT1      ':
            entries.append(entry)
    require(len(entries) == 1, 'expected exactly one root FONT1 file')
    entry = entries[0]
    size = u32(entry, 28)
    cluster = u16(entry, 26)
    require(0 < size <= len(data), 'FONT1 file size bounds')
    cluster_bytes = spc*bps
    expected_clusters = (size+cluster_bytes-1)//cluster_bytes
    require(expected_clusters <= cluster_count, 'FONT1 exceeds data area')
    out = bytearray()
    visited = set()
    for _ in range(expected_clusters):
        require(2 <= cluster <= cluster_count+1 and cluster < 0xff0,
                'invalid, reserved, or out-of-image FAT12 cluster')
        require(cluster not in visited, 'FAT12 chain loop')
        visited.add(cluster)
        start = data_sector*bps + (cluster-2)*cluster_bytes
        require(start+cluster_bytes <= len(data), 'cluster data bounds')
        out.extend(data[start:start+cluster_bytes])
        pair = u16(fat, cluster*3//2)
        cluster = (pair >> 4) & 0xfff if cluster & 1 else pair & 0xfff
    require(0xff8 <= cluster <= 0xfff, 'FAT12 chain length or end marker mismatch')
    return bytes(out[:size])


def font1_from_disk(data):
    """Validate the known disk, then recover and validate its FONT1 in memory."""
    require(len(data) == DISK_SIZE, 'unsupported disk size')
    require(hashlib.sha256(data).hexdigest() == DISK_SHA256, 'unsupported disk SHA-256')
    archive = read_fat12_font1(data)
    require(len(archive) == ARCHIVE_SIZE and hashlib.sha256(archive).hexdigest() == ARCHIVE_SHA256,
            'disk FONT1 size or SHA-256 mismatch')
    return archive


def parse_archive(data):
    """Validate the exact supported archive and decode every member in memory."""
    require(len(data) == ARCHIVE_SIZE, 'unsupported archive size')
    require(hashlib.sha256(data).hexdigest() == ARCHIVE_SHA256,
            'unsupported archive SHA-256; only the documented FONT1 is accepted')
    pos = 0
    outputs = []
    for index, (expected_name, expected_size, expected_hash) in enumerate(EXPECTED):
        require(pos + 41 <= len(data), 'truncated member header')
        require(data[pos:pos+4] == bytes.fromhex('a596fdff'), 'bad PACK2 signature')
        require(data[pos+24:pos+31] == b'FTCOMP\0', 'unsupported codec')
        ea, size, nextpos = (u32(data, pos+offset) for offset in (12, 16, 20))
        n = u16(data, pos+39)
        require(ea == 0 and size == expected_size, 'unexpected member metadata')
        require(1 <= n <= 512 and pos+41+n <= len(data), 'member name bounds')
        # Compare raw bytes, rather than normalizing unsafe path characters.
        require(data[pos+41:pos+41+n] == b'\\' + expected_name.encode('ascii') + b'\0',
                'unexpected member name or order')
        final = index == len(EXPECTED)-1
        require((nextpos == 0) == final, 'unexpected archive member count')
        start, end = pos+41+n, nextpos or len(data)
        require(start < end <= len(data), 'member payload bounds')
        decoder = Decoder()
        output = decoder.decode(data[start:end], expected_size,
                                archive_footer_count=len(EXPECTED) if final else None)
        require(hashlib.sha256(output).hexdigest() == expected_hash,
                'recovered member hash mismatch: ' + expected_name)
        outputs.append((expected_name, output))
        pos = end
    require(pos == len(data), 'unused archive bytes')
    return outputs


def output_components(output):
    """Require a lexical path under cwd/local-research, never following links."""
    import os
    path = Path(output)
    require('..' not in path.parts, 'output may not contain parent traversal')
    if path.is_absolute():
        try:
            path = path.relative_to(Path.cwd())
        except ValueError:
            raise ValueError('output must be under cwd/local-research') from None
    parts = path.parts
    require(len(parts) >= 2 and parts[0] == 'local-research',
            'output must be a new directory under cwd/local-research')
    require(all(part not in ('', '.', '..') for part in parts), 'invalid output path')
    require(hasattr(os, 'O_NOFOLLOW') and os.open in os.supports_dir_fd,
            'this safe writer requires POSIX dir_fd and O_NOFOLLOW support')
    return parts


def write_outputs(output, outputs):
    """Create a new destination, with dir-fd-relative no-follow/exclusive writes.

    Ancestors beyond local-research must already exist. No existing destination
    is reused, even if empty. Descriptor-relative operations prevent symlink
    swaps from redirecting file writes. Parsing must finish before calling this.
    """
    import os
    parts = output_components(output)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open('.', flags)
    dest = None
    created = False
    written = []
    try:
        for index, part in enumerate(parts[:-1]):
            if index == 0:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=parent)
                except FileExistsError:
                    pass
            child = os.open(part, flags, dir_fd=parent)
            os.close(parent)
            parent = child
        os.mkdir(parts[-1], mode=0o700, dir_fd=parent)
        created = True
        dest = os.open(parts[-1], flags, dir_fd=parent)
        for name, content in outputs:
            require(name in {entry[0] for entry in EXPECTED}, 'unexpected output name')
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=dest)
            written.append(name)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
    except Exception:
        if dest is not None:
            for name in written:
                os.unlink(name, dir_fd=dest)
        if created:
            os.rmdir(parts[-1], dir_fd=parent)
        raise
    finally:
        if dest is not None:
            os.close(dest)
        os.close(parent)


def extract(archive, output, *, disk=False):
    """Read a bounded user-supplied input, validate everything, then write."""
    import os
    import stat
    output_components(output)
    fd = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode), 'archive must be a regular, non-symlink file')
        expected_size = DISK_SIZE if disk else ARCHIVE_SIZE
        require(info.st_size == expected_size, 'unsupported input size')
        data = stream.read(expected_size + 1)
    if disk:
        data = font1_from_disk(data)
    outputs = parse_archive(data)
    write_outputs(output, outputs)
    return [{'name': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
            for name, content in outputs]


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=(
        'Offline, allowlisted FTCOMP/PACK2 unpacker for a user-supplied IBM PC DOS '
        'FONT1 archive. No fonts or archive are bundled, downloaded, or executed. '
        'Use only source data you are entitled to process. Requires POSIX.'))
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--archive', type=Path, help='local user-supplied FONT1')
    inputs.add_argument('--disk', type=Path, help='local user-supplied known Disk03.xdf (static FAT12 read)')
    parser.add_argument('--output', required=True, type=Path,
                        help='new directory under cwd/local-research (no symlinks or overwrite)')
    args = parser.parse_args(argv)
    try:
        result = extract(args.disk or args.archive, args.output, disk=args.disk is not None)
    except (ValueError, OSError, IndexError, zlib.error, struct.error) as exc:
        parser.exit(2, 'error: ' + str(exc) + '\n')
    print(json.dumps({'archive_sha256': ARCHIVE_SHA256, 'entries': result}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
