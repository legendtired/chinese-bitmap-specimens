# SC_Song 13×13 与外补 Arial

中文来自 `sunfon.ttf` 的原存13×13位图层。英文和数字按用户选择，使用另一来源 `Eon.gdr` 中的 Arial 原生13点位图。两者不是已证实的原装配套，不是同系统提取，也不是设备界面截图。

## 中文来源与度量

[Kingmos-GUI第三方保存仓库](https://github.com/172625145/Kingmos-GUI)曾保存 `build/kingmos_gui/kingmos/system/sunfon.ttf`。已核文件4,686,044字节，SHA256：

`648b674639a9a83d35ca65934561dd38ee8d623afec2ee4e632ae6f7d53e0d55`

内部家族SC_Song、Version 1.00、唯一名`Microsoft:SC_Song:1996`；版权串ZHUHAI Stone Computerized typesetting system R&D LTD., 1995–1996。这些是内部文字记录，不能据此确认制作主体关系、原设备实装或具体发行年。第三方保存位置不证明Windows CE或其他硬件来源，也不证明使用或再分发许可。

- EBDT/EBLC v2，13ppem、1 bit、imageFormat 5连续MSB-first位流，indexFormat 2/5；没有栅格化轮廓。
- 原框13×13、horizontal advance13、bearingX0、bearingY11；基本区汉字最大墨迹12×12，但保留13×13存储框。
- 21,742个映射槽，21,741个非空字形；20,902个基本区汉字、21个兼容汉字，无扩展A汉字。
- GB2312的6,763个汉字、Big5基本区的13,061个汉字齐全，不等于所有符号、全Unicode或GB18030覆盖。
- **这一位图层没有ASCII。** 整个TTF的ASCII cmap不能当作该层ASCII的证据。

## 英数来源与补充边界

沿用已有Psion条目的[Revo v1.08(14) chitr保存来源](https://github.com/explit28/Psion-ROM/tree/main/Revo/Revo_v1.08%2814%29_chitr)，但选取该来源本来就存在的Arial13层，不拉伸原8或11层。

- 对应ROM为16,777,216字节，SHA256 `9c9fc74f237d7b741ab57b8eafa6cb400c5c72d80a9abb3c2b11b309b06b6210`。
- `Eon.gdr`是其0x2c1480偏移、0x23085长度的原片段，143,493字节，SHA256 `2477ea0d6bae65eba347eb8a9ef9785bf01b58279c903b10da12d1cbc673a5de`。
- GDR原Arial家族表明确列出UID `0x100001f4`，倍率1×1。该层13高、ascent11、正体常规字重、比例宽。不是同文件Times New Roman13，也不是较小位图的放大版。
- 95个可打印ASCII均有映射，空格为空，94个可见字符非空。原advance3–15px、left bearing0–2px、位图宽0–13px、高0–13px。
- 原文件版权文字为Copyright Monotype Typography Ltd 1997。这里记录来源，不作开放许可声明。

本站把英数字样标记为外部补充，不将它们计入SC_Song原生ASCII覆盖，也不改中文。三行固定样图为210×47透明PNG；前156×30区域与此前两行中文原图像素完全相同，新增右侧区域透明。英文行按原不等宽字进总长210，不强行压到中文行宽。三行基线分别11、28、45；4px行间隔是展示约定，不是原设备实测行距。

## 近似与范围

与HZK12的全部6,763个共同汉字裁外部空白后，86字精确同形；不缩放的±1px平移Dice平均0.830627，2,158字（31.91%）≥0.90，995字≥0.95。局部相似明显，不能只用低精确重复率称“全新”或“原创”。

已比较历史202条、当前补充13条及冻结28层的完整共同汉字。基于243条目快照，覆盖198/243个ID，仍45个缺口，部分来源只限固定小样本。另与Samsung YP-T6直接比较20,902共同汉字：1字精确同形，平均Dice0.644078。以上不是所有来源全库去重，也不是逐字手工设计或原创性证明。

只收此13层。12层与HZK11US的全部6,763个共同GB2312汉字同形；14/15/16层的重复或高度近似决定不因本次批准而改变。

## 固定样图重绘

先自行取得并确认有权处理上述两个SHA匹配的原文件，再运行：

```sh
python scripts/sc_song13_specimen.py \
  --source local-research/sunfon.ttf \
  --arial-source local-research/Eon.gdr \
  --output local-research/sc-song13-fixed.png
```

脚本只重绘已批准的固定中文两行及英数一行，双源长度和SHA均锁定。没有下载、执行ROM、轮廓取模、任意文字、字体或子集导出入口；已有输出不会覆盖。原TTF、GDR、ROM与完整字模不随仓库或网站分发，原字体权利仍归各原权利人。
