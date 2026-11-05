# KBITX 原稿导出为 BDF

[返回获取与导出方法](font-export.md)

适用于本目录的 **Z工坊像素圆体 16×16** 和 **DiamondPix 16×16**。使用原生 KBITX 字形数据，不经过 TTF 栅格化、缩放或缺字补配。输出留在本地；字体使用与再分发仍按原来源许可执行。

## 准备

- Java 运行环境；本次实测 OpenJDK 21.0.13。
- Python 3.9+，仅运行下方的 BDF 字符计数修复脚本，不需要第三方 Python 包。
- 在 [Bits'N'Picas v2.2.2 发布页](https://github.com/kreativekorp/bitsnpicas/releases/tag/v2.2.2) 获取 `BitsNPicas.jar`，放到 `local-research/tools/`。
- 从下列上游浏览页取得原稿，放到 `local-research/sources/`：
  - [RoundPix16 原稿](https://github.com/Astro-2539/ZLabs-RoundPix-16px/blob/df114b8dd1564e722e09f3e726b919f2a27d0afd/data/ZLabsRoundPix_16px_CN.kbitx)
  - [DiamondPix 原稿](https://github.com/Astro-2539/ZLabs-DiamondPix-16px/blob/d243cf3d3d66ace3aa61d692c68f7306b57e55ef/data/ZLabsDiamondPix_16px_SC.kbitx)

转换命令见[官方说明](https://github.com/kreativekorp/bitsnpicas#converting-bitmap-fonts)。monobit 0.48.0 不提供 KBITX reader，不能直接代替此步骤。

## 导出

从本站仓库根目录执行。生成文件如已存在，先自行移走；修复脚本拒绝覆盖输入或已有输出。

```sh
mkdir -p local-research/generated
java -Djava.awt.headless=true -jar local-research/tools/BitsNPicas.jar convertbitmap -f bdf -o local-research/generated/round16.raw.bdf local-research/sources/ZLabsRoundPix_16px_CN.kbitx
python3 scripts/fix_bdf_char_count.py local-research/generated/round16.raw.bdf local-research/generated/round16.bdf

java -Djava.awt.headless=true -jar local-research/tools/BitsNPicas.jar convertbitmap -f bdf -o local-research/generated/diamond16.raw.bdf local-research/sources/ZLabsDiamondPix_16px_SC.kbitx
python3 scripts/fix_bdf_char_count.py local-research/generated/diamond16.raw.bdf local-research/generated/diamond16.bdf
```

Bits'N'Picas v2.2.2 的 BDF 导出器会把 `.notdef` 写入文件，却未计入 `CHARS`。随附脚本只修正这一行的数字，保留其余所有字节。它不是通用 BDF 修复器，也不会规范化其他元数据。

实测 DiamondPix 原稿没有 DOCTYPE，工具会打印 XML 校验警告但继续输出。不能仅据 `DONE` 或退出码判断完整性；本次另行核对了全部字形。新版本输入仍应重新核验。

## 验证范围与限制

2026-11-05 对以下固定输入进行了独立 KBITX 解码与输出 BDF 对照：

- RoundPix16：7,859 个 Unicode 字形，加 1 个 `.notdef`，合计 **7,860**。全部原像素、位图尺寸、左右位置、基线位置和 advance width 一致；全部源像素为 0/255。
- DiamondPix：2,637 个 Unicode 字形，加 1 个 `.notdef`，合计 **2,638**。全部码位、位图尺寸、bearing 和 advance width 一致。**U+5E7E「幾」有 5 个透明度值为 230 的像素**；官方 1-bit BDF 导出按 `>=128` 转黑，其余源像素为 0/255。因此它是原格点上的单色导出，不能称整个源文件灰度无损。
- 两份源文件均没有 kerning 对。方法不保证其他 KBITX 的 kerning、灰度或应用专有元数据无损保留。
- Unicode 编码沿用 KBITX 的 `u`；`.notdef` 保留为 `ENCODING -1`。不做简繁替换，不给缺字补配。
- BDF 的 `BBX` 和 `DWIDTH` 是逐字数据，不可把所有字形强制铺成 16×16。导出器生成的 `SIZE`、`POINT_SIZE`、`SWIDTH` 和 FONT 名称等是其自身规则，不能据此反推原稿完整排版参数。此处只修复字符计数，不宣称严格规范化了整个 BDF。
- 该流程只生成 BDF 点阵文件，不是供所有桌面应用直接安装的字体。安装试用应选上游已提供的原版 TTF；不要选 MD/MS 特效版代替原稿。

## 固定输入与结果校验值

SHA-256：

```text
BitsNPicas.jar（v2.2.2）
22685a52bc1a7f26680f80197548e74dc61a9f58eb083d6f700220a48a1165a6

ZLabsRoundPix_16px_CN.kbitx
60216332f2f2c8fe5ccb39ce41416f02c077d5b317a1765e5640a2b6dbd19014
修复 CHARS 后的 round16.bdf
bc8cfa33c7f1b36dedee61317f37f5b39b8d63ea0c6637017b122edc157de6e2

ZLabsDiamondPix_16px_SC.kbitx
43d13cc7de00e0f4e303754f9a7cdc4e1d00e0d723688358459f73c35a99b50f
修复 CHARS 后的 diamond16.bdf
0d2959d58d4347bf2068026a8630e776e099baeb6abbafa3a0ae0fe402e83e38
```

校验值限定本次输入及工具版本。上游更新后不同，不应直接套用上述全量验证结论。本站不附带原稿、完整 BDF 或工具 JAR。
