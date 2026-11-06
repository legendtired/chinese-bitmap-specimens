# 字库获取与导出方法

字体文件、原始字模和网页预览不是同一种东西。先按条目中的来源取得正确版本，再按格式选择下列方法。所有转换都在本地完成；使用、修改与再分发仍以原许可为准。

## 已有可运行方法

- **四通 MS-2401H 四套32点**：校验BIOS与CA字库ROM后，解压导出每套6763个汉字的Unicode BDF。[步骤、样式编号与边界](stone-ms2401h.md)。

- **文曲星 NC1020**：已核验的 `obj_lu.bin` → Unicode BDF，Python 标准库。[步骤与脚本](nc1020.md)。
- **Casio XD-A10000**：`china12z.cjf`／`china24z.cjf` → Unicode BDF，Python 标准库。[步骤与脚本](casio-exword.md)。
- **Panasonic FS-UV1**：已核验的汉字 ROM → BDF。[步骤与脚本](panasonic-fs-uv1.md)。
- **HZK12／14／16／16S／24F／24H／24K／24S**：已核验源文件 → Unicode BDF，Python 标准库。[步骤与脚本](hzk-export.md)。
- **HZK11US**：只导出已核验的6763个汉字；682个非汉字记录因映射不可靠而排除。[汉字子集脚本与范围](hzk11us-export.md)。
- **FlipperCN 20240803**：固件内604字菜单子集 → Unicode BDF，保留逐字指标。[步骤与脚本](flippercn-export.md)。
- **Palm CJKOS 10／12点**：专用 FBLK PDB → BDF；严格可往返码位转换为 Unicode，未映射／重复槽位保留为未编码字形。[正确来源版本与脚本](cjkos-export.md)。
- **TUMBLED 18／24**：原生 glyph/shape 文本 → Unicode BDF，保留组合、位移与超出样句字框的原像素。[步骤与脚本](tumbled-export.md)。
- **TTF／TTC 内嵌黑白点阵、Unicode PCF**：按原位图层导出 BDF，需 Python 与 FreeType。[步骤、已验证范围与脚本](bitmap-export.md)。
- **Z工坊 RoundPix16／DiamondPix 的 KBITX 原稿**：用作者格式工具导出 BDF，再修正字符计数；Diamond 有5个灰度像素会单色化。[步骤、校验与限制](kbitx-export.md)。

### 保留原编码或源槽位的导出

这些方法保留字模，但输出不等于可直接输入任意 Unicode 文本的字体：

- **DEC Tru64 10项**：本地 ISO 提取两个字体子集，解包后用 `pcf2bdf` 转换；保留 Big5／GB2312／DEC 专有 CNS 原编码。[步骤与命令](dec-cns-export.md)。
- **CNS40**：校验 HBF 和两个 BIN，再导出6085字的 CNS11643-92 第1字面原编码 BDF。[步骤与脚本](dec-cns-export.md)。
- **Sony G90／HZK16F**：分别导出4096／8368个源槽位，使用自定义编码，不猜 Unicode。Sony 来源访问限制与前景推断另有说明。[步骤与脚本](source-slot-export.md)。

BDF 是点阵交换格式，不是所有系统都能直接安装的 TTF。用支持 BDF 的软件打开；不要为了“安装”把任意矢量字体重新栅格化后当作原点阵。

## 本来就是 BDF：不必再提取

**ELISA** 的准确来源 `elisau10.tgz` 内已有 JIS X 0208 BDF；与目录原SHA及固定样图一致。需要 Unicode 时可重编码，不必猜原FNT。[原包获取、重编码与许可限制](elisa-export.md)。

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

- **完整Unicode映射**：Sony G90、HZK16F、DEC专有CNS等仍需独立核定，不能把可导出原槽位等同于可直接输入任意文字。

PSA C屏继续通过条目中的联系入口申请试用，私有固件和完整字模不公开。MN1871681、MS6459 与 ChinaSea 等资料或字符表重建，不能据此导出不存在的完整字体。汉仪等正交轮廓设计也不等同于 EBDT 内嵌点阵；是否允许转换先看具体许可。

- [Sharp X68000 16点获取与导出](sharp-x68000.md)：原生JIS字模、字符映射与ANK边界。

- [IBM PC DOS 中文24点](ibm-pcdos.md)：校验指定FNT，离线导出7444个标准GB2312字符及未编码IBM扩展。

- [Nokia DCT3 1999](nokia-dct3.md)：静态解出9385个原Unicode码位，含9004个原生11×12汉字，保留西文与度量字段。


- [FM Towns F20 20点](fmtowns-f20.md)：JIS原生汉字及ANK样图，导出边界分别记录。
- [Solaris 中易宋体五个字号](solaris-gbk.md)：12／14／16／20／24点原生PCF与Unicode／原码导出。

## 文曲星 PC505 14×15

[提取方法与边界](wqx-pc505.md)。仅接受已校验的原厂仿真器obj，导出7445个GB映射字符和95个可打印ASCII；原生汉字14×15，不能裁为14×14。共同基线和advance为导出约定，原始输入并非已证实的实机dump。公开目录只提供固定样图和本地提取脚本，不附完整字库。

- [MStar 电视/DVB 简体18点](mstar-18.md)：18×18存储、最大字面14×14；完整GB2312与原生ASCII，附离线导出方法。


## 仅有固定预览重绘

- **三国志Ⅴ DOS 16×14**：[解码、去重和重绘方法](san5-dos.md)。精确校验本地ZIKU.16P后，只重绘两行固定样文；符号映射与尾部尚有未核范围，不提供完整Unicode字体导出。


- [Windows 3.2 宋体13／20点](windows32-cwin30.md)：固定SHA安装盘存档、原生字框与ASCII、标准GB2312映射及无字模离线导出方法。
