# Psion 中文 + Arial

用户选择的同系统搭配。中文来自 Unicode.gdr，英文数字来自同一 ROM 的 Eon.gdr Arial；不声称是唯一原配。保留原像素、可变字宽与度量。

取得有权处理的 Revo v1.08(14) chitr ROM 后：

```
python scripts/psion_arial_to_bdf.py ROM.bin --size 8 --output psion8-arial.bdf
python scripts/psion_arial_to_bdf.py ROM.bin --size 11 --output psion11-arial.bdf
```

脚本校验完整 ROM 及两份 GDR 的 SHA256，不联网，不执行固件，不覆盖已有输出。新增95个可打印ASCII字符（含空格），不替换原中文或标点。

ROM、GDR及完整BDF不随公开仓库分发；公开候选仅脚本、说明和固定样图。
