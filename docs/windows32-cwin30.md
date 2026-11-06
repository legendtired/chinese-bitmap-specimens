# Windows 3.2 宋体点阵：原盘验证与提取

本次未读取实体软盘；来源为第三方公开存档，未独立证明其官方分发链。

本页对应 Windows 3.2 简体中文版第三方存档安装盘镜像中的 SIMSUN13.FON 和 SIMSUN20.FON。仅提供固定字样、格式说明与**不含字模的脚本**，不分发完整字体。公开存档不等于开放再分发或商用许可。请自行确认取得原盘与使用字体所需的权利。

它们是存档镜像保存的点阵，不是在本项目中由 TTF 取模；这不等于已经证明最初的逐点手绘或手修历史。不要将这两款改称 MS Song/MS Hei，也不要与 Solaris 中易宋体混同。

## 来源与固定校验值

[Windows 3.2 简体中文版第三方存档资料页](https://archive.org/details/microsoft-windows-3.2-simpl-chinese-3.5)。定位 `Microsoft Windows 3.2 (Simpl. Chinese) (3.5)/DISK6.img`。

DISK1 的 SETUP.INF 明确列出 `6:simsun13.fon`、`6:simsun20.fon`。DISK6 保存相应 SZDD 压缩文件。全部处理为离线读取镜像、解压和读取数据；无需运行 SETUP、Windows、EXPAND.EXE 或其他原盘程序。

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| DISK6.img | 1474560 | `3f769322784d0c7e64530075ba0b9f444025590931f22b2d16d134b74e741f17` |
| SIMSUN13.FO_ | 152435 | `f0051cbef4065420ce25201fa909368fa2e7da037a5121dff8c5bd25b3dd8dd0` |
| SIMSUN13.FON | 204830 | `740a69421666667e734e356f536b8684d55cefe1e6a5e9d16fe80c438161b2dd` |
| SIMSUN20.FO_ | 300553 | `443c45d0eb8d9059dcca90d70a68040f897bf134c06bdf35120ff77f24938215` |
| SIMSUN20.FON | 473528 | `f245986e77adbb467dcbef6428e1a7abb01ccaf40ea61cc4a680c5dcdc445b9e` |

脚本只接受这些已核验版本，其他版本一律停止，不凭文件名猜格式。

## 标准库脚本

脚本：[`scripts/windows32_bitmap_export.py`](../scripts/windows32_bitmap_export.py)。仅依赖 Python 标准库，无网络下载、无系统安装、无矢量渲染，也没有内嵌任何原字体数据。

```sh
python3 scripts/windows32_bitmap_export.py local-research/windows32/DISK6.img --size 13 --output local-research/generated/windows32/13
python3 scripts/windows32_bitmap_export.py local-research/windows32/DISK6.img --size 20 --output local-research/generated/windows32/20
```

也可将相应的已核验 `.FO_` 或 `.FON` 作为输入。默认只生成“视野无限广，窗外有蓝天。”、“片版牌局”、`0123456789 AaBb GgMm !?:+-.` 三组原生尺寸 PNG、网站的固定两行PNG与覆盖报告。输出前会一次检查全部目标路径；任何一个文件已存在就整体拒绝，不先写入部分结果。

具备相应使用权时，可添加 `--export-bdf` 在本地输出完整 BDF。**不要把生成的 BDF、原FON、完整字模JSON或原盘加入本项目。**

```sh
python3 scripts/windows32_bitmap_export.py local-research/windows32/DISK6.img --size 13 --output local-research/generated/windows32/13 --export-bdf
```

BDF 含全部 7445 个标准 GB2312 双字节字符，加95个可打印 ASCII，共7540字形。为避免把未知字段当作排版事实，BDF 明确采用左边距0、bottom=0、ascent=字框高、descent=0的上对齐固定字框约定；这不是对 Windows 原始基线的恢复。字形像素、汉字字框、ASCII字宽不变。

## CWIN30 的已核验解码范围

这里的 `.FON` 不是普通 NE 格式 Windows 位图资源文件。头部为 `CWIN30    `，编码标记为 `GB2312`。下列字段仅描述这两个固定SHA文件中实际使用并验证的内容，不声称完整解释所有历史CWIN30版本。

| 偏移 | 类型/含义 | 13点 | 20点 |
| --- | --- | ---: | ---: |
| 0x00 | 10字节签名 | CWIN30及4空格 | 同左 |
| 0x8C | 6字节编码名 | GB2312 | GB2312 |
| 0x9E / 0xA0 / 0xA2 | 三个LE16尺寸字段，本版本相等 | 13 | 20 |
| 0xAE | LE16半角字宽 | 7 | 10 |
| 0x110 | LE32 ASCII位图区偏移 | 288 | 288 |
| 0x114 | LE32 双字节位图区偏移 | 1952 | 5408 |
| 0x11C | LE16 每ASCII槽字节数 | 13 | 40 |
| 0x11E | LE16 每汉字槽字节数 | 26 | 60 |

- 每个字模按行存储，每行最高位在左，存储位0为墨迹、1为背景。反相只是统一前景语义，不改变字形。
- 13点汉字每行2字节，末3位为字框外行填充；20点汉字每行3字节，末4位为行填充。ASCII分别为7×13与10×20字框，行存储分别1与2字节。
- ASCII为独立的128槽区，原码位就是槽序号。导出只用U+0020至U+007E共95个可打印字符。空格也来自本字库的对应空槽；不借用其他字体。
- 双字节区依次存放A1–A9与AE–F7区，跳过未分配的AA–AD四区；每区第二字节为A1–FE共94槽。
- 对代码 `(lead, trail)`，槽序号为 `(lead−0xA1−skip)×94+(trail−0xA1)`，其中lead≥0xAE时skip=4，否则skip=0。
- 仅使用严格GB2312解码成功的码位，不把未分配槽强行映射到Unicode。有效标准双字节字符7445个，其中6763汉字全部非空。
- 13点双字节区物理上有7803槽，比83×94多一个尾槽；20点有7802槽。额外/未分配槽不冒充标准字符。

真实汉字存储字框分别13×13、20×20。13点中6040/6763汉字墨迹为13×13；20点中5188/6763汉字墨迹为18×18，最大墨迹宽和高为19×19。“20点”不能改标为18×18原始字框。

## 独立解码与往返检查

每款均通过：

1. 标准库“逐行大端整数+位移”解码，与独立NumPy逐位解包的7540个Unicode字形逐字、逐行完全一致。
2. Pillow原始1位图解码，使用另算的源偏移，对同样7540字形逐像素完全一致。此过程不调用字体渲染器或FreeType。
3. 全部物理ASCII与双字节槽，包括未映射槽、控制码和行填充，经过Pillow位平面后重打包，与源数据逐字节一致。13点为7931槽/204542字节；20点为7930槽/473240字节。
4. BDF由独立文本解析器读回后，7540字形的字宽、字高、行位图均一致。
5. 三组固定样图的像素与初始解码结果相同；改变源文件任意已测试字节后固定SHA检查拒绝输入。

## 与已有字样的去重范围

核验研究基线的全部224个旧目录样图的SHA256，其中223项有可比较的同一汉字；ChinaSea外字资料图没有相同测试字。13点和20点均与223项存在同字像素差异。比较允许任意平移、不缩放、不改像素。

对样句的10个汉字，保守地允许在每张旧图的任意位置寻找匹配后，13点最小合计仍差138像素（HZK14样张）；20点最小合计差564像素（方正18样张），与Solaris20合计至少差619像素。因此不是整组只有1–3像素的微调。该结果是样字排重，不是对所有历史字库做全量原创性证明。

同盘16点与Beijing/ISAS16的6760/6763个汉字完全相同；24点与HZK24S的6758/6763个汉字完全相同，均按近重复排除，没有另增新款。

原盘SIMSUN.TTF与SIMHEI.TTF仅有常规轮廓表，不含EBDT/EBLC、bdat/bloc等内嵌位图，本项目没有渲染它们生成样张。配套TrueType名称表载Great Wall Computer Co. 1994，只作载体背景，不能据此独立证明每个FON点阵的作者。

## 测试与精确重绘

```sh
python3 tests/windows32-cwin30.test.py
WINDOWS32_SOURCE=local-research/windows32/DISK6.img python3 tests/windows32-cwin30.test.py
```

不带私有源时检查合成位图、位序/填充、边界、SZDD回引用、错误SHA拒绝、禁止覆盖、固定样图SHA；带镜像时另检查全部7540字形、BDF回读、两行PNG精确重绘和修改源文件后的SHA拒绝。

网站两行PNG使用纯标准库编码，汉字与原生ASCII两行间4px，字间另加1px样图排版间隔；这些间隔不改变字模或导出BDF的字宽。

- win32_simsun_13.png：`19d238a771141c971fc81264093e63e199dddaaebefaa86ca79b5dd5510c6de4`
- win32_simsun_20.png：`73ff1c50efaef100f781d6bb2db796f726fee2dd7ddb7a76396acad6cdfb4ef1`

独立原始位图核对另见 [`scripts/verify_windows32_bitmap_decode.py`](../scripts/verify_windows32_bitmap_decode.py)，需Pillow，仅调用1-bit原始像素解码，不调用字体渲染。

```sh
python3 scripts/verify_windows32_bitmap_decode.py local-research/windows32/DISK6.img
```

## 已撤下字体的交叉核验

为避免换来源重新引入已排除字模，另从 [Solaris第三方存档镜像](https://archive.org/details/solaris-7-1199-sparc-cs) 取回 SUNWcxmft 包的 song12/14/20.pcf.Z。解压后的SHA分别严格吻合撤回记录：

- 12：`81e5bd76ab37f1c1d055da3b29cd550accf855aae6a747d6e8e91c55381becb3`
- 14：`523f94245fa2fcf72d82feebaadc2cc3dbe6223191ed3387253a57da136399a0`
- 20：`1c19696c3f7d1445fe6a969522224de1283f7f389e6e2fe972de0901432bef08`

对每组共同6763汉字，去除外侧空白后逐像素比较：Windows13与三组分别0/1/0字相同，Windows20与三组均0字相同。再允许水平、垂直各±4px整数平移，保留全部墨迹、不缩放：Windows13对Solaris12/14的汉字差异中位数55/38像素，Windows20对Solaris20为92像素；仅差≤3像素的字分别5、35、1个，不构成近整库复用。已撤下的样图和完整来源字体没有随本材料重发布。

Archive元数据的年份与配套字体名称表年份存在差异；未将存档条目日期用于认定设计或发行年份。


BDF按75dpi声明尺寸，SWIDTH使用 `round(width×72000÷(size×75))`，全角字符为960；这是导出度量的一致性约定，不修改任何位图或固定预览像素。
