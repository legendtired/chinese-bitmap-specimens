# IBM PC DOS：原生 24×24 简体字库本地导出

本工具从使用者自备、已核验的 IBM PC DOS 中文字库中导出三套原生 **24×24** 点阵：楷体 `prckt24`、黑体 `prcht24`、仿宋体 `prcfs24`。不缩放、不裁切、不描边、不移位、不借用其他字体补字。公开工具仅含脚本、说明和不含源字模的测试，**不分发安装盘、FONT1、IBM FNT 或完整 BDF**。

每套均有 **7,444 个标准 GB2312 Unicode 映射，其中包含全部 6,763 个汉字**。U+3000 全角空格没有原始记录，导出不合成它。另有尚未确认 Unicode 的 IBM 记录，全部保留为 `ENCODING -1`，不计作已知字符覆盖。

## 来源、年代与权利

浏览来源：[WinWorld PC DOS 2000 产品页](https://winworldpc.com/product/pc-dos/2000)。核验对象是其中的简体中文 3.5 英寸 XDF 发行包，盘内第一张盘的 README 说明 PC DOS 2000 是 PC DOS 7 的升级版，并保留 IBM 1981、1998 年版权声明。

三套 FNT 文件头均为 `System DBCS 24`，内部中文名称分别是“楷体”“黑体”“仿宋体”。内部日期均为 **01/24/92**。这是字库头里的日期字段，不等于本发行包发行日期，也不足以证明字形最初设计或首次公开日期。发行归属已核实，但尚未确认原始字形设计者。

没有找到并核实 IBM 字库的开放再分发许可。归档站允许浏览或获取，不代表获得字体再分发权；格式转换同样不会改变原权利。请只处理自己有权使用的源文件，完整恢复结果留在本地。工具参考代码的 MIT 许可不覆盖 IBM 字库。

## 已核验的输入

主导出器只接受下列三个文件的确切字节内容。文件可以更名，但大小与 SHA-256 必须一致；其他版本或改动后的文件一律拒绝。

| 文件 | 大小（字节） | 原始记录 | 标准映射 | 汉字 | 未映射 IBM 记录 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `prckt24.FNT` 楷体 | 345600 | 7503 | 7444 | 6763 | 59 |
| `prcht24.FNT` 黑体 | 331776 | 7503 | 7444 | 6763 | 59 |
| `prcfs24.FNT` 仿宋体 | 340992 | 7472 | 7444 | 6763 | 28 |

SHA-256：

- `prckt24.FNT`：`1cf871b9a37966d779402cb30be9150611ddcf8a7b6598a8e8512ff985eb3fca`
- `prcht24.FNT`：`6b8a3d637a5a92d84259bdd5265c2021f98c43e51e4154a1907151d54b1eb949`
- `prcfs24.FNT`：`789fe69db7497e570a9e7a63434a3a20a4f75ed7e67fe23d72916a49608a0771`

这些摘要标识本次严格恢复、重复验证的输入，不能说成“与当年未压缩原件的独立官方校验和一致”。目前未确认可用于此目的的归档内置文件校验和。

## 从自备原盘恢复 FNT

需要 Python 3.9+ 与 POSIX 环境（Linux、macOS 或 WSL），用于安全的目录相对写入。全程离线，只使用 Python 标准库，不需要 Pillow，不运行 `UNPACK2.EXE`、`FONT.EXE`、`XDFCOPY.EXE` 或安装盘中的其他程序。

1. 使用自己已有的归档软件打开自备简体中文发行包，取出 `Disk03.xdf`。不启动镜像里的程序。已核验的外层 7z 为 13,157,298 字节，SHA-256 为 `26f42bdef79f795d8d42ec6fbcd87b5214cf370540eb454c545d878a2779fc71`；工具本身不下载也不解 7z。
2. 第三张盘是 1,884,160 字节的逻辑扇区镜像，SHA-256 为 `eb523b67eb860c39538ec9645b1670d56a5ff339105e97c7ad31a521156b2a2a`。`FONT1` 位于其 FAT12 根目录。
3. 从仓库根目录执行，输出目录必须尚不存在：

```sh
python3 scripts/ibm_ftcomp_unpack.py \
  --disk /path/to/your/Disk03.xdf \
  --output local-research/ibm-fonts24
```

配套工具先核验整张盘的大小和 SHA-256，再静态读取 FAT12 中的 `FONT1`，核验 FONT1，最后解开 FTCOMP/PACK2 的 fT21 数据。不挂载、不启动原盘，也不改动输入。

如果已有从该盘提取的 `FONT1`，可直接使用：

```sh
python3 scripts/ibm_ftcomp_unpack.py \
  --archive /path/to/your/FONT1 \
  --output local-research/ibm-fonts24
```

此 FONT1 大小为 1,219,357 字节，SHA-256 为 `57268c1137ce589c96957052972dbd58574c17a027ea66f1a12c6fd460a578e3`。两种入口互斥，只支持上述确切版本。它不是通用 XDF、FAT 或 FTCOMP 解包器。

解包器在内存中完成五个成员的长度和摘要核验后才写文件：三套目标 FNT、`prcst24.FNT` 宋体，以及 5,601 字节的辅助文件 `prczn24.IBM`。宋体因重复排除，不被主 BDF 导出器接受；辅助文件不是第五套完整汉字字体。

FTCOMP 解码路径参考 Deark 的公开源代码，算法贡献者为 Dimitriy Ryazantcev、Jason Summers。仓库保留了静态 bootstrap 表和原 MIT-style `COPYING`，详见 [参考代码与表的来源说明](../scripts/vendor/ftcomp/README.md)。没有附带或运行下载的可执行程序。

## 导出三套 BDF

从仓库根目录分别运行：

```sh
python3 scripts/ibm_pcdos_to_bdf.py \
  --font local-research/ibm-fonts24/prckt24.FNT \
  --output local-research/ibm-kai-24.bdf

python3 scripts/ibm_pcdos_to_bdf.py \
  --font local-research/ibm-fonts24/prcht24.FNT \
  --output local-research/ibm-hei-24.bdf

python3 scripts/ibm_pcdos_to_bdf.py \
  --font local-research/ibm-fonts24/prcfs24.FNT \
  --output local-research/ibm-fangsong-24.bdf
```

每次输出一个 BDF，并在终端显示记录数、映射数和 BDF 摘要。输出只能放在**当前工作目录的 `local-research/` 内**，须为新的 `.bdf` 文件。所有输入、结构、映射和逐字点阵摘要检查完成后才创建输出。输入只读，已有文件永不覆盖，不能覆盖输入。输入路径和输出路径各级均拒绝符号链接；输出写入还采用目录描述符、禁止跟随链接和排他创建，防止链接替换把写入导向别处。

不提供 `--force`、跳过摘要、忽略损坏、改变字号或推测扩展编码的选项。重跑请选新的输出文件。`local-research/` 应保持在版本控制和发布包之外；不要将其恢复文件批量添加到公开仓库。

## 字体结构与映射

- 文件以 512 字节扇区组织。头部存有 CP1381、24×24、每字 72 字节、压缩方式等字段。
- `0xC0–0x1C7` 是 nibble 前缀解码表；`0x200–0x9FF` 是 256 个预测上下文，每个上下文为 0–15 的完整排列。
- `0xA00` 起是扇区目录，本批数据从 `0x1A00` 开始。每条记录为 16 位 IBM ID、8 位压缩长度、payload，不跨扇区。每个数据扇区必须被目录恰好引用一次，引用匹配其首条记录；根目录与叶页首项一致。
- 每字恰好解出 144 个残差 nibble，再用前两行同列的 nibble 预测还原 72 字节。保持逐行存储、每行 3 字节、最高位在左。压缩尾部仅允许不足 8 位的填充，不补零凑字形。
- GB2312 双字节 `(high, low)` 对应内部 ID：`256 + (high - 0x8C) × 94 + low - 0xA1`。只对 Python 严格 GB2312 解码定义的码位建立映射，并核验整张映射摘要；**不把所有 CP1381 私有码位当作 GB2312**。
- 无法确证映射的原始记录使用 `STARTCHAR IBMxxxx`、`ENCODING -1`，点阵完整保留。它们是保留记录，不是已经确认可输入的 Unicode 字符。部分字体软件会忽略未编码记录，需按 BDF 原文检查其存在。

所有 6,763 个汉字均有非空字形。覆盖是简体 GB2312，不能表述成完整繁体字库或简繁双全集。工具不做简繁转换，也不输出另一个半宽 ASCII 字库。

## 原生字框与 BDF 度量

- `SIZE 24 72 72`，XLFD 为 14 字段，原生 24 像素 strike、72×72 dpi。
- `FONTBOUNDINGBOX 24 24 0 0`、`BBX 24 24 0 0`、`DWIDTH 24 0`、`SWIDTH 1000 0`。
- `FONT_ASCENT 24`、`FONT_DESCENT 0`；每条记录包含 24 行 BITMAP，每行 6 个十六进制字符。

**24/0 基线及零偏移是保留完整字框的合成导出约定，不是恢复出的历史排版度量。** 不因此移动像素、裁边或重采样，不声称复现原机文字基线。FreeType 核验使用真正的 24 ppem bitmap strike。

网站固定样句“视野无限广，窗外有蓝天。”是 10 个汉字与 2 个中文标点，全部来自同一套原始 24×24 字模，样图为 288×24；没有拼接半宽 ASCII 行或其他字库。

## 去重与收录边界

三套候选与已比较的 HZK、DEC 等本地参考均有大量真实像素差别，允许平移后也不是全库重复。这只能说明不是所比较点阵库的完全重复，不能证明独立设计或独立著作权来源。

同一归档内的 `prcst24.FNT` 宋体，其全部 6,763 个 GB2312 汉字与已核验四通 GB5007C-24 ROM 完全相同，因此不另作为新字体导出。16 点宋体与既有 Beijing16、DEC 宋体高度接近，也不纳入本工具。`PRCHN24` 等半宽资料不混入这三套全宽结果。

## 不含源字库的回归测试

```sh
python3 tests/ibm-pcdos-export.test.py
python3 -O tests/ibm-pcdos-export.test.py
python3 tests/ibm-ftcomp-unpack.test.py
```

测试自行构造前缀表、预测表和点阵，不依赖 IBM FNT、不联网。覆盖压缩边界、两行预测、扇区目录、重复 ID、标准映射、全角空格不补造、未编码记录保留、原像素回读、BDF 度量、摘要白名单、只读输入、路径穿越、符号链接、拒绝覆盖及命令行拒绝绕过选项。检查不依赖可被 `python -O` 关闭的 `assert`。

有系统 FreeType 时，测试另核验合成字模的 24 ppem strike、24 像素 advance、字框与每个原生像素；没有 FreeType 时明确跳过该项，主导出器仍只需 Python 标准库。

三套真实源文件已在私有本地核验：全部原始记录与既有独立验证 BDF 逐字一致，全部 22,332 个已映射字形（三套各 7,444）通过 FreeType 24 ppem 的度量及像素回读。146 条未映射记录也逐条保留、按 BDF 原文与源矩阵比较一致。这些验证结果不代表取得完整字体的公开再分发许可。

## 原配半角英数

[PRCHN24 提取与可选合并](ibm-prchn24.md)：同发行盘公共 12×24 半角，95 个可打印 ASCII；三套汉字共用，不是各自专属西文字重。固定样图增加独立西文行，保留原生字宽。
