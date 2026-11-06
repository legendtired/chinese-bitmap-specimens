# Palm 细明与系统西文配套

保留 CJKOS 繁体细明 12×12 的原中文样字，另配 **Palm m515 / Palm OS 4.1 的系统 stdFont**，补入 U+0020–U+007E 共95个可打印ASCII。英文、数字和标点均直接读取原位图，不借用相似字体，也不等宽化。

这是兼容同一Palm系统的字体搭配，不是细明PDB自带ASCII，也不声称是12点细明唯一原配或原机混排复刻。其他Palm条目本次不变。

## 来源与证据

- 中文来自 [CJKOS历史归档](https://palmdb.net/app/cjkos) 的 `cjkFntEx.zip` → `FontExt/FB512XMF.PDB`，原导出方法见 [CJKOS FBLK](cjkos-export.md)。
- 西文来自 [Palm设备ROM资料页](https://palmdb.net/app/palm-roms-complete) 的 `Palm-m515-4.1-en.rom`。先确认自己有权处理该来源。
- CJKOS4.27随包手册明确列出m515中文界面支持；[开发商介绍](https://www.njstar.com/cms/cjk-os-for-palm)说明CJKOS是在英文Palm OS上提供中日韩支持。
- [Palm OS字体规范](https://palm.wiki/development/docs/601/PalmOSReference/Font.html)定义 `stdFont` 为fontID 0。该ROM的 `Latin Locale Module` 数据库中，`fnti/32000` 将fontID 0映射到 `NFNT/32000`。
- ROM SHA-1与 [MAME的m515记录](https://github.com/mamedev/mame/blob/master/src/mame/palm/palm.cpp)一致。
- CJKOS4.27官方手册第10页的混排示例中，英文短语的80×11像素与本次stdFont完全相同；同处中文为10点，不能把它作为12点细明原机基线的证据。

校验值：

- ROM SHA-1：`a0767ea26cc493a3f687525d173903fef89f1acb`
- ROM SHA-256：`47bb591f77390eae3b94669e1cb77ac8f8f5acced3d1cff35acd1ae205248f20`
- NFNT/32000 SHA-256：`1070e21fcb60a4b58f456364af8917ce8d9508c1f88f9894f9aec62b050d790a`
- 细明PDB SHA-256：`a8de69c5cf30d53a3433c63c1fea1f02a54f21e380ebfe1d312514a51eabf091`

## 本地导出

Python 3.9以上，无第三方依赖。输出目录必须尚不存在；输入不匹配上述SHA时拒绝处理。脚本只读取二进制，不执行或刷写固件。

```sh
python3 scripts/palm_system_latin_to_bdf.py \
  --rom local-research/palm/Palm-m515-4.1-en.rom \
  --cjkos local-research/palm/FB512XMF.PDB \
  --output local-research/palm/ximing-system-latin
```

输出：

- `palm-m515-std-ascii.bdf`：95个ASCII，保留原11px字框、比例字进及9px ascent／2px descent。
- `cjkos-ximing-original.bdf`：调用原CJKOS解析器导出的13973个源槽位，保持原映射与全部未编码槽位。
- `cjkos-ximing-m515-std-combined.bdf`：仅追加95个ASCII，共14068个槽位，其中13801个获得Unicode编码。每个原中文glyph块、bitmap、字进、bearing和编码保持不变。
- `report.json`：输入与输出校验值、资源定位、映射数量及排版边界。

## 排版边界

中文BDF原有字符框底部基线约定、12px ascent／0px descent、12px字进全部保留，不改成Palm系统度量。组合中11px西文字框按底部对齐至12px中文行框，原像素与比例字进不变；这是导出排版约定。

固定预览保留原来的156×12中文行，逐像素未改；下面新增英数行。中文仍留原1px字间距，英数按系统原字进排列。两个字库的大小没有归一化、拉伸或补画。

已验证95个ASCII与源NFNT逐像素一致；组合前后全部13973个中文glyph块一致，完整BDF回读和固定预览检查通过。原机实际选择的fontID、CJKOS开关及12点混排基线未运行核验。

## 公开与许可

CJKOS与Palm系统字体的独立再分发授权均未确认。公开归档可取得不等于获得授权。本仓库仅提供固定样图、方法和不含字模数据的解析脚本；完整ROM、PDB、BDF及字模数组留在本地，不随网站或GitHub发布。
