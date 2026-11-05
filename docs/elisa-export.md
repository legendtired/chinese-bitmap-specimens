# ELISA 恵梨沙：原 BDF 与 Unicode 重编码

本方法对应目录 `elisa_8_native`。原输入已经是 **JIS X 0208 编码的 BDF**，不必重新猜测或解析原始 FNT。脚本只把字符编码改为 Unicode，逐字保留原位图、字宽、bearing 和版权字段。

## 获取完整原包

从 [MINIX distfiles 归档索引](https://www.minix3.org/distfiles-backup/) 查找 `elisau10.tgz`，或从 [FreeBSD font-elisa10 项目记录](https://github.com/freebsd/freebsd-ports/tree/main/japanese/font-elisa10) 查阅来源。取得包后保留整个原包和其中的说明，不要只转发字体文件。

[原 Vector 来源介绍](https://www.vector.co.jp/soft/data/writing/se013782.html) 仍保留作为出处。本轮 Vector 下载页返回403，未重试或绕过；MINIX 是独立发布的历史归档，其包哈希与 FreeBSD 记录一致，包内 BDF 哈希又与本目录既有证据一致。镜像存在本身不扩大原许可。

此处的 `elisau10` 是 **10×8 字框、8×8 字面**。它与另一个 `elisat10`（8×8 字框）不是相同的排版版本，不能仅凭 “ELISA 8” 或包名中的数字替换输入。

本次在 2026-11-05 实际取得并核验：

- `elisau10.tgz`：125292 字节，SHA256 `bb62d48db7a26339313947b623376bb18d92196424ee1545ef54ed8b0200dfba`。与 [FreeBSD 的 distinfo](https://github.com/freebsd/freebsd-ports/blob/main/japanese/font-elisa10/distinfo) 一致。
- 包内 `elisau10.bdf`：852905 字节，SHA256 `5f1c61f4d2962d3bfc4128708eb48b3885e26eb797ebe986027eb8ddab39d524`。与本项目目录原有的 source_sha256 完全一致。
- 原包还包含 `elisa100.doc`、`elisau10.doc`、`hosoku.txt`、`fonts.alias` 和 `clR5x8-s5x8.diff`。日文说明采用 Shift-JIS，可用支持此编码的文本编辑器阅读。

如果软件支持 JIS X 0208 BDF，原来的 `elisau10.bdf` 本身就可作为字体输入。下面的步骤用于需要 Unicode 码位的软件。BDF 并不等于可直接安装到任意系统的 TTF/OTF，目标软件需支持位图 BDF。

## 导出 Unicode BDF

需要 Python 3.9+，转换本身只用标准库。把完整原包放到 `local-research/elisa/elisau10.tgz`，在仓库根目录运行：

```sh
mkdir -p local-research/elisa
python3 scripts/elisa_to_bdf.py \
  --source local-research/elisa/elisau10.tgz \
  --output local-research/elisa/elisa-unicode.bdf
```

也可以把 `--source` 指向从完整原包中解出的、哈希相同的 `elisau10.bdf`。脚本直接读取原包中的 BDF，不向文件系统解压归档路径。

输出为 BDF 和相邻的 `.bdf.json` 校验报告。原包或 BDF 哈希不符就停止，已有输出或报告也不会被覆盖。它不接受 `elisa100.lzh`、`ELISA100.FNT`、`elisat10.bdf`，也不提供忽略校验的开关。

## 字框、编码与覆盖

- 全部 **6877 个字形**严格通过 Python `iso2022_jp` 将 JIS X 0208 映射到 Unicode，逐字检查往返映射和重复码位。不是 CP932 或 JIS X 0213，不做简繁替换。
- 保留 `BBX 10 8 0 -2`、`DWIDTH 10 0`、`FONT_ASCENT 6`、`FONT_DESCENT 2`。基线按原 BDF：字框覆盖 y=-2 至 5，基线上方6像素、下方2像素，不把字形向上或向下挪动。
- 原 8×8 字形右侧补两列空白；不裁边距、不缩放、不补字。每行 BDF 用两个字节存10位像素，剩余位仍为零。
- 原文件的 `SIZE`、`PIXEL_SIZE` 和 XLFD 中的尺寸为10，脚本原样保留。这不表示字形高10像素，实际高度由8像素的 BBX 决定。
- 目录繁体样句和全角英数行完整；整个200×20固定样图的RGBA像素逐一重建后差异为0。
- 没有 U+0020–U+007E 的普通 ASCII 字形。全角英数不是普通半角 ASCII；仅 U+3000 为全空白字形。
- 简体样句缺“视”“蓝”；JIS 末尾的“凜”“熙”也不在本版。6877 字不等于完整现代日文字库，更不等于完整中文字库。

脚本仅改 `ENCODING`、字符名、字符集声明、默认字符与一条转换说明。原位图和全部字形度量不变。报告列出输入／输出哈希、字数、字框、基线、样句缺字和许可提示。

## 验证

不附带字体的基础测试：

```sh
python3 tests/elisa-export.test.py
```

基础运行通过18项测试，8项真实输入测试会明确跳过。实际源文件与目录像素验证另需 Pillow：

```sh
ELISA_SOURCE=local-research/elisa/elisau10.tgz \
ELISA_CATALOG_ROOT=. \
python3 tests/elisa-export.test.py
```

本次26项全部通过，包含6877字的源／输出位图与bearing对照、全部映射的独立 EUC-JP 复核、既有样图完整像素对照、哈希拒绝、输出防覆盖和失败回滚。没有把原字模嵌入脚本或测试。

## 许可与边界

原包说明将使用限定为个人用途，禁止营利使用；个人范围内允许改动。个人再分发须保持原归档组成，不能单独分发字体或修改后的字体；转载等其他情形另有联系权利人的要求。具体以 `elisa100.doc` 和 `elisau10.doc` 为准。

因此本项目只提供处理脚本和方法，**不分发原包、完整BDF、重编码结果或字库子集**。Unicode 重编码没有改变版权，也不授予商业使用、嵌入应用或公开发布的许可。保留完整原包，输出仅按原许可在本地使用。
