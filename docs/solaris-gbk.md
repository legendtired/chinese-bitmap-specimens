# Solaris 中易宋体：12／14／16／20／24点

这五套来自 Solaris 7 SPARC 11/99 简体中文版原盘的 `SUNWgxfnt` 包，是原生黑白 PCF 点阵，不是从轮廓字体重新栅格化。目录按汉字实际 bitmap 字框标为12／14／16／20／24点。

## 来源与日期

从[原盘资料页](https://archive.org/details/solaris-7-1199-sparc-cs)查找 `Solaris 7 1199 SPARC Software CS.iso`。资料页可读不表示字体具有开放许可；请在有权使用的情况下取得原盘或已有副本。本站不提供镜像、PCF、BDF或完整字模。

- PCF版权属性：`Copyright (c) 1997 Beijing Zhong Yi Electronics Co.`。
- 包内文件日期：1998-07-23。
- 原盘版本：Solaris 7 SPARC 11/99，即1999-11载体。

1997是版权年，1998是这份文件的日期，1999是原盘版本，均不能单独证明首次设计或发行年份。未确认完整字体的开放再分发授权；转换不改变原权利限制。

## 静态提取

无需安装或启动 Solaris，也不要运行原盘程序。

1. 用本地归档工具打开自己取得的 ISO。
2. 定位 `Solaris_7/Product/SUNWgxfnt/archive/none`。这个无后缀文件实际为 ZIP 归档；复制到本地研究目录后，用支持 ZIP 的工具只读打开。
3. 提取 `openwin/lib/locale/zh.GBK/X11/fonts/75dpi/` 下的 `gbksong12.pcf.Z`、`gbksong14.pcf.Z`、`gbksong16.pcf.Z`、`gbksong20.pcf.Z`、`gbksong24.pcf.Z`。
4. `.Z` 是 Unix compress 格式。使用操作系统已有的 `uncompress` 解压到**新文件**，不要只改后缀。本站转换器只接受解压后的PCF，不运行外部程序，也不负责下载或解包原盘。

以下命令在仓库根目录执行。输入、输出目录应为自己控制的普通目录，不使用符号链接。`set -C` 防止 shell 覆盖已有输出：

```sh
mkdir -p local-research/solaris-source
# 将合法取得并提取的 .pcf.Z 放入该目录后：
(set -C; uncompress -c local-research/solaris-source/gbksong12.pcf.Z > local-research/solaris-source/gbksong12.pcf)
```

若系统没有 `uncompress`，先通过系统的可信软件仓库准备解压工具。不要执行原盘内程序来提取字体。其余四个文件同法处理；输出存在时换一个新文件名，不覆盖旧文件。

## 指定版本校验

[纯标准库转换器](../scripts/solaris_gbk_to_bdf.py)只接受下列解压后PCF，文件名本身不作为身份依据。实际SHA-256、字节数、字框、字数和映射必须同时符合。其他版本会拒绝，不提供跳过校验的开关。

| 原文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| gbksong12.pcf | 1696464 | `3c092318acb711fed39f11ad00c356e13a454ef0abf213916a74bc74299f7db6` |
| gbksong14.pcf | 1872304 | `975ac1cf10c384db0902283468f3d373761ac46d9e5992e20fe2a8e7aa7db309` |
| gbksong16.pcf | 2048144 | `07de4bec37ba0d0354f06ca1c101c46518e4eabd18fff6a8e9953bf676f57c65` |
| gbksong20.pcf | 2399824 | `63d229d64536be3a8548dd1605879ffeb6911cae09d3dc0814d4c0142006eb8a` |
| gbksong24.pcf | 2751504 | `171d73f44ef1d23d0e5d0e29b3b70057bef6e3574af6dce9ccd67c2879c9528e` |

## 本地导出

需要 Python 3.9+，以及支持 `O_NOFOLLOW` 和目录相对文件操作的 POSIX 系统，例如 Linux。脚本在不具备安全文件接口的平台会停止。输入必须是普通文件，所有路径组件不得为符号链接；输出必须位于当前目录下的 `local-research/`，必须是尚不存在的 `.bdf` 文件。脚本拒绝目录穿越、非普通输入、符号链接和覆盖，不能指定公开网站目录为输出。若写入中途失败，新文件可能不完整，应人工检查并改用新输出名；脚本不会自动删除路径，避免并发情况下误删替换文件。

默认导出严格GBK映射可确认的Unicode子集：

```sh
python3 scripts/solaris_gbk_to_bdf.py \
  --font local-research/solaris-source/gbksong12.pcf \
  --output local-research/solaris-export/song12-unicode.bdf
```

需要保留全部原码字形时，另导出原编码版：

```sh
python3 scripts/solaris_gbk_to_bdf.py \
  --font local-research/solaris-source/gbksong12.pcf \
  --encoding native-gbk \
  --output local-research/solaris-export/song12-native-gbk.bdf
```

其余字号更换输入和新输出文件名。标准输出是校验报告，含源文件SHA、BDF SHA、字符数、全局指标和95个未确认映射的原码。BDF是点阵交换格式，不是所有系统都能直接安装的TTF；原编码版不能当作Unicode字体输入文字。

## 字符、尺寸与保留范围

每套原PCF包含21980个有编码字形。严格GBK映射得到21885个Unicode字符，含20902个基本汉字，兼有简体与繁体；另95个历史扩展原码没有在本轮证据中确认Unicode对应。

- Unicode版输出21885字，明确排除95个未确认码，不用现代GB18030、猜测的PUA或码值本身冒充Unicode。
- 原码版保留全部21980字，95个未确认码仍以原GBK数值保存。它们并未丢失，但不能宣称已完成Unicode映射。
- 原ASCII只有U+0021–U+007E共94字。**原PCF没有U+0020半角空格**，有U+3000全角空格。两个BDF均不补造U+0020，也不使用其他字体补字。
- 固定样文中的空格仅作字号一半的排版留白，不是字体字形；字符数据仍报告缺省空格。
- 保留每字原像素、字框、bearing、`DWIDTH`和`SWIDTH`。源`SWIDTH`即使ASCII也为1000；ASCII实际`DWIDTH`是字号的一半，不擅自修正历史记录。

| 汉字bitmap字框／advance | 原PIXEL_SIZE | FONT_ASCENT | FONT_DESCENT | 全局行高 | 汉字BBX y偏移 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 12×12／12 | 14 | 12 | 2 | 14 | -1 |
| 14×14／14 | 16 | 13 | 3 | 16 | -2 |
| 16×16／16 | 18 | 15 | 3 | 18 | -2 |
| 20×20／20 | 22 | 19 | 3 | 22 | -2 |
| 24×24／24 | 26 | 22 | 4 | 26 | -3 |

每字墨迹大小不同，表中是实际保存的bitmap字框。BDF的全局上升／下降来自原PCF加速器表，不能用逐字外框并集替代；`FONTBOUNDINGBOX`保留逐字外框并集。固定样文为了比较字形，使用紧凑字框排版，不冒充原系统默认行距。

## 核验与比较边界

- 两条独立PCF读取路径核对了字节序、位序、scan-unit及全部原码像素；严格GBK映射另与系统编码转换核对。
- 系统FreeType逐字读取原PCF、Unicode BDF和原码BDF。每套21980个原码、21885个Unicode字与21980个原码导出均核对尺寸、bearing、advance及像素，原全局ascent／descent／行高一致。
- 源文件检查覆盖原SWIDTH记录、94个原ASCII及U+0020缺省。公开单元测试仅用自制合成点阵，涵盖格式组合、坏表、映射、BDF指标和路径／非普通文件／不覆盖反例，不需要下载字体。
- 同Unicode对照了指定HZK、Beijing／ISAS、DEC、Firefly及WQY12点来源；12／14／16点还与SimSun 5.03原生1-bit位图层逐20902汉字核对，分别只有170／118／162字紧裁墨迹相同，不是同一套。方正12／14／24只比较了网站固定样文，不据此推断全库关系。

这些结论足以排除本轮所查主要已有来源的整库重复，但不是穷尽所有历史字体的去重，也不是证明每一个字均为独立手绘。归档来源、历史版权标注和点阵差异均不能替代使用许可。

## P908相关研究变体

2026-11-07按用户选择，将已发布P908中号合并到14点条目的相关来源说明，不再单列。GB汉字精确同形2407/6763（35.591%），共同CJK为5740/15763（36.414%）；允许±2px平移、不缩放后多数字形仅少量像素差异，但不证明来源关系、复制方向或授权链。Sun本体原像素、字框、覆盖及来源不改，不借用P908补字。P908的原生16高行格、13×14典型字面及独立覆盖、来源、权利与SHA锁定方法详见[手机研究记录](phone-gdr.md)。
