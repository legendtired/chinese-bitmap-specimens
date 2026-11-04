# Casio Ex-word XD-A10000：获取与提取

12×12与24×24已列为推荐。推荐表示字样欣赏与研究价值，不代表可免费商用或再分发。

## 三步获取

1. 打开 [来源文件夹](https://github.com/dictdump/dictdump/tree/main/nor-and-nand/CY102-XD-A10000/nand/extracted-nand-files-from-device/CY102D0C-extracted/font)，按需要选择 china12z.cjf 或 china24z.cjf。在 GitHub 文件页选择 Download raw file 保存原始文件，不要把网页另存为CJF。请自行确认有权取得和使用输入。
2. 打开 [cjf_to_bdf.py 脚本](../scripts/cjf_to_bdf.py)，保存到同一文件夹。需要 Python 3，无第三方依赖，不联网、不内嵌字形。
3. 在该文件夹运行下面一条命令，文件名按尺寸替换：

```sh
python3 cjf_to_bdf.py china12z.cjf casio12.bdf
python3 cjf_to_bdf.py china24z.cjf casio24.bdf
```

Windows 可将 python3 改为 py。脚本只接受核验过的文件SHA256，拒绝猜测格式和覆盖已有输出。若报 Unknown input，先确认保存的是原始文件而非HTML；不要绕过校验。输出路径已存在时，选择另一个文件名。

输出 BDF 是位图字体交换格式，不是可直接双击安装的TTF。需使用支持BDF的软件。开发者也可用本仓库 scripts/render_bdf.py 查看；它保留原像素、没有矢量取模或其他字体补字。转换不带来字体授权。

## 来源与核验边界

来源是 dictdump 第三方设备保存项目，目录标为 XD-A10000 的 NAND 提取文件。我们未独立认证原机、转储过程和修改历史。型号属于约2010年的电子辞典，不等于字形创作年代，也没有广播电视字库来源证据。原始作者、商用和再分发授权未明确。本站不提供完整CJF、ROM或BDF下载，只展示固定样句与无字模脚本。

文件均为256字节头加23940个定长双字节编码单元；不是23940个汉字，也不是完整四字节GB18030。Unicode映射按当前Python GB18030编码器；少数非GB2312位置可能因标准修订不同，未逐码实机认证。

- china12z.cjf：574816字节；SHA256 0d83d8a638d1329c1b1a28bc2568c05594721eeeed012efa2f1bea0ab595d65b。
- china16z.cjf：766336字节；SHA256 c9036da87827b2d3fc21d51586b383f2e6aed0987038dd2d66e7f78dfee2c5a2。
- china24z.cjf：1723936字节；SHA256 5daf1780bb0ff1e68989736d1f3858e215436c2e232f7ab13063adae07d9e2a1。

## 为什么没有新增16点条目

16点与现有NISC条目高度重合：GB2312的6763个汉字中6719个一致、44个不同。因此只保留获取和版本线索，不冒充独立新字体；脚本仍可转换核验过的china16z.cjf。

12点与所查NC1020/HZK12的6763汉字仅9/2个一致。12/24点在当前同尺寸样句筛查中均无完整匹配；这是有限比对，不是全球唯一性或作者归属证明。像素一致不能推断复制方向。
