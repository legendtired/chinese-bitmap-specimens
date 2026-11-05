# FlipperCN 20240803 字模导出

适用目录条目：`flippercn_20240803_ui`。导出器只处理已核验的 **20240803 测试版固件包**，输出 Unicode BDF。它保留固件内 U8g2 字模的原始像素、码位、左右留白、基线偏移和前进宽，不执行固件，不连接设备，也不补字。

脚本不附带固件或字模，需要自行取得有权使用的来源文件。来源仓库标注 GPL-3.0，但未发现独立字库许可；技术上能够导出不等于已经取得再次分发字库的许可。网站不提供导出的完整 BDF。

## 取得准确来源

从[20240803 固件文件浏览页](https://github.com/ZhaiRenGaiZaoJia/FlipperZero-CN-Firmware/blob/main/mntm_cn-20240803%E5%85%AC%E6%B5%8B%E7%89%88/mntm_cn-20240803Test.tgz)取得 `mntm_cn-20240803Test.tgz`，放入本地 `local-research/`。无需刷入设备，也无需手动解包。

只接受下面的文件：

- 压缩包：10,027,673 字节。
- 压缩包 SHA-256：`e31b30ee7cbcc10ceae67d3533ae3a999d1ad3420ed0e38c93dd8b18b644b6a4`。
- 这个 SHA 是**整个 TGZ**的指纹，不是单独字模的指纹。

其他日期、重新打包或修改过的文件会被拒绝。不同版本的字模位置不能直接套用，脚本没有跳过校验的选项。

## 本地操作

需要 Python 3.9 或更新版本；导出只用 Python 标准库，不需要第三方包或联网。

先检查来源和覆盖信息，不写出字库：

```sh
python3 scripts/flippercn_to_bdf.py local-research/mntm_cn-20240803Test.tgz --inspect
```

导出 BDF 和不含位图行的核验报告：

```sh
python3 scripts/flippercn_to_bdf.py \
  local-research/mntm_cn-20240803Test.tgz \
  local-research/flippercn-20240803.bdf \
  --report local-research/flippercn-20240803.json
```

输出目录必须已存在。脚本不会覆盖已有文件；重跑时请使用新文件名。BDF 是点阵交换格式，适合本地核验和支持 BDF 的工具，不应把这一步称为生成可在所有桌面系统直接安装的 TTF/OTF。

若使用本仓库的 BDF 渲染入口，可以检查实际存在的字：

```sh
python3 scripts/render_bdf.py \
  --font local-research/flippercn-20240803.bdf \
  --encoding unicode --text '设置 显示 输入 返回 确认 菜单' \
  --output local-research/flippercn-check.png
```

渲染入口需要 Pillow。它按 BDF 指标重新排版，行距和墨色不保证与网站固定样图完全相同；字形像素不做平滑或替换。固件、完整 BDF 和其他完整字模输出应留在本地研究目录，不加入公开发布包。

## 输出范围与指标

- 共 **604 码位**：503 个汉字、95 个可打印 ASCII 码位（包括空格）和 6 个中文引号／标点。编码直接取自 U8g2 记录，不使用猜测的 GB 编码映射。
- 这是设备菜单子集，缺少“野”“天”等常用字。导出不会变成完整中文字库。
- 484 个汉字是 9×9 字形框；“位、某、波、脚、默”高 10 像素。其他字也有更窄或更矮的原生边界，不强制扩成同一字符位图。
- 汉字通常前进 10 像素，但“足”前进 9 像素，左 bearing 为 −1；“选”前进 11 像素。ASCII 保持各自的宽度，空格前进 1 像素。
- 原字体全局边界为 `10 11 -1 -2`，即宽 10、高 11、左偏移 −1、下偏移 −2。单字位图最大宽度为 9；全局框与单字位图宽度不是同一指标。
- BDF 保留每个字的原始 `BBX` 和 `DWIDTH`。`SIZE 11 72 72` 是按全局像素高选择的 BDF 导出约定，不是对原作者字号定义的重新认定。

## 解析与核验依据

原字体位于包内 `f7-update-mntm-release-186bc960/firmware.dfu`：

- DFU 文件：853,165 字节，SHA-256 为 `07ad42d9119ca653650a83c2e02dfecc369fd5742880a19012bcba52df3c7129`。
- 字模开始于**整个 DFU 文件**的 `0xCB1C4` 偏移，长度 11,801 字节。这不是设备闪存地址。
- 字模 SHA-256：`15a85edd16380fef4991a1b3efd4fc85c51bc6bea8547cf51fdde2c9a9a4791d`。

算法依据是 [U8g2 官方字体解码器](https://github.com/olikraus/u8g2/blob/master/csrc/u8g2_font.c)：23 字节头、8 位码位区、Unicode 索引与记录区，以及 LSB-first RLE。脚本独立实现解析，并检查记录边界、码位顺序、Unicode 索引、RLE 长度和全局字形范围。

已对这份来源完成以下验证：

1. TGZ、DFU、嵌入字模三层 SHA-256 符合预期。
2. 604 字形全部成功解码，并经 BDF 写出／重新读取逐字核对，码位、像素、bearing 和 advance 全部一致。
3. 用导出的 BDF 重建原网站三行样文，137×41 图像与固定样图逐像素 RGBA 完全一致。
4. 同尺寸但内容改动的来源被拒绝；已有输出不会被覆盖；截断、越界和不前进的 RLE 均被拒绝。

## 测试方法

无私有来源时运行合成数据测试：

```sh
python3 tests/flipper-export.test.py
```

完整来源检查需要自行提供 TGZ。若也指定现有样图并安装 Pillow，会附加整张图像的像素一致性检查：

```sh
FLIPPERCN_TGZ=local-research/mntm_cn-20240803Test.tgz \
FLIPPERCN_SPECIMEN=assets/specimens/flippercn_20240803_ui.png \
python3 tests/flipper-export.test.py
```

未提供来源时，依赖来源的测试会明确显示跳过，不能把它称为完整来源验证通过。测试文件不携带原始字模数据。
