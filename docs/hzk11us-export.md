# HZK11US：仅汉字的本地 BDF 导出

此方法只支持 tomzbj 的 **HZK11US Unicode 重排版**，导出其中 6763 个汉字的原始 11×11 点阵。不适用于其他同名字库，也不把它当作按 GB2312 区位排列的普通 HZK 文件。

源库的部分符号、假名和 ASCII 对应关系未可靠核定。脚本**排除全部非汉字记录**，包括有像素的记录，不猜测、不重新分配编码，不从其他字体补字。这是汉字子集 BDF，不是“完整 Unicode 字库”。

## 来源与核验版本

- [来源项目与作者说明](https://github.com/tomzbj/unicode_hzk_smlib_gen)。在项目根目录自行取得 `HZK11US`，保留原文件。
- [源文件浏览页](https://github.com/tomzbj/unicode_hzk_smlib_gen/blob/HEAD/HZK11US)。大小必须为 **163790 字节**，共 7445 条记录。
- SHA-256：`9caa46ecd8371415edd34b4eb7cd8645ffc93e562590b99932d67cf2cffc1f43`。
- Git blob：`30227a3aeb1ab5814f2fb67e0de8e1d6e0950123`。
- 作者 [gen_smlib.py](https://github.com/tomzbj/unicode_hzk_smlib_gen/blob/HEAD/gen_smlib.py) 的 `unicode_tab` 已逐项核对，与 Python 严格 GB2312 双字节映射得到的 7445 个 Unicode 码位排序后完全相同。映射脚本的 Git blob 为 `3231bd7f9e3b16e254a5e36fe9721f7b0fa61ca6`。

脚本重建并检查映射指纹，不附带作者的码表或字模，不执行作者脚本，也不联网下载。文件名可以不同，但大小与 SHA-256 必须全部符合；未知版本会被拒绝。

## 转换步骤

需要 Python 3.9 或更新版本，仅使用标准库。将自行取得的原文件放在本地研究目录：

```sh
mkdir -p local-research/hzk11us local-research/generated
python3 scripts/hzk11us_to_bdf.py --list
python3 scripts/hzk11us_to_bdf.py \
  --input local-research/hzk11us/HZK11US \
  --output local-research/generated/hzk11us-han.bdf
```

输出为 BDF 与同名 `.bdf.json` 报告。也可用 `--report 新路径.json` 指定报告路径。两个输出都拒绝覆盖已有文件或符号链接，不能指向输入文件；需要重跑时请使用新的输出名称。

生成的 BDF 可用支持此格式的点阵工具打开；它不是可直接安装到所有系统的 TTF。可用本站渲染入口核对：

```sh
python3 -m pip install Pillow
python3 scripts/workspace.py render-bdf \
  --font local-research/generated/hzk11us-han.bdf \
  --encoding unicode --text "视野无限广，窗外有蓝天。" \
  --output local-research/generated/hzk11us-check.png
```

样文中的逗号和句号不在导出范围，缺字报告应保留这两项。渲染布局由渲染器决定，不能为了补齐标点而使用源库的错映记录。

## 保留什么、排除什么

- 每条记录 22 字节，11 行，每行 2 字节，逐行自上而下、每行高位在左。每行右侧的 5 个填充位必须为零。
- 先重建完整的 Unicode 排序索引，再选择 U+4E00–U+9FFF 范围内的 6763 个汉字。实际首尾码位为 U+4E00、U+9FA0，范围内并非每个码位都有字。
- 不裁边距、不移动像素、不缩放或重新栅格化。BDF 的每行仍存原来的 2 字节。
- 余下 682 条非汉字记录全部排除，其中 661 条非空。排除不等于原记录没有像素，也不意味着它们可安全解释为表中所标的字符。
- 不导出标点、假名、字母、全角英数、符号或空格，不生成普通 ASCII 别名。不是原字体全部字符的覆盖报告。
- 原始文件没有可靠的基线信息。导出约定为 `DWIDTH 11 0`、`BBX 11 11 0 0`、ascent 11、descent 0，即**基线位于字框底部**。这是明确的交换格式约定，不是恢复出的原始排版参数。

每次转换在写入前，都会把 BDF 的全部 6763 条位图读回，与对应源记录的 **148786 字节**逐字节比较。JSON 包含源文件与映射身份、排除数量、BDF SHA-256、度量约定和往返校验结果。此检查证明导出记录保留了原字节，不表示被排除的记录也已导出，也不能代替逐字形人工校勘。

## 测试与已验证范围

无需真实字库即可运行合成测试，测试中没有原始字体字模：

```sh
python3 tests/hzk11us-export.test.py
```

自备已核验输入后，可运行真实输入、全量字节往返、命令行拒绝覆盖和固定字样对照：

```sh
HZK11US_TEST_INPUT=local-research/hzk11us/HZK11US \
HZK11US_TEST_MAPPING_SOURCE=local-research/hzk11us/gen_smlib.py \
HZK11US_TEST_SPECIMEN=assets/specimens/tomzbj_hzk11us.png \
python3 tests/hzk11us-export.test.py
```

后两项环境变量可省略，对应检查会明确跳过。只有 PNG 对照测试需要 Pillow。已核验版本通过全部 6763 个汉字的字节往返，网站固定字样中的 10 个汉字像素完全一致，两个标点位置保持透明。没有声称对全部汉字逐字做过人工辨认。

## 使用与发布边界

来源仓库没有明确提供原字模授权。能取得文件、脚本可以转换，都不等于获得使用、修改或再分发许可；历史字模权利仍需另行核实。

本站仅提供处理脚本、说明和固定预览。原始 HZK11US、导出的完整汉字子集 BDF 及其他原字模数据均留在本地研究目录，不随站点或仓库发布。JSON 报告不含字模，可用于记录本地转换结果。
