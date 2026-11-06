# Palm CJKOS FBLK → BDF

适用范围：本站简／繁体10点与12点四项。脚本只读取PDB，不运行Palm程序。需要Python 3.9以上，无第三方依赖。

## 取得正确版本

从 [PalmDB 的 CJKOS 页面](https://palmdb.net/app/cjkos) 取得历史包 `CJKOS.zip`。在其中打开 `CJKOS/cjkos_os5.zip`，取出：

- `Font/FGB10F.PDB`：简体10点。
- `Font/FGB12F.PDB`：简体12点。
- `Font/FB510F.PDB`：繁体10点。
- `Font/FB512F.PDB`：繁体12点。

同包的 `cjkos_TW.zip`、`cjkos_os4.zip` 也包含与本站记录SHA-256相同的这四个文件。

**不要用 `cjkos401.zip` 的简体两个文件替代本站版本。** 它们的SHA不同，12点字模内容也大量不同。繁体两个在这些包内一致。脚本也识别401版的两个旧简体文件，但报告会标记 `catalog_source_match: false`。

与本站四项对应的SHA-256：

- FGB10F：`2f2db52b735589ee627b2c9ccd4d73bca2ae1cded7ccf14c377423c54a112cef`
- FGB12F：`c02b4e383ddd08b146fef4f853d55bd6492ceb546cf687fcdf4491837bbcdc8c`
- FB510F：`3ca7a7aa0e595638044337a78f16bc0c194e08d1a30ef13d70212f86c7be83a7`
- FB512F：`e913c4c3f91cf2852747500f5c516a5f6ef1852df66493e4cc289f2656e15882`

未知SHA会拒绝导出，避免将其他CJKOS字号、精简版或压缩布局误读。

## 导出

输出BDF与JSON报告必须是两个不同的新文件，父目录须已存在。脚本拒绝覆盖已有文件、目录、悬空链接或输入源文件，也拒绝output/report指向同一解析路径；写入使用独占创建。重新导出请选择新的文件名。可用 `--report 路径` 指定独立报告位置。

```sh
python3 scripts/cjkos_to_bdf.py local-research/cjkos/Font/FGB10F.PDB local-research/FGB10F.bdf
python3 scripts/cjkos_to_bdf.py local-research/cjkos/Font/FGB12F.PDB local-research/FGB12F.bdf
python3 scripts/cjkos_to_bdf.py local-research/cjkos/Font/FB510F.PDB local-research/FB510F.bdf
python3 scripts/cjkos_to_bdf.py local-research/cjkos/Font/FB512F.PDB local-research/FB512F.bdf
```

默认输出Unicode BDF，并在同目录写出 `.bdf.json` 报告。所有物理槽位都会保留。Python标准库 `gb2312`／`big5` 能严格解码并回编码到同一原码位的字形获得Unicode编码；未定义位置和非规范重复映射保留为 `ENCODING -1`，原码位记录在 `STARTCHAR source-XXXX` 及报告中，不猜Unicode、不偷偷丢槽。

原编码研究输出可加 `--encoding source`。它将PDB原双字节码（GB从A1A1、Big5从A140开始）写入ENCODING，使用自定义 `CJKOSGB`／`CJKOSBIG5` 注册名，不冒充Unicode或常见X11的GB 2121编码。通用软件可能不能直接将这些码位映射成文本。

## 布局与限制

- PDB使用资源表，类型/创建者为 `dFnt`／`dCJK`，资源类型 `FBLK`，依资源ID排列，每个完整资源2048字。
- GB范围A1–F7×A1–FE，共8178槽。Big5范围A1–F9×40–7E、A1–FE，共13973槽。
- 12点每字18字节，连续、行优先、MSB在左，每行12位。
- 10点每字13字节：前10字节分别存各行左8点，后3字节从高位开始依次存10行右2点，末4位为填充。
- 字框和advance为10或12，保留所有空边。源文件没有逐字baseline/bearing记录，BDF将基线明确约定在字符框底部。
- 不含普通ASCII，不从Palm系统字体或其他字库补字。
- 这不是普通Palm NFNT字体。monobit 0.48的Palm读取器及Bits'N'Picas的NFNT支持不能直接替代FBLK解析。

2026-11-05验证：四个完整字体所有槽位经monobit 0.48读回后，原像素、advance、bearing和数值编码一致；四项各12字样句的像素掩码与现有PNG差异为0。完整映射与例外数量见导出JSON。普通Unicode名称与原字模身份的全面人工核验不在此测试范围。

CJKOS是历史共享软件；来源包可取得不等于独立字体获准再分发。BDF仍受原权利限制。本仓库只提供解析脚本与固定样图，不附PDB或完整导出字库。

## 扩展12点样式

同一历史包的 `CJKOS/cjkFntEx.zip` 中，`FontExt/` 提供以下四款，均可用上述脚本导出：

- `FGB12KTF.PDB`：简体楷体；SHA-256 `5877cc54d8a4cce49629a40e4c29e8c45908799d35f8dfa94ed667a0777ba77a`。
- `FGB12FSF.PDB`：简体仿宋；SHA-256 `f630ebdea98ae72e28d7179b64cb97bde13f39eb65b66bed2c7bf6209897d4de`。
- `FB512KBF.PDB`：繁体标楷；SHA-256 `20cb494bf5aa0beb70faa1e2cc68b7d8b1fd9efc0a54e9b9f53bb5129a2ca135`。
- `FB512XMF.PDB`：繁体细明；SHA-256 `a8de69c5cf30d53a3433c63c1fea1f02a54f21e380ebfe1d312514a51eabf091`。

简体各6763个、繁体各13061个非空汉字。包内文件日期为1999年，不等于已证实首次发行年或手工制作历史。扩展宋体FGB12STF与HZK12全6763汉字重复，不另收录。

四款与普通Palm12、HZK12、Apple Kai/BiauKai/LiSung及MingLiU逐字比较非重复；其余同高度条目仅做固定样字排查，不宣称全字库相似率已核验。
