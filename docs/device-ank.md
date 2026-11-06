# Sharp／FM Towns 原生英数补充

现有固定样图已展示英文数字。现在可另行导出原机ANK，并与现有汉字结果合并；旧导出器仍保持原范围。

- Sharp X68000：8×16英数，合并16×16 JIS字形，共6972字。
- FM Towns F20：10×20英数，合并20×20汉字，共6450字。
- 每套ANK有95字，含数字、大小写英文字母和空格。原槽5C为日元符号U+00A5，7E为上划线U+203E；不能当成反斜线或波浪线。因此普通ASCII覆盖93字，不补画缺字。

使用与原导出器相同且经SHA-256验证的ROM：

```sh
python3 scripts/device_ank_to_bdf.py --device sharp --rom local-research/cgrom.dat --output local-research/sharp-with-ank
python3 scripts/device_ank_to_bdf.py --device fmtowns --rom local-research/FMT_F20.ROM --output local-research/fmtowns-with-ank
```

每次输出独立ANK、合并BDF和校验报告。输出目录必须不存在；保留原像素、原字宽，不借字。基线统一在字框底部，是导出约定，不代表已恢复原机排版。未纳入半角假名或未核定控制码。

来源与ROM取得方法：[Sharp](sharp-x68000.md)、[FM Towns](fmtowns-f20.md)。公开仓库只含脚本，不含ROM或完整导出字库。
