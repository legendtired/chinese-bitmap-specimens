# 内嵌点阵与 Unicode PCF：导出为 BDF

[返回获取与导出方法](font-export.md)

使用 [bitmap_strike_to_bdf.py](../scripts/bitmap_strike_to_bdf.py) 读取字体中已保存的黑白位图。它不把矢量轮廓取模、不补字、不缩放。输入须自行取得并确认允许转换；本站不附带原字体或导出后的完整字库。

## 准备

需要 Python 3 和 `freetype-py 2.5.1`。下载本仓库后，在仓库目录打开终端：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install freetype-py==2.5.1
```

下列命令使用该虚拟环境。Windows 用 `py -m venv .venv` 创建环境，将 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。输入文件名含空格时加引号；输出选新文件名。

## 先看有哪些尺寸

```sh
.venv/bin/python scripts/bitmap_strike_to_bdf.py fireflysung.ttf --list
```

输出列出 `face`（字体集合中的字面）、`strike`（位图层编号）、`ppemX` 和 `ppemY`。只有列出的尺寸可导出。`reportedHeight` 是字体报告的高度，不能直接当作汉字设计高度或 ppem。

## 导出

```sh
.venv/bin/python scripts/bitmap_strike_to_bdf.py fireflysung.ttf firefly12.bdf --ppem 12
.venv/bin/python scripts/bitmap_strike_to_bdf.py Hei.ttf hei12.bdf --ppem 12
.venv/bin/python scripts/bitmap_strike_to_bdf.py Dotum.ttf dotum12.bdf --ppem 12
.venv/bin/python scripts/bitmap_strike_to_bdf.py wenquanyi_9pt.pcf wenquanyi12.bdf --ppem 12
```

例如本次核验的 MingLiU 7.00 集合，`face 0` 是 MingLiU：

```sh
.venv/bin/python scripts/bitmap_strike_to_bdf.py mingliu.ttc --list
.venv/bin/python scripts/bitmap_strike_to_bdf.py mingliu.ttc mingliu12.bdf --face 0 --ppem 12
```

其他 TTC 先运行 `--list`，按名称确认字面，再显式选 `--face`；同名字体不同版本不保证含相同位图层。若同一 ppem 有多个层，使用列表中的 `--strike` 编号代替 `--ppem`。

只导出选定字符时，可追加 `--text "视野无限广，窗外有蓝天。"`。缺字列在结果的 `unavailable` 中，不借用其他字号或字体补齐。未指定 `--text` 时导出该层可映射的 Unicode 显示字符，控制字符不导出。

## 能保留什么

- 原黑白像素、每字字宽、左右 bearing 和相对基线位置。
- 字体自带的 Unicode 字符映射。输出 BDF 的 `ENCODING` 是 Unicode。
- 输入 SHA256、字面及位图层编号写入 BDF 注释；终端列出导出数与缺字数。

全局 `FONTBOUNDINGBOX` 与行高按本次导出字形的实际范围和位图层指标确定，可能大于汉字字高。它保留每字相对基线的位置，不保证不同软件的整行排版完全相同。

无位图、选错尺寸、非 Unicode 字符映射或灰阶／彩色位图会报错。不能将此脚本用于原始 ROM、HZK、Palm PDB、CJF、HBF 配套 BIN，也不能将字体轮廓上的正交格点当作内嵌位图。已有输出文件不会覆盖。

## 本次验证范围

已对下列实际来源全层导出，并将目录中的汉字行与西文行逐像素比对，均一致：

- Firefly 1.3.0：11、12、13、14、15、16px。12–15px 部分字符只有轮廓而无该尺寸位图，脚本正确留缺。
- Apple Hei：9、12、16、24px。
- Google Fonts 仓库 `sources/ttf/Dotum.ttf`：12、14、16px。不要换成仅含轮廓的 hinted/unhinted 版本。
- 文泉驿 `wenquanyi_9pt.pcf`：12px。
- MingLiU 7.00 TTC 的 face 0：11、12、13、15、16、20px，各导出28,705个显示字符，204个仅有其他层的字符留缺。

其他含内嵌点阵的字体可以先 `--list` 检查，但这不表示所有文件版本都已经核验；导出后仍应核对字形、编码及许可。普通矢量字体、截图重建样张和未验证设备格式不在保证范围内。

测试输入 SHA256：

```text
fireflysung.ttf     06b1af510de7a396b694b8c2ac0d71a6d1dc1b35c66409c7d8070a7b3515ad56
Hei.ttf            644a6e45387d8a8e22d1f4ecb3bc7bf80a4b6df49e444a5df5f4d973173a50b1
Dotum.ttf          58e69081efb630ad936dd398c20191f0b7ca2f91b1a2e4f310f5efc173ee6d60
wenquanyi_9pt.pcf   923c0836c9ae367ce422717c851a5fc7ba2326438f4fa88740e4105cfdfbe22f
mingliu.ttc        b642c3b47249c14b6e35866833e298069f9e5d76a0870bb18d9aaa4f5c774c28
```

来源：[Firefly](https://github.com/rougier/freetype-gl/blob/master/fonts/fireflysung.ttf)、[Apple Hei 镜像](https://github.com/justrajdeep/fonts/blob/master/Hei.ttf)、[Dotum](https://github.com/googlefonts/gulim/blob/main/sources/ttf/Dotum.ttf)、[文泉驿 PCF](https://github.com/AmusementClub/WenQuanYi-Bitmap-Song-TTF/tree/master/Original%20Fonts)、[MingLiU 镜像](https://github.com/grubeninspekteur/webseitendesigner-pywright/blob/master/fonts/mingliu.ttc)。镜像可访问不等于允许转换或再分发。
