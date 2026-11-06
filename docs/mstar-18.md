# MStar 电视/DVB 简体点阵：18×18存储、最大字面14×14

这是一份电视/DVB源码中的完整简体位图资源，不是已确认型号的零售电视ROM，也没有证据认定它与Sony字幕机同源。只收录本18点资源，两份24点候选不收录。

## 来源、尺寸和覆盖

[固定版本的来源浏览页](https://github.com/schreibikus/8831-16714/blob/e1f844b204be3f045a425520503331a6e059ac9d/tv-ap/dvb/ui2/font/Simp_ch_18X18.bin)。本地文件应为490,262字节，SHA-256：

`b2860bdb2486c5901bcebe3b29d4e009ec9151915c4d9640a8009d039903f0bf`

- 未压缩1bpp、18×18存储单元，每槽56字节：18行×3字节及2字节尾填充。
- 原生Unicode表7,804槽，包含全部6,763个GB2312汉字及95个普通可打印ASCII。
- 汉字最大实墨14×14；5,491字正好14×14。其余汉字较窄或较矮，不人为补满。
- 全部6,763个汉字非空、去外围空白后仍有6,763种不同图案。全表有226空白字形，包括空格和私用码位；不把这些槽当作汉字覆盖。
- 18×18是存储框，14×14是最大墨迹，均不等于已验证的实机行距。

[头部格式](https://github.com/schreibikus/8831-16714/blob/e1f844b204be3f045a425520503331a6e059ac9d/core/api/include/msAPI_Font.h#L209-L225)与[DTMB镜像清单](https://github.com/schreibikus/8831-16714/blob/e1f844b204be3f045a425520503331a6e059ac9d/scripts/check_bin/CheckBinSize_nasa_64m_dtmb.in#L5)直接支持资源结构及电视用途。源码历史中的2017-06-20提交时间不是字体设计年份；正式字体名、设计者、制作年代及零售机型仍未确认。保存的位图不自动证明最初手绘制作。

## 排版与固定样张

[计宽代码](https://github.com/schreibikus/8831-16714/blob/e1f844b204be3f045a425520503331a6e059ac9d/core/api/msAPI_OSD.c#L612-L770)支持可变宽与固定宽两种模式：VARWIDTH用原bbox宽度，否则用存储宽18；额外gap、缩放及kerning由其他选项决定。

本站固定样图和默认BDF采用**原bbox宽度、不加可选gap/kerning、不缩放**。汉字字进15px，ASCII保留原宽度，例如空格7、数字0为8、A为11。每字完整18×18像素和空白都保留，不将尾部空白误画成遮盖后字的背景。共同BDF基线y=0、两行间4px仅为导出/展示约定，不冒充设备截图。全部原bbox的x/y均为0；四个原字段逐字保存在BDF注释中。

可用`--layout fixed`选择源码支持的18px固定字进；两种模式的每字像素完全相同，不作为两款字体收录。

## 本地离线导出

先自行取得并确认有权处理来源文件。仓库不附原字库，也不提供下载直链。脚本只接受上述精确哈希，不执行固件、联网或栅格化轮廓，不覆盖现有输出。

```sh
python3 scripts/mstar_18_to_bdf.py local-research/Simp_ch_18X18.bin --inspect
python3 scripts/mstar_18_to_bdf.py local-research/Simp_ch_18X18.bin local-research/mstar18.bdf
python3 scripts/mstar_18_to_bdf.py local-research/Simp_ch_18X18.bin local-research/mstar18-fixed.bdf --layout fixed
python3 scripts/mstar_18_to_bdf.py local-research/Simp_ch_18X18.bin local-research/sample.bdf --text "视野无限广，窗外有蓝天。"
```

默认导出7,804个原Unicode字形，包括原本为空的槽位；缺字及空子集报错，不借用其他字体。BDF是交换格式，转换不授予使用或再分发权。

已完成：全7,804字、2,528,496像素与独立位索引算法核对；BDF回读核对全部字形、字框和字进。软件验证不等于实机测试。

## 去重范围

以收录前222条目录为基准，180条有Unicode映射的原字模记录比较896,580对共同汉字，含172条完整已取得来源、7条预览子集、1条设备UI子集。其中78条覆盖全部6,763个GB2312汉字。另5条缺可靠Unicode映射的来源查整套图案池；36张当前固定样图查312个共同汉字；1张纯参考图不作原生像素比较。

未发现整套或高比例精确重复。最高同码位相同数为MingLiU15的12/6,763，HZK14为10/6,763，Ayu18与Osaka18各0/3,331。只去除外围空白作比较，不缩放或改字。另查26条可映射的已移除/合并来源，/efont/16与SimSun14各仅2个汉字相同，其余无同码位相同；部分已移除来源没有完整原字模，不能声称穷尽全历史字库。

这些结果排除已查材料中的直接整库复制，不证明原创、全球唯一或设计谱系。本站不重新引入已拒绝候选。

## 版权边界

未找到这份字库的独立开放许可或整库再分发授权。[根README](https://github.com/schreibikus/8831-16714/blob/e1f844b204be3f045a425520503331a6e059ac9d/README.txt#L5-L16)及周边源码有MStar专有声明，不能据此确证具体中文字形权利人。

仓库的FreeFontNotice针对Gentium/Nanum，FreeType许可针对引擎，均不能套用于本中文资源。公开镜像不等于字体授权。本站仅提供固定小样、来源及不含字模的导出脚本，不公开BIN/BDF或全字形数据，不标OFL、开源或免费商用。
