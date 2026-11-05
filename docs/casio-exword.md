# Casio Ex-word XD-A10000：获取与提取

已收录12点和24点字样，12点列为推荐。

## 获取

1. 打开[来源文件夹](https://github.com/dictdump/dictdump/tree/main/nor-and-nand/CY102-XD-A10000/nand/extracted-nand-files-from-device/CY102D0C-extracted/font)，选择 `china12z.cjf` 或 `china24z.cjf`，点击 GitHub 文件页的 Download raw file。
2. 将 [cjf_to_bdf.py](../scripts/cjf_to_bdf.py) 保存到同一文件夹。
3. 安装 Python 3，按所选尺寸运行：

```sh
python3 cjf_to_bdf.py china12z.cjf casio12.bdf
python3 cjf_to_bdf.py china24z.cjf casio24.bdf
```

Windows 可将 `python3` 改为 `py`。输出用支持 BDF 的软件打开。脚本无第三方依赖，会检查文件校验值；报 `Unknown input` 时确认下载的是 CJF 而非网页，输出已存在时换一个文件名。

## 文件资料

来源为 dictdump 保存的 XD-A10000 NAND 提取文件，设备约2010年。原机和转储过程未独立核验，字模许可待核实。

每个文件含256字节头和23,940个双字节编码单元，按 Python GB18030 编码器映射 Unicode；非 GB2312 区可能存在标准版本差异。

- 12点：574,816字节；SHA256 `0d83d8a638d1329c1b1a28bc2568c05594721eeeed012efa2f1bea0ab595d65b`。
- 16点：766,336字节；SHA256 `c9036da87827b2d3fc21d51586b383f2e6aed0987038dd2d66e7f78dfee2c5a2`。
- 24点：1,723,936字节；SHA256 `5daf1780bb0ff1e68989736d1f3858e215436c2e232f7ab13063adae07d9e2a1`。

## 比对

16点与 NISC 的6,763个 GB2312 汉字中，6,719个一致、44个不同，作为版本线索保留；脚本也支持该文件。12点与 NC1020／HZK12 同范围比对分别有9／2字一致。12／24点在现有同尺寸样句中均无整组匹配。
