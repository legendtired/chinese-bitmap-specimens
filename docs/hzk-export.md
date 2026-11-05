# HZK 转为 BDF

适用于本站 HZK12、HZK14、HZK16、HZK16S、HZK24F／H／K／S 八项。脚本只转换已核验的具体文件，不是通用 HZK 解析器。

## 获取与导出

1. 在 [aguegu/BitmapFont 的 font 目录](https://github.com/aguegu/BitmapFont/tree/master/font)查看对应文件，并自行取得原始二进制。保存网页 HTML 不能作为输入。
2. 将文件放在被忽略的 `local-research/hzk/`，不要提交到仓库。
3. 在项目根目录运行，要求 Python 3.9+，转换本身只用标准库：

```sh
mkdir -p local-research/generated
python3 scripts/hzk_to_bdf.py --list
python3 scripts/hzk_to_bdf.py \
  --input local-research/hzk/HZK12 \
  --output local-research/generated/HZK12.bdf
```

产生 BDF 和同路径加 `.json` 的核验报告。脚本依据**文件大小和 SHA-256**识别版本，文件名可以改变；未知、改动或截断的输入会被拒绝。不下载字库，不内嵌字模，不覆盖已有输出，也不提供跳过校验的选项。需要重跑时请使用新的输出名称。

BDF 可用于支持点阵 BDF 的工具，不等于系统可直接安装的 TTF。不要将转为轮廓、缩放后的字体称为原生点阵的新字号。

本项目已有 BDF 诊断和渲染工具；渲染另需 Pillow：

```sh
python3 scripts/workspace.py inspect-bdf \
  --font local-research/generated/HZK12.bdf
python3 scripts/workspace.py render-bdf \
  --font local-research/generated/HZK12.bdf --encoding unicode \
  --text "视野无限广，窗外有蓝天。" \
  --output local-research/generated/HZK12-sample.png
```

## 保留与省略

- 原文件从 `A1A1` 开始按94列区位排序。字模偏移为 `((高字节−0xA1)×94 + 低字节−0xA1)×每字字节数`。每字依次存顶行至底行，每行高位在左；12／14／16点每行2字节，24点每行3字节。12／14点右侧填充位须全零。
- 仅将 Python 严格 `gb2312` 编码可往返的已分配码位映射为 Unicode。未分配、厂商扩展和其他未知槽位不猜映射，报告记录被省略的有墨迹槽位。
- 保留原始字框、行字节和全角宽度。没有普通 ASCII，`Ａ`（U+FF21）不会复制到 `A`（U+0041）；原展示中的全角英数也不成为半角字。
- 保留原库全角空格 U+3000。其他已分配但全空的字模视为缺字，不生成替代字形。HZK16 缺 `┆┇┈┉┊┋` 六字，导出7,439字；其余七项各7,445字。这是所导出范围，不是整个原文件的总字形数。
- HZK 原数据没有独立基线与 bearing 元数据。输出采用整个原字框、`DWIDTH=字宽`、`BBX` 偏移0,0、上升高为字高、下降高为0的明确排版约定，不宣称恢复了原厂排版指标。

**不支持 HZK16F 与 HZK11US。** HZK16F 在 GB2312 简体槽位放置繁体字形，直接转码会把繁体形错误标为简体 Unicode；没有完整核定的对应表前不能据此导出通用 Unicode 字体。tomzbj 的 HZK11US 是另一个 Unicode 重排格式，已知标点与 ASCII 索引不可靠，不能套用本脚本。其他同名 HZK、ASC 文件和更大字号也不在本次支持范围。

## 核验范围

2026-11-05 从上述来源取得实际文件，核对文件大小、Git blob SHA 与 SHA-256。八项的中文样句12字和全角英数／符号24字与本站既有固定样图逐像素一致，共288个字符位置，差异为0。完整导出进一步逐字回读 BDF，检查所有导出行字节与原文件一致。

文件身份见脚本 `--list`。存储与区位规则也可对照来源项目的 [Makefile](https://github.com/aguegu/BitmapFont/blob/master/Makefile)、[bitmapfont.cpp](https://github.com/aguegu/BitmapFont/blob/master/bitmapfont.cpp) 与 [block.cpp](https://github.com/aguegu/BitmapFont/blob/master/block.cpp)。样图核验不能证明所有字形的历史设计来源、语义正确性或授权。

```sh
# 不依赖原字库的合成测试
python3 tests/hzk-export.test.py

# 自行准备全部八个输入后，增加真实输入与完整 BDF 回读核验
HZK_TEST_SOURCE_DIR=local-research/hzk python3 tests/hzk-export.test.py
```

无原字库时跳过两项真实输入测试；不把跳过声称为通过。测试不附带原字模。

## 权利边界

原仓库工具代码的 GPL-3.0 不自动授予历史 HZK 字模权利。转换不会改变原字体许可；使用、商用和再分发须另行核实。本站只提供方法与转换代码，不随仓库发布原字库或导出的完整 BDF。
