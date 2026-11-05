# FTCOMP companion provenance

`../../ibm_ftcomp_unpack.py` is an offline Python reimplementation of the
fT21/PACK2 decoding path, informed by Deark. Dimitriy Ryazantcev reverse-engineered
the decompression algorithm and wrote the original Deark decoder; Jason Summers
maintains Deark and adapted the implementation. The original MIT-style license
is preserved verbatim in `COPYING`. `ftcompdata.h` is the unmodified Deark
bootstrap weight/preset table, loaded as numeric data, never compiled or executed.

Source files inspected on 2026-11-05 (these links are source-code pages, not
archive, font, or executable downloads):

- [FTCOMP algorithm](https://github.com/jsummers/deark/blob/master/src/fmtutil-ftcomp.c)
  SHA-256 `8a83af1cec4d96948d3c58f444f1e483a9ec525df5df983e62abdc6fa6e1b544`
- [PACK2 container](https://github.com/jsummers/deark/blob/master/modules/os2pack.c)
  SHA-256 `93ef900d01bd23a204fecbf513bd21caa172a3f5abdba90f5af2206db85a97a5`
- [Bootstrap tables](https://github.com/jsummers/deark/blob/master/foreign/ftcompdata.h)
  SHA-256 `b71c7e60880e793f3cf1435df1eba07ebbd19975794a11df3e99a592df3cddf7`
- [Deark license](https://github.com/jsummers/deark/blob/master/COPYING)
  SHA-256 `770a005b55f848b3985030ba01bb3f5db5718955ecdef3ec41d0ca00b97e24c6`

The links track upstream master; hashes identify the exact inspected copies.
The script verifies the bundled table hash before decoding.

## Scope and local use

No IBM source archive, font, font derivative, disk image, or original executable
is included here. Deark's license does not grant rights to IBM font data. Supply
only an archive you are entitled to process. This is deliberately not a general
purpose FTCOMP tool: only the previously studied FONT1 of 1,219,357 bytes and
SHA-256 `57268c1137ce589c96957052972dbd58574c17a027ea66f1a12c6fd460a578e3`
is accepted as a direct archive. Alternatively, `--disk` accepts only the studied
1,884,160-byte `Disk03.xdf`, SHA-256
`eb523b67eb860c39538ec9645b1670d56a5ff339105e97c7ad31a521156b2a2a`.
It runs no original program and makes no network requests.

From the repository root, run:

```
python3 scripts/ibm_ftcomp_unpack.py --archive /path/to/your/FONT1 --output local-research/fonts24
```

Or use your existing archiver to extract `Disk03.xdf` locally from your own
installation media archive, then run:

```
python3 scripts/ibm_ftcomp_unpack.py --disk /path/to/your/Disk03.xdf --output local-research/fonts24
```

`--archive` and `--disk` are mutually exclusive. The disk route verifies the
whole-image hash before parsing its FAT12 root directory and follows only the
`FONT1` cluster chain. It verifies that recovered archive against the same
FONT1 allowlist before decoding. The known image's FAT regions differ; the
reader deliberately uses the first FAT, matching the verified recovery. Boot
code and original extraction programs are never executed. All intermediate
data remains in memory; no raw archive or temporary fonts are written outside
the requested output directory. This script does not unpack 7z containers.

Requires Python 3.9+ on POSIX with `O_NOFOLLOW` and descriptor-relative operations.
The destination must not already exist and must be under the current working
directory's `local-research`. That root is created if needed; any deeper parent
directories must already exist. Symlink ancestors below the working directory,
symlink input files, parent traversal, and overwrites are rejected. The entire
archive is decoded and all five member lengths and hashes are checked in memory
before creating output files. The command prints a JSON result to stdout.

The recovered files are `prckt24.FNT`, `prcfs24.FNT`, `prcht24.FNT`, `prcst24.FNT`,
and `prczn24.IBM`. The last is a 5,601-byte auxiliary file, not a fifth full font.
The separate font exporter accepts only `prckt24.FNT`, `prcht24.FNT`, and
`prcfs24.FNT`; `prcst24.FNT` is deliberately excluded as a duplicate. Recovered
hashes establish reproducibility against research artifacts, not independent
authentication of pre-archive originals; no verified stored FTCOMP checksum was
identified in this recovery.

Source-free tests:

```
python3 tests/ibm-ftcomp-unpack.test.py
```

Optional local five-member extraction verification (uses a temporary directory
and removes outputs afterward):

```
IBM_FTCOMP_ARCHIVE=/path/to/your/FONT1 python3 tests/ibm-ftcomp-unpack.test.py
```

Optional disk-to-five-member verification:

```
IBM_FTCOMP_DISK=/path/to/your/Disk03.xdf python3 tests/ibm-ftcomp-unpack.test.py
```

Source-free tests additionally exercise synthetic FAT12 traversal, malformed
geometry, invalid clusters, loops, truncated/overlong chains, duplicate/missing
FONT1 entries, disk allowlist rejection, and mutually exclusive CLI inputs.
