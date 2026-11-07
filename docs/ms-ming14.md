# MS Ming 微軟細明 14×14

来源：[第三方文件浏览页](https://github.com/Kochise/dreamcast-docs/blob/master/OS/msming.ttf)。保存路径OS/msming.ttf只是来源位置，不证明Dreamcast或特定Windows CE设备实装。

原文件3,172,552字节；SHA256 `5e9d90f68aae316091bd1bec797c2bc4670a1186caaf601ecae2e7e5661ae353`。Version 1.00，内部唯一名Microsoft:MS Ming:1999；版权串ZHUHAI Stone Computerized typesetting system R&D LTD., 1995–1999。内部年份不是已证实设备年代。

## 原位图与覆盖

直接解EBDT/EBLC v2、14ppem、1-bit、imageFormat 5连续MSB-first位流、indexFormat 2。不调用轮廓栅格器。水平字进14、bearing X=0/Y=12，字符框14×14。SFNT表checksum、cmap映射、EBLC地址/度量和逐行像素与FontTools独立实现交叉核验；再按原字节位置逐像素复查。

本层21,786个映射码位、21,784非空、20,902非空汉字。GB2312汉字6,763/6,763、Big5基本汉字13,061/13,061，不是全Unicode/GB18030声明。本层无非空ASCII，不推断整个TTF无西文。固定两行样文没有缺字，不补其他字体的英数。

## 离线重绘

自行取得有权处理且SHA匹配的本地文件，使用Python和Pillow：

```sh
python3 scripts/msming14_specimen.py --source /path/to/msming.ttf --output local-research/generated/msming14.png
```

仅重绘已批准14×14层的固定两行样图，保留原字框与像素，额外4px行距仅为布局。脚本不联网、不导出字体或字库子集，也不接受任意样文。

第三方保存不等于开放授权。只公开固定样图、来源说明和无字模脚本，不附原TTF、完整字模或子集；不提供统一开放字体许可。

## 比对边界

已查历史及近期具名基准中未发现高重复证据，不声称全目录整库排除，也不以原存位图证明全部人工设计。基准合并覆盖当前239项快照中的194个ID，45项仍有输入缺口，含受限样本。仅收14×14，不收同文件其他字号，也不收SC_Song。

最终近似复核对202条历史记录、77条近期命名缓存和24个新鲜源解析层的每层全部共同汉字进行比较（共303层，含重复来源，不代表303套独立字体）。裁外围空白后允许±1px平移，不缩放、不以尺寸差截断。共同汉字至少1,000的层中，最高平均Dice为Dotum14：0.696718（7,476共同字，1个精确同形，255个Dice≥0.90）；文泉驿14为0.693668（20,902共同字、9个精确同形）。这是已测范围的近似审计，不填补上述45项缺口，也不证明原创性。
