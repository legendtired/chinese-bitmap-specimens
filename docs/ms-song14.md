# MS Song 14×14 与外补 Arial13

中文为 `MSSONG.TTF` 原存14×14位图。英数按用户选择，另用 `Eon.gdr` 的原生Arial13。它们来自不同来源，不是已证原装配套；Arial没有缩放或改称14点，中文没有补字或改笔画。

## 中文来源与版本

实际取得的是[Rose-Hulman大学课程软件目录保存的IE5语言支持包](https://www.rose-hulman.edu/class/ee/hoover/Orcad%20Lite%209.2%20Schematic%20Drawing%20and%20Simulation/Orcad%20Lite%209.2%20Freeware%20Installation%20Disk/ie5/En/)，不是本次从微软官网取得，也不能据此证明任何特定设备实装。

- `ielpkzhc.cab`：2,869,970字节，SHA256 `9229d8b3e2d54a8f46aee2dfffad55a068028c4960d6546942fb29940a9bf7f4`。
- 其中 `MSSONG.TTF`：2,569,116字节，SHA256 `cfc3544bf432b43f8bd1eacd728c3df7bf8a85320dddec53e7f564b32d00072d`。
- 字体内部家族MS Song、Version 1.00、唯一名 `Microsoft:MS Song:1996`；版权串为ZHUHAI Stone Computerized typesetting system R&D LTD., 1995–1996。这是源文件内部声明，不是独立确认的制作年代或手绘证据。
- CAB成员时间1999-04-26，包内时间戳1999-08-24，大学保存元数据2000-05-15。它们是包装或保存信息，不作为字体设计年份。
- 包内Microsoft签名字节和VeriSign时间戳反签名的静态检查通过；没有完成外部根信任、撤销状态或现代Authenticode策略核验。旧MD5/RSA也不是现代安全保证，不称“已完整官方认证”。

[历史Microsoft知识库Q159471的保存页](https://jeffpar.github.io/kbarchive/kb/159/Q159471/) 提到Office97简体中文支持包中的Mssong.ttf，但其文件长度不同，只作名称与产品关联旁证，不充当此样本版本或哈希证明。

## 原位图、度量与覆盖

- EBDT/EBLC v2，14ppem，1 bit，indexFormat 2/5、imageFormat 5连续MSB-first位流。没有从轮廓重新取模。
- 原字框14×14，字进14，bearingX0、bearingY12，BBX下边界-2。最大汉字墨迹13×13，不能因此裁成13点。
- 7,429个原存映射字形、7,428个非空。GB2312的6,763个汉字全部非空；Big5基本汉字仅4,383/13,061，**不是完整繁体字库**。
- **这一位图层没有半角ASCII。** 整文件cmap或西文轮廓不代表此层位图覆盖；本次不使用轮廓补齐。
- 固定中文仅为「视野无限广，窗外有蓝天。」。不显示旧繁体缺字诊断行，不借其他中文字体补缺，不替换简繁码位。

16个SFNT表和整文件checksum、21,982项cmap、14层93个子表，以及全部7,429字形、1,456,084像素都经原表独立寻址和FontTools交叉核验；另用Python/iconv互核GB2312与Big5汉字集合。原生位图证明源里保存了这些像素，不证明最初全部人工绘制。

## 外补Arial13

沿用已有Psion资料的[Revo v1.08(14) chitr保存来源](https://github.com/explit28/Psion-ROM/tree/main/Revo/Revo_v1.08%2814%29_chitr)，选取原生Arial13，不缩放成14。

- 对应ROM为16,777,216字节，SHA256 `9c9fc74f237d7b741ab57b8eafa6cb400c5c72d80a9abb3c2b11b309b06b6210`。
- `Eon.gdr`为该ROM偏移0x2c1480、长度0x23085的原片段，143,493字节，SHA256 `2477ea0d6bae65eba347eb8a9ef9785bf01b58279c903b10da12d1cbc673a5de`。
- 原Arial家族表关联UID `0x100001f4`、倍率1×1，13高、ascent11、正体常规比例宽。该已核来源没有原生14高Arial层。
- 95个可打印ASCII有映射，空格为空，94个可见字符非空。原advance3–15px，left bearing0–2px，right bearing−1–5px，逐字ascent−1–11px，位图宽0–13px、高0–13px。原度量与像素均保留。
- 原文件版权文字为Copyright Monotype Typography Ltd 1997。它不是开放许可声明，也不是MS Song的署名。

展示图为210×32透明PNG。中文168×14区域的前景像素与已核简体原图逐像素相同，只把白底转透明；右侧扩出的42列为空。第二行单独展示Arial13，保留210px原字进总长；其13高原行框放在14高展示行中，底部多1px透明留白。基线12/29与4px间隔是本站组合排版，不是原机行距或运行时配对。外补英数不计入MS Song原生ASCII覆盖。

## 比对范围

14层与202历史记录、13项补充、28冻结层及5份直接参考共248条记录，逐层比较全部同Unicode非空汉字：只去外围空白，检查精确一致及dx/dy各-1/0/+1的最大Dice，不设字框差门槛，不缩放或裁内部。

- HZK14：6,763共同字，5字精确同形，平均Dice0.8391050622；2,507字≥0.90，984字≥0.95。
- Sun GBK14：6,763共同字，41字精确同形，平均0.8231160058。
- Samsung YP-T6：6,763共同字，38字精确，平均0.7364970726。
- SC_Song13：6,763共同字，0字精确，平均0.6408914478。

在已测范围未见整套高度重复，但保留明显局部相似，不宣称独创或全球唯一。冻结基线仍为198/243个目录ID、45个缺口；三份恢复来源另作直接比较，不把它们改写成冻结覆盖，也不声称全站全部字体整库排除。

只收14层。12层与HZK11US的全部6,763汉字同形；16层与银钩铁画1999的6,763共同字中6,726字精确相同，平均Dice0.9994172667。两者不因此次批准而重新收录。

## 固定样图重绘

自行取得并确认有权处理上述SHA匹配的两个原文件，使用Python和Pillow：

```sh
python3 scripts/ms_song14_specimen.py \
  --source local-research/MSSONG.TTF \
  --arial-source local-research/Eon.gdr \
  --output local-research/ms-song14-fixed.png
```

脚本只重绘已批准的固定简体一行与外补Arial13英数一行，双源长度和SHA锁定；已有输出不会覆盖。不联网、不执行ROM或安装程序、不取模轮廓，不提供任意文字、字体或子集导出入口。

大学保存、内部署名与包内签名均不等于再分发许可。只公开这一固定小样图、必要事实和无字模方法；完整CAB、TTF、GDR、ROM、字模数组及字库子集保持私有。字体使用与再分发仍受原权利约束。
