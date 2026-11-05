# DEC PCF 与 CNS40 HBF 的原编码 BDF 导出

这两条路线仅处理用户自行取得的本地源文件，不下载、不安装、不公开完整字库。BDF 保留点阵和原编码；不是可直接输入任意 Unicode 文本的 TTF/OTF，也不补字或放大。

## DEC Tru64：10 项

来源入口：[历史媒体目录](https://ftp.zx.net.nz/pub/Media/Digital/)、[Tru64 中文技术手册](https://ftp.zx.net.nz/rom/V5.0Ar1094_D1/DOCS/HTML/SUPPDOCS/CHINADOC/CHINACH5.HTM)。输入为用户自行取得的 `AG-RHB7B-BE.iso`，卷标 `V5.0Ar1094_A1`。普通 ISO9660 名称显示 `WORLDWID/KIT`，Rock Ridge 名称显示 `Worldwide_Language_Support/kit`；工具看到的路径可能不同。

使用本站脚本，从本地光盘镜像只提取两个经过 SHA256 验证的中文字体子集：

```sh
python3 scripts/extract_dec_font_subsets.py AG-RHB7B-BE.iso dec-subsets
mkdir dec-input
uncompress -c dec-subsets/IOSZHSFONTP505 | tar -xf - -C dec-input
uncompress -c dec-subsets/IOSZHTFONTP505 | tar -xf - -C dec-input
```

这两个输入是 Unix compress 压缩的 tar，不是普通 zip。解包后字体位于 `dec-input/usr/i18n/lib/X11/fonts/decwin/75dpi/`。解包仅用于本地研究，目录中的其他字体不因此成为本站收录项。

使用 [Debian pcf2bdf 软件包](https://packages.debian.org/pcf2bdf)提供的 `pcf2bdf`；已核验版本为 1.07。Debian／Ubuntu 可从系统软件源安装 `pcf2bdf` 与提供 `uncompress` 的 `ncompress`。下列转换命令请使用尚不存在的输出文件名，避免工具覆盖旧结果：

```sh
pcf2bdf -o dec-heiti-16.bdf dec-input/usr/i18n/lib/X11/fonts/decwin/75dpi/adecw_heiti_gb2312_16_16_75.pcf
```

10 项输入文件如下：

| 目录条目 | PCF 文件名 |
| --- | --- |
| dec_hei_big5_16 | adecw_hei_big5_16_16_75.pcf |
| dec_hei_big5_24 | adecw_hei_big5_24_24_75.pcf |
| dec_sung_cns11643_24 | adecw_sung_cns11643_24_24_75.pcf |
| dec_sung_cns11643_32 | adecw_sung_cns11643_32_32_75.pcf |
| dec_heiti_gb2312_16 | adecw_heiti_gb2312_16_16_75.pcf |
| dec_fangsongti_gb2312_24 | adecw_fangsongti_gb2312_24_24_75.pcf |
| dec_songti_gb2312_34 | adecw_songti_gb2312_34_34_75.pcf |
| dec_heiti_gb2312_34 | adecw_heiti_gb2312_34_34_75.pcf |
| dec_kaiti_gb2312_34 | adecw_kaiti_gb2312_34_34_75.pcf |
| dec_fangsongti_gb2312_34 | adecw_fangsongti_gb2312_34_34_75.pcf |

2026-11-05 已核验：10 个 PCF 的 SHA256 均与目录记录一致；合计 99,071 字形的原编码、逐字位图、BBX、DWIDTH、基线均与导出的 BDF 一致。pcf2bdf 保留原字符集属性和 DEFAULT_CHAR，但去掉旧式 `RESOLUTION=103` 属性，保留 `RESOLUTION_X/Y=75`。因此不能声称所有元数据逐字节不变。

导出仍是 Big5、GB2312 或 `DEC.CNS11643.1986-2` 原编码，不是 Unicode。DEC 专有 CNS 编排不能当作普通 EUC-TW，GB2312 文件中的默认字形/扩展槽也不能静默丢弃；转换 Unicode 需另行验证映射、重复映射和未映射字形。34×34 条目必须保留原字框和 26/8 基线，不能裁成 32×32。

不推荐对这些 PCF 直接使用 monobit 0.48：实测其双字节编码索引会错配码位。PCF→BDF 应使用以上已验证的 pcf2bdf 路线，不能只凭“命令运行成功”判断编码正确。

## CNS40：1 项

来源入口：[Debian 历史归档目录](https://archive.debian.org/debian/pool/main/h/hbf-cns40-1/)。原始包名为 `hbf-cns40-1_1.0.orig.tar.gz`。从本地包解压后，将 `cns40-1.hbf`、`4040w0.bin`、`4040w1.bin` 放在同一目录；原包中的路径为 `texmf/fonts/hbf/chinese/cns40/`。

```sh
tar -xzf hbf-cns40-1_1.0.orig.tar.gz
python3 scripts/cns40_hbf_to_bdf.py texmf/fonts/hbf/chinese/cns40/cns40-1.hbf cns40-source.bdf --report cns40-source-report.json
```

脚本仅接受经过核验的这一套 HBF/BIN SHA256，不是任意 HBF 转换器。不覆盖已有文件；缺文件、修改过的源文件或其他版本会明确拒绝，不以猜测继续导出。

2026-11-05 已逐字验证全部 6,085 字形：保留 CNS11643-92 plane 1 双字节原码、40×40 位图、advance=40、BBX=40×40+0−6、ascent/descent=34/6 和 DEFAULT_CHAR=0x2121，未改成 Unicode。也已通过 bdftopcf 的格式读取验证。整个过程未裁切、重绘、借字或归一化尺寸。

原 HBF 自身存在度量元数据不一致：`SIZE 40 150 150`，而 `RESOLUTION_X/Y` 为 75。脚本保留两者，在 JSON 报告明确提示；BDF 必需的 SWIDTH=480 依据原 SIZE 和像素字宽派生，不代表源库包含轮廓。像素字宽和基线不受改变。

monobit 0.48 的裸 HBF→BDF 命令不适用于保留本条目原码：它将原 0x2121 变为 0x012121，字符集属性不再保留原 plane 信息，且实测没有产生 Unicode 字符标签。不得把这样的输出宣称为原码保真或已完成 Unicode 映射。

## 权利与使用限制

转换成功不等于取得字体使用或再分发许可。DEC 的 PCF 版权属性与 CNS40 位图的来源仍需核对；CNS40 中“header file is in the public domain”只明确指 HBF 头文件，不能据此推断全部 BIN 字库开放。本站只提供方法和代码，不随代码附带完整源字体或导出的字库。
