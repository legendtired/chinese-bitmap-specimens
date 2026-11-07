# Sony PSP 中文BWFont 16×18

本条展示官方PSP系统软件6.61中的 `gb3s1518.bwfon`。它是原生1-bit中文点阵，每字36字节，存储框 **16×18**，汉字最大墨迹 **15×18**；文件名不是15像素存储宽的证据。新增条目默认不推荐，原241条资料与样图、17项推荐不变。

## 来源与年代

- [Sony PSP系统软件官方支持页（2015存档）](https://web.archive.org/web/20150130152009/http://www.playstation.com/en-us/support/system-updates/psp/)：该页注明6.61于2015年1月15日发布。本次使用非Go版6.61更新包，只静态解析，不运行固件。
- 包内版本记录：`5553,0,3,1,0,6.61`；01g档内名称表：`00489,flash0:/font/gb3s1518.bwfon`。
- 更新包32,580,549字节，MD5 `6be8878f475ac5b1a499b95ab2f7d301`，SHA256 `dc23a6dabdaed40bbfaad811d1f170346b911ba9750478fe5928d9f10c94f552`。
- 目标字体1,023,372字节，SHA256 `05c9991fc82c96672026d5e71da595d0a5b028a74607d726e613099db8a3699a`。
- 静态解出435个目录／文件记录，444个解码块的PRX SHA1与KIRK头／数据CMAC均通过。目标记录相对PSAR偏移23,712,416，数据偏移23,713,024；560,928字节加密块解压为上述字体。
- 格式参考：[PPSSPP PSAR文档](https://github.com/hrydgard/ppsspp/blob/d4e3c7eb2bf0ec9241621b3752cd3e5406178c78/docs/PsarFileFormat.md)。源字节与已核第三方镜像一致，但镜像不是授权依据。

本次锁定的是**2015年PSP系统软件6.61版本中的字节**。PSP硬件2004年发行，不证明本字体于2004年制作；本次没有证明更早固件使用完全相同的字节。

## 映射、覆盖与度量

BWFont没有内嵌Unicode目录。使用的165段压缩Unicode表来自[intraFont固定版本](https://github.com/pspdev/libintraFont/blob/d461ba98e61e6f8f381c450c4774fb3e34d8600a/src/intraFont.c)，源码头注明作者BenHur与CC BY-SA 3.0许可；本仓库不复制该完整映射表或源码，也不将其许可延伸至Sony字体或整个仓库。[Jpcsp的BWFont实现](https://github.com/jpcsp/jpcsp/blob/00ac4d6daedd89c0492093ae83fb0d3d819af414/src/jpcsp/format/BWFont.java)采用相同的intraFont表，不是另一份独立官方映射证据。尚未从Sony固件模块独立恢复查字逻辑。

- 28,427个映射槽恰好用尽字体文件；28,426个非空字形，唯一空槽是全角空格U+3000。
- 非空基本区汉字20,902个、扩展A汉字6,582个，另有21个兼容汉字。
- GB2312汉字6,763/6,763、Big5基本区汉字13,061/13,061齐全。不是全部Big5符号／别名、GB18030或Unicode覆盖声明。
- 没有U+0020–U+007E ASCII映射，不以全角英数替代，也不拼接另一字体。这不代表整个PSP系统没有西文字体。
- 行数据高位在左。全部槽位经逐位落点与逐行16位两种解码交叉核对，并回写为相同原字节。
- Sony原固件的advance、bearing和基线未核。intraFont的16px advance、15px top bearing是该库约定，不当作原机实测。

固定预览是192×38两行简繁样文：“视野无限广，窗外有蓝天。”及“視野無限廣，窗外有藍天。”；行间2px为展示排版。保留16×18存储框及原像素，不裁框、不补字。这不是PSP界面截图或原机排版复刻。

## 查重范围

历史202、当前补充13和近期26层均完成可用同Unicode非空字形完整交集的精确及近似比较。比较域为U+3400–U+9FFF，不含21个兼容汉字。精确仅裁外围空白；近似允许横纵各±1px平移，分母保留完整墨迹，不设尺寸差门槛、不裁切或缩放字形。

已查范围未见高重复。GNU Unifont16为2/27,484精确同形，平均Dice 0.652018；文泉驿宋16为2/27,483，平均Dice 0.651996；P908大号为1/15,788，平均Dice 0.641525。方正像素18的0.737802平均Dice仅基于15字样本，不能扩称全库。

这些层有重叠，**不是241套独立字体**。实际覆盖收录前196/241个当前ID，仍有45个缺口，部分基准只保留小样本。未发现高重复不等于全目录已查或独立设计／作者关系已证。

## 离线重绘固定样图

自行取得有权处理且SHA匹配的本地BWFont和上述固定版本 `intraFont.c`。公开工具不含原字体、Unicode全表、解密密钥或解包器，只读取指定本地输入，重绘这两行固定样文。

```sh
python3 scripts/psp_bwfont_specimen.py \
  --source local-research/psp/gb3s1518.bwfon \
  --mapping-source local-research/psp/intraFont.c \
  --output local-research/generated/psp-fixed.png
```

映射源SHA256：`3f8692c9c9e63ddb475cb7d0288c73354ca02a25d542bf421f3b9759a0f4a5b2`。工具先校验两个输入，仅取固定样文所需槽位，不联网、不执行固件、不导出任意文字、完整字体、字模数组或子集。

运行带原始输入的严格回归：

```sh
PSP_BWFONT_SOURCE=local-research/psp/gb3s1518.bwfon \
PSP_MAPPING_SOURCE=local-research/psp/intraFont.c \
python3 tests/psp-bwfont.test.py
```

未设置两个输入时，测试明确报告未运行私有源回归；只进行公开固定PNG、元数据、原241项不变及错误输入拒绝检查。源回归使用独立固定槽号逐像素核对，不把PNG哈希相符冒充源验证。

## 公开边界

原厂来源与开源解析代码的许可不等于原字体开放授权。仅公开固定小样图、必要元数据、来源说明和无字模固定预览器；不公开更新包、完整BWFont、完整字模JSON／SQLite、解密材料或其他字库子集。使用与再分发须另核原权利。
