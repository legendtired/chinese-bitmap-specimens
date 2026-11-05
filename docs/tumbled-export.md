# TUMBLED 原生文本 → BDF

适用于目录中的TUMBLED_18和TUMBLED_24。需要Python 3.9以上，无第三方依赖。不使用轮廓栅格化，不合成粗体，不补普通ASCII。

## 取得源文件

使用 [TUMBLED 上游仓库](https://github.com/TsFreddie/TUMBLED) 的源代码，而不是把PBF/PBL改名为TTF。保留相应目录的完整结构：

- `fonts/TUMBLED_18/font.json`、`glyphs/*.txt`、`shapes/*.txt`
- `fonts/TUMBLED_24/font.json`、`glyphs/*.txt`、`shapes/*.txt`

实测版本：[f91881acbdc9a4fa05bbc62338d25e7907517bd1](https://github.com/TsFreddie/TUMBLED/tree/f91881acbdc9a4fa05bbc62338d25e7907517bd1)。两目录的44076个源文件均已按该版本Git blob SHA-1复核。其他版本应重新核对报告和固定样图。

## 导出

输出BDF与JSON报告必须是两个不同的新文件，父目录须已存在。脚本拒绝覆盖已有文件、目录、悬空链接或输入源文件，也拒绝output/report指向同一解析路径；写入使用独占创建。重新导出请选择新的文件名。可用 `--report 路径` 指定独立报告位置。

```sh
python3 scripts/tumbled_to_bdf.py local-research/TUMBLED/fonts/TUMBLED_18 local-research/TUMBLED_18.bdf
python3 scripts/tumbled_to_bdf.py local-research/TUMBLED/fonts/TUMBLED_24 local-research/TUMBLED_24.bdf
```

同时生成 `.bdf.json`，记录所用源文件的组合SHA-256、字数、advance分布、实际边界和空字形数。导出目标目录须已存在。

## 解析规则与尺寸

规则来自作者的 [PebbleFontTool源文本读取器](https://github.com/TsFreddie/PebbleFontTool/blob/main/tool/src/lib/server/loader.ts) 和 [PBF构建器](https://github.com/TsFreddie/PebbleFontTool/blob/main/bin/pbf.ts)。

- glyph文件名是十进制Unicode码位；第一行是advance，后续各行为 `offsetTop offsetLeft shapeName`。
- shape文件第一行是 `top left`；之后每个 `#` 是一粒原像素，空格是空白。组合位置为shape原点加glyph位移；多shape取像素并集。
- 保留每字advance与bearing；不把所有字压入统一汉字框。没有对应glyph的字符不会自动使用wildcard。
- 该脚本只接受18／24原生源目录；不处理28／36来源不同的字模，也不会自动合成bold。出现区域变体文件名时停止，要求先明确选取，避免静默覆盖同码位。

实测两个目录各10978字，均无U+0020–U+007E普通ASCII。18号有49个双shape组合字，24号为单shape；两者各有1个空字形，仍保留其advance。全角英数是独立原码位，不转换成普通ASCII。

**目录中的14×19和16×25是现有样句范围，不是整库裁切框。**

- 18号advance为14（10907字）、7（70字）、8（1字）。全部原像素的存储坐标范围达23×21；例如“轍”源shape宽23，但advance仍是14，原样保留而不修形。
- 24号advance为16（10906字）、8（71字）、9（1字），整体坐标范围16×25。

`font.json`的height为18／24，是原始槽高。BDF约定基线在该高度，逐字 `BBX yoff = 原槽高 - top - bitmapHeight`。FONT_ASCENT/DESCENT扩展到容纳所有原像素：18号18/3，24号24/1；原槽高另存为 `SOURCE_LINE_HEIGHT`。因此BDF的默认行距可能与手表18／24槽高不同，不以裁边换取相同行距。

2026-11-05验证：两库共21956字经过monobit 0.48读回后，位图坐标、advance、bearing及数值Unicode编码全部一致；两项现有12字样句的PNG像素掩码差异为0。测试不将样句尺寸外推成全库固定字框。

字体按上游OFL-1.1及所附声明使用；分发时保留原许可与作者信息。本站不附完整输入或导出字库。
