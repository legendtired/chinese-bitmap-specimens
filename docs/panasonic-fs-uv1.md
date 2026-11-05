# Panasonic FS-UV1 / FS-A1F：获取与导出

16×16 原生字模。默认导出 **2,966 个汉字**的 Unicode BDF：JIS 一级汉字 2,965 字，加符号区的「仝」。字形及空白边距原样保留，不补字、不转矢量。

## 三步导出

1. 自行取得并确认有权使用 `fs-a1f_kanjifont.rom`。可打开 [File-Hunter 的 Panasonic 资料目录](https://download.file-hunter.com/System%20ROMs/machines/panasonic/)，查找该文件。文件名不是核验依据，必须匹配下方大小与 SHA256。
2. 将 [fsuv1_to_bdf.py](../scripts/fsuv1_to_bdf.py) 保存到同一文件夹，安装 Python 3.9 或更新版本。
3. 在该文件夹打开终端，运行：

```sh
python3 fsuv1_to_bdf.py fs-a1f_kanjifont.rom panasonic-fsuv1-han16.bdf
```

Windows 可把 `python3` 改为 `py`。输出可以用支持 BDF 的字体工具打开；BDF 不是供所有系统直接安装的 TTF。脚本只用 Python 标准库，不联网、不附带 ROM 或字模、不覆盖已有文件。

需要字数、空字和输出校验记录时，加 `--report`：

```sh
python3 fsuv1_to_bdf.py fs-a1f_kanjifont.rom panasonic-fsuv1-han16.bdf --report panasonic-fsuv1-report.json
```

两条命令是不同用法示例，不要对同一个已存在的输出重复执行。

## 符号、假名与全角英数

默认仅导出上述汉字。可加 `--include-symbols` 导出按现代 EUC-JP 暂映射的 **3,489 个字符**，其中3,474个非空、15个空字位：

```sh
python3 fsuv1_to_bdf.py fs-a1f_kanjifont.rom panasonic-fsuv1-jis16.bdf --include-symbols
```

此模式用于研究。历史符号区与现代 JIS 并非全部逐字核准；15个空字位保留，不替换。固定预览用到的全角英数与标点已核对，但不代表所有符号都已核验。两种模式均不导出半角 ASCII，也不导出未确认映射的 ROM 槽位。

## 文件核验与来源

- 大小：131,072 字节。
- SHA256：`e4036415638e73d5894d850cab3a40cb63e76afa0391d0ad31321bf2ed61b7d7`。
- [FS-UV1 持有人转储记录](https://www.msx.org/forum/msx-talk/software/list-undumped-msx-software-please-help?page=67)（2026-05-28）称其 JIS 一级汉字 ROM 与 FS-A1F 相同，并公布上述 SHA256。本站核验了所用文件与公布哈希一致，没有独立拆机认证。
- 旧镜像中同名为 FS-UV1 的另一文件有7个字位不同，疑似转储问题，未作为新字体或兼容输入收录。

报 `Input does not match` 时，检查是否保存成网页、下载不完整或取得了另一版本；不要跳过哈希校验。报 `Output already exists` 时，更换输出文件名。未找到原文件时，固定 PNG 不能反向恢复完整字库。

## 格式与边界

每字32字节，依次为左上、右上、左下、右下四个8×8块；块内每行一个字节，最高位在左。JIS区点为一基编号，槽位为 `区×96+点`；第16区起减512。例：16区1点「亜」位于槽1025。输出统一16×16字框和16像素进位，不裁边；以字框底部为基线（上升16、下降0）是导出排版约定，不是从ROM恢复的原厂指标。

- 繁体样句「視野無限廣，窗外有藍天。」缺「廣」「窗」，原位留空。
- 与 jiskan16、JF-Dot-jiskan16s 的2,966个共同汉字，原矩阵及排除空边平移后均无相同字形。目录其他16点条目仅做样本初筛，不能据此声称全库去重。
- 未获得 ROM 或字模的再分发、商用授权；镜像可访问不代表可自由使用。本站只提供固定预览、说明和不内嵌字形的脚本，不提供完整 ROM 或导出的 BDF。

更多格式见[字体获取与导出](font-export.md)。
