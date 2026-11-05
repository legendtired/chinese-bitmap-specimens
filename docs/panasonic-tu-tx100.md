# Panasonic TU-TX100 文字放送字样

- 16×24存储框，主要墨迹约15×18；3488个Unicode映射字符，含2966汉字。
- 来自 [Teletext Rescue](https://github.com/AssunaYuuki/teletext_rescue) 的位图表。作者标称TU-TX100来源，尚未独立核验原机ROM。
- 与FS-UV1共同2966汉字逐点不同；另34份已收录字库未发现整套重复。不是完整繁体字库，固定样句缺「廣」「窗」。

## 本地导出

自行取得并确认有权使用上游版本 `31c84f7a57187f9110c4e843a374cc26209b9601` 的 `cpp/src/jtes_fonts.inc`。

```sh
python3 scripts/tu_tx100_to_bdf.py /path/to/jtes_fonts.inc /path/to/tu-tx100.bdf
```

脚本校验SHA256，直接使用上游JIS→Unicode表，保留16×24原像素。输出3488字符；不含半角、小字或未映射外字。不联网，不覆盖已有文件。

上游程序GPL许可不等于字体再分发授权。本站只提供固定样图、来源和不含字模的导出脚本，完整BDF留在本地。
