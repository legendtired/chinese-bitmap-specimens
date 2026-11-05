# 字库获取与导出方法

字体文件、原始字模和网页预览不是同一种东西。先按条目中的来源取得正确版本，再按格式选择下列方法。所有转换都在本地完成；使用、修改与再分发仍以原许可为准。

## 已有可运行方法

- **文曲星 NC1020**：已核验的 `obj_lu.bin` → Unicode BDF，Python 标准库。[步骤与脚本](nc1020.md)。
- **Casio XD-A10000**：`china12z.cjf`／`china24z.cjf` → Unicode BDF，Python 标准库。[步骤与脚本](casio-exword.md)。
- **Panasonic FS-UV1**：已核验的汉字 ROM → BDF。[步骤与脚本](panasonic-fs-uv1.md)。
- **HZK12／14／16／16S／24F／24H／24K／24S**：已核验源文件 → Unicode BDF，Python 标准库。[步骤与脚本](hzk-export.md)。
- **TTF／TTC 内嵌黑白点阵、Unicode PCF**：按原位图层导出 BDF，需 Python 与 FreeType。[步骤、已验证范围与脚本](bitmap-export.md)。
- **Z工坊 RoundPix16／DiamondPix 的 KBITX 原稿**：用作者格式工具导出 BDF，再修正字符计数；Diamond 有5个灰度像素会单色化。[步骤、校验与限制](kbitx-export.md)。

BDF 是点阵交换格式，不是所有系统都能直接安装的 TTF。用支持 BDF 的软件打开；不要为了“安装”把任意矢量字体重新栅格化后当作原点阵。

## 本来就是 BDF：不必再提取

GNU Unifont、GNU intlfonts、M+ Bitmap、Shinonome、JF Dot 的 BDF 镜像、缝合像素的 BDF 发布包及部分作者原始 BDF，直接在条目所列的项目目录或 Releases 选择对应文件。`.bdf.gz` 解压后即为 BDF；`.tar.gz`／`.zip` 先解包，再选条目注明的文件。

BDF 的编码不一定是 Unicode。读取头部 `CHARSET_REGISTRY`／`CHARSET_ENCODING`；例如 GB2312、Big5、JIS X 0208 都不能只改文件扩展名或编码标签就变成 Unicode。M+／Shinonome 等日文 BDF 的汉字与西文可能分别存放，应按原项目配对，不从别的字体补字。

本仓库可将 Unicode、GB2312 或 Big5 BDF 的原像素渲染为 PNG，用于核对：

```sh
python3 -m pip install Pillow
python3 scripts/workspace.py inspect-bdf --font input.bdf
python3 scripts/workspace.py render-bdf --font input.bdf --encoding unicode --text "视野无限广，窗外有蓝天。" --output local-research/generated/check.png
```

按原文件选择 `--encoding`，不要对 JIS 或 CNS11643 文件误用 Unicode。渲染只产生 PNG 与缺字报告，不导出新字体。

## 已有安装字体：按原项目使用

原项目直接提供的 TTF／OTF 可按其安装说明使用，无需先转换成 BDF。例如 KH Dot 的 TTF 发布包与多数现代像素字体。像素形状的轮廓字体不一定含内嵌位图，不能因为外观像点阵就套用内嵌点阵导出脚本。

## 仍需专门处理的格式

以下条目目前没有本站已验证的一键导出脚本，来源入口不等于转换工具：

- **Sony G90、FlipperCN**：固件里的专用字模布局／U8g2 压缩流，不能套用通用 TTF 提取脚本。
- **Palm CJKOS**：PDB 内 FBLK 资源；10点与12点打包方式不同，需要专用解析和编码核验。
- **HZK16F、HZK11US**：前者以 GB2312 槽位存放繁体字形；后者的部分符号与 ASCII 映射未可靠核定，不能直接声称得到准确 Unicode 字库。
- **HBF、CNS40**：需同时取得描述文件和它引用的全部 BIN／字模文件，编码与范围由 HBF 决定；不是单独下载一个 BIN 即可。
- **DEC Tru64**：先从条目指定光盘的 `WORLDWID/KIT/IOSZHTFONTP505` 或 `IOSZHSFONTP505` 取出原 PCF，再核对其 Big5／GB2312／CNS11643 编码。当前通用脚本不承诺支持非 Unicode PCF。
- **ELISA、TUMBLED**：原始 FNT 和 glyph/shape 文本各有自己的规则，需使用对应解析工具；不能改后缀充当 TTF。

PSA C屏继续通过条目中的联系入口申请试用，私有固件和完整字模不公开。MN1871681、MS6459 与 ChinaSea 等资料或字符表重建，不能据此导出不存在的完整字体。汉仪等正交轮廓设计也不等同于 EBDT 内嵌点阵；是否允许转换先看具体许可。
