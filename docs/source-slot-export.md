# Sony G90／HZK16F：保留原槽位的 BDF 导出

这两项可以导出点阵，但不能因此声称得到完整、准确的 Unicode 字库。脚本保留全部存储槽位，包括空白、保留和未识别槽位；不补字、不从别的字体取字、不猜简繁对应。

- **Sony G90**：4,096 个 24×32 槽位。默认导出与本站字样一致的推断前景，也可导出原始编码图案位。
- **HZK16F**：8,368 个 16×16 槽位，按原文件顺序逐字节保留。槽位数量不是已确认的字符数量。
- 输出自定义 `CHARSET_REGISTRY "SOURCE.SLOT"`、`CHARSET_ENCODING "0"`。`ENCODING 0` 表示第一个源槽位，**不是 U+0000**；其余数字同理。字形命名为 `slot00000`、`slot00001` 等。

本仓库只提供脚本和说明，不附带原字库、固件或完整 BDF。来源可下载不代表可以任意再分发；工具代码许可也不自动授予字体权利。

## 取得输入

### Sony G90

来源记录为 [CurtPalme Sony G90 下载资料页](https://www.curtpalme.com/SonyG90_Downloads.shtm)，对应 v1.11 Firmware code 包中的 `Tg1f0110.mot`。2026-11-05 的获取检查返回 HTTP 403，不能保证访客目前可从此页取得输入。脚本不联网、不绕过访问限制；需要使用者另行合法取得同一版本的原文件。

不要把主程序 `Tg1m0111.mot`、ZIP 本身、不同版本、经过文本换行转换的副本传给脚本。它只接受以下精确版本：

- 文件：`Tg1f0110.mot`
- 大小：1,180,052 字节
- SHA256：`1db369769fb411e50ddd0087eefe24dfe9713579ca42a2ed510f7e13a0674800`

原字形权利属于相应权利人，未获额外商业授权。拿不到正确输入时，到这里停止，不能用本站预览或别的字体拼出“完整原字库”。

### HZK16F

参见 [BitmapFont 来源项目](https://github.com/aguegu/BitmapFont) 的 [font/HZK16F 文件浏览页](https://github.com/aguegu/BitmapFont/blob/HEAD/font/HZK16F)。从来源项目取得原始二进制文件，不要保存 GitHub HTML 页面。脚本只接受以下版本：

- 文件：`HZK16F`
- 大小：267,776 字节
- SHA256：`e94400a4ac1a80f8681169324d45d39b360c7260d3157876500812c81010642b`

该文件以传统 GB 槽位存放繁体字形。将所有槽位按简体 GB2312 字符直接解码为 Unicode，会把部分繁体形挂到简体码位上。本方法不做这种转换，也不使用自动简繁转换推断全库映射。原仓库工具代码的 GPL-3.0 不自动解决历史字模的使用与再分发授权。

## 导出

需要 Python 3.9+，仅使用标准库。将输入与输出留在被忽略的 `local-research/`；不要提交或发布完整字库。以下命令在仓库根目录执行：

```sh
mkdir -p local-research/source-slots

python3 scripts/source_slots_to_bdf.py --kind hzk16f \
  --input local-research/source-slots/HZK16F \
  --output local-research/source-slots/hzk16f-slots.bdf

python3 scripts/source_slots_to_bdf.py --kind sony-g90 \
  --input local-research/source-slots/Tg1f0110.mot \
  --output local-research/source-slots/sony-g90-foreground-slots.bdf

python3 scripts/source_slots_to_bdf.py --kind sony-g90 --sony-view raw \
  --input local-research/source-slots/Tg1f0110.mot \
  --output local-research/source-slots/sony-g90-raw-pattern-slots.bdf
```

脚本首先校验输入大小和 SHA256。Sony 还校验每条 S-record 的计数、校验和、地址范围、重复地址，以及解码缓冲区的 SHA256。没有“忽略摘要”选项；遇到版本不符应核对来源，不能硬套。

成功后终端输出 JSON，包括输入与 BDF 的 SHA256、槽位总数、空槽数、尺寸和 Sony 视图类型。目标文件必须不存在；已有文件或符号链接都会拒绝覆盖。再次导出请选新文件名。输出目录须事先存在。

## Sony 的两种视图与限制

S-record 数据放入 512 KiB 的零初始化缓冲区；未记录的地址保持零。该缓冲区 SHA256 为 `def4df180acbd6f1c5c1b6886500e6c5cf9ed5cbee4cd34d7d4687be9a2faef7`。

槽位 `i` 的起点为 `(i >> 7) × 0x4000 + (i & 127) × 32`。每行读取起点加行号、加 `0x1000`、加 `0x2000` 的三个字节，字节内高位在左，得到 24 位。

- `raw`：直接保留这 24 个编码图案位。它是原始存储视图，**不等于屏幕上的实体笔画**。
- `foreground`，默认：每个像素取“当前编码位 AND 左侧前一编码位”，独立字框左邻居设为零。该规则来自同系 MB90092 的 pattern-background-1 资料，应用于 G90 是推断，未经 G90 实机独立核验。真实设备相邻字符可能影响边界；导出的前景也不包含背景／描边信息。

两种视图都不裁掉 24×32 字框的空边，不放大，不加入曾手补的六个汉字，不声称已有完整字符映射。本站已人工核对过少量菜单字形，但此脚本统一使用源槽位，连这些少量字符也不混入 Unicode 编码。

每组第四个 `0x1000` 字节银行不在上述 24 位字模布局内，原缓冲区这些区域仍有 113 个非零字节。它们不进入 BDF。因此即使导出 `raw`，也只能往返核对字模银行，**不能把 BDF 当成完整固件备份或可回写设备的镜像**。`foreground` 还会丢失原编码的背景／描边信息，不能反推原始图案位。

## 基线、字宽与使用方式

原二进制数据没有可直接沿用的桌面字体基线与排版度量。BDF 使用透明的容器约定：`BBX 宽 高 0 0`、`FONT_ASCENT=高`、`FONT_DESCENT=0`、`DWIDTH=宽`，即完整字框置于基线上方。这不是对原硬件基线的考证；点阵行序和空边不变。Sony 字框为 24×32，HZK16F 为 16×16。

用支持自定义编码 BDF 的查看器按槽位浏览，或由程序按 `ENCODING` 的源索引选取字形。不要按 Unicode 文本直接排字，不要将注册名改成 `ISO10646`，也不要给本站 `render-bdf --encoding unicode` 当作 Unicode 字库使用。普通桌面字体菜单未必支持该格式；本方法不承诺生成可直接安装的 TTF。

实测 FreeType 可打开三种输出，但不会自动选择这个自定义字符映射。调用方需先用 `FT_Set_Charmap` 选择文件的唯一 charmap，再用源槽号查询字形；不能把没有默认 Unicode charmap 误判为没有字模。已逐一验证全部源槽号可寻址，FreeType 额外增加的 `.notdef` 不计入源槽总数。

## 验证

默认测试不需要私有字库，使用合成字模验证每个槽位、位序、三个银行、左邻居规则、空槽保留、拒绝覆盖和输入检查：

```sh
python3 tests/source-slots-export.test.py
```

持有正确输入时，再开启全库往返测试：

```sh
SOURCE_SLOT_SONY_INPUT=local-research/source-slots/Tg1f0110.mot \
SOURCE_SLOT_HZK16F_INPUT=local-research/source-slots/HZK16F \
python3 tests/source-slots-export.test.py
```

测试独立解析生成的 BDF，不仅核对声明的 `CHARS`：HZK16F 将所有行拼回后逐字节比较完整输入；Sony 原图案视图比较所有字模银行，前景视图与逐像素独立参考实现比较全部槽位。缺少私有输入时，对应两项实测会显示跳过；合成测试通过不等于真实版本已经测试，也不构成硬件验证或字义映射验证。

2026-11-05 使用上述正确输入实测：14 项测试全部通过；未提供输入时为 12 项通过、2 项跳过。Sony 两种视图均有 1,336 个空槽，HZK16F 有 388 个空槽，全部保留。

另对当前固定样图作独立像素核对：Sony 样文的 10 个非空字符使用已有核对表选源槽，重绘后整张 RGBA 一致；HZK16F 两行的 36 个非空字格以图案反查源槽，重绘后整张 RGBA 一致，保留同像素的所有候选槽。此项只证明这些固定样图的源像素一致，**不把反查候选当作 Unicode 字符映射，也不代替全库往返或实机验证**。
