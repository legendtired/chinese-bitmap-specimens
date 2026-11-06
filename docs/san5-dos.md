# 三国志Ⅴ DOS · 16×14

这是《三国志Ⅴ》DOS 版资源 `ZIKU.16P` 中的原生点阵字样。已恢复13,052个主汉字的对应关系，固定中文样句完整；西文行使用原库全角英数，不是半角 ASCII。仅公开固定预览与不含字模的重绘工具。

## 来源与许可

输入来自第三方游戏存档副本，游戏压缩包哈希与 [rwv/chinese-dos-games 资源索引](https://github.com/rwv/chinese-dos-games/blob/master/games.json) 的记录一致。没有实体原盘读取链，不能称为已验证原盘 dump。未执行游戏，未验证全部游戏内码。

- 文件：`ZIKU.16P`，384,704字节。
- SHA-256：`94c3a14bec8930525d798e891d8b3493f64ca292e25ef36d8d7cd3ad18a46bd5`。
- [2004年游戏字库研究](https://www.xycq.org.cn/forum/archiver/tid-34610.html)与[宏碁／龍碟历史线索](https://scrappedblog.blogspot.com/2014_01_22_scrappedblog_archive.html)可供追溯，但本次没有取得龍碟原 PAT 字库逐字比对，不能据此认证字形作者或创作年代，也没有电视字幕机来源证据。

原字体再分发与商用许可未确认。第三方存档可取得、码表或转换工具采用开源许可，都不等于原字库获准再分发。完整字体、游戏资源、BDF、全部位图数组和本地候选映射不随网站发布。

## 存储与映射

每字16宽×14高，1bpp，按行存储，每行2字节，最高位在左；每字28字节。前384,608字节包含13,736个完整字槽，末尾96字节尚未解释。

以下是从0开始的物理字槽编号，不是游戏内码：

- 0–683：684个符号、部首和控制图形位置，只有部分映射已核验。
- 684–6084：CNS第1字面的5,401个常用汉字。
- 6085：实际字形为「碁」，游戏内码未验证。
- 6086–13735：CNS第2字面的7,650个次常用汉字。

13,052个主汉字位图均非空且各不相同。CNS与 Windows TCA 两套码表交叉核对，并目视检查边界及90个次常用随机样字；不是人工逐字认证全部字形。

映射依据：[公會碼结构](https://pedia.cloud.edu.tw/Entry/Detail?title=%E5%85%AC%E6%9C%83%E7%A2%BC)、[Windows TCA 20001表](https://github.com/SheetJS/js-codepage/blob/master/bits/20001.js)、[CNS Unicode码表镜像](https://github.com/m80126colin/cns11643/blob/main/data/MapingTables/Unicode/CNS2UNICODE_Unicode%20BMP.txt)、[CNS官方开放数据](https://data.gov.tw/dataset/5961)。

需要保留的边界：

- 第5416槽字形上部为彐，保留「彞」U+5F5E；Windows TCA表在该处使用「彝」U+5F5D，不能直接替换。
- 前684槽存在264处 Windows 与现代 CNS 映射差异，部分为旧表未编码；第0槽为空格，第404槽实际空白，不补造字符。
- 样文用到的符号和全角英数字槽已实际渲染核对。西文末尾点号采用旧 TCA U+2024，现代 CNS 同位置为 U+FF0E；只确认所用原字形，不把候选映射说成游戏编码定论。
- 不宣称完整 Big5、全部13,736槽的 Unicode 映射已认证，也不把末尾96字节算入本次已确认字库。

## 去重范围

按同 Unicode 汉字比较，先只裁空白边缘，不缩放；每组共有13,051个主汉字：

- KC 国乔15繁体：仅1字相同（車），其余13,050字不同。
- UnionWay 双桥16：0字相同。
- GNU intlfonts 的 ETen Taipei16：仅3字相同（單、旨、車），其余13,048字不同。

比较输入 SHA-256 分别为：

- KC：`f628b02934c02927cc05923f3c7c01d4114b9fa58019c42072bc32442fd0e97e`。
- UnionWay：`b3b5deb74be5a82a744c3e5fccec65251e5d685e2498969b0c3f6ea78cc6445f`。
- ETen：`3dd6b7c025800f9bcfb46b107bd2ac305a7575146ff2fa34114e1399d9d7071e`。

旧缓存中的 `taipei16.bdf` 实际署名 UnionWay，不是 GNU 的 ETen；以内部 FONT／FOUNDRY和上述哈希区分。结果支持另行收录，不表示已证明原创作者或与所有历史字库无亲缘。

另对[本站提交 1d003b3](https://github.com/legendtired/chinese-bitmap-specimens/commit/1d003b3e46b20219b31207ab64883737aac94b9e)的222条目做固定预览检查：221项原生预览第一行墨迹均不相同，1项参考资料图排除；各本地PNG的SHA与该提交目录匹配。这里只是样图比较，不能当作221套完整字库的全量去重。

## 固定预览重绘

自行取得并确认有权处理上述输入后，放在被忽略的 `local-research/`。需要 Python 3.9+ 和 Pillow：

```sh
python3 scripts/render_san5_specimen.py \
  --source local-research/san5/ZIKU.16P \
  --output local-research/generated/san5-fixed.png
```

工具只接受精确长度与哈希，拒绝覆盖已有输出；不联网、不执行游戏、不输出完整字库。脚本只包含这两行固定样文的位置编号，不携带字模或全库映射。

中文为「視野無限廣，窗外有藍天。」；西文为「０１２３４５６７８９　ＡａＢｂ　ＧｇＭｍ　！？：＋－․」。按原16px存储字框作等宽预览，未缩窄、补画或替换。画布432×30，中文从y=0开始，西文从y=16开始；16px字进与2px行间距是本预览排版约定，游戏字距和基线未验证，不是游戏屏幕布局复刻。

后续若制作Unicode字体，应先解决符号候选和异体映射，再单独记录输出范围、度量约定及许可；本次没有提供可直接安装的完整字体。
