# SimSun 3.03（Windows XP）与5.03（Windows 7）：12／14px 原生点阵

本站按版本并列收藏两版中易宋体，每版只展示12、14px两个字号。这是**同一 SimSun 字体家族的不同版本**，不是两个独立原创字体家族；字号条目也不等于独立字体家族数量。原方正像素条目和样图继续保留。

## 推荐版本

- **Windows XP 对应版本：SimSun 3.03**，12px和14px均推荐。微软也将3.03列于Windows Server 2003。
- **Windows 7 对应版本：SimSun 5.03**，12px和14px均推荐。

系统名说明微软官方列出的版本对应关系，便于识别和比较；下列样图使用第三方保存件，不能据此称为直接取自Windows安装盘。两版四项接在原有推荐之后，原推荐顺序不变。

## 短样图

四图均为同一句“视野无限广，窗外有蓝天。”，直接读取各自原生 EBDT/EBLC 的1-bit位图。未栅格化轮廓、借字、补画或统一缩放字号。字进、bearing和基线来自各自源层；放大图只做4倍最近邻复制。

### SimSun 3.03 · Windows XP

- [12px资料页](https://legendtired.github.io/chinese-bitmap-specimens/fonts/simsun_v303_12.html)

![3.03 12px，4倍](../assets/specimens/simsun_v303_12_4x.png)

- [14px资料页](https://legendtired.github.io/chinese-bitmap-specimens/fonts/simsun_v303_14.html)

![3.03 14px，4倍](../assets/specimens/simsun_v303_14_4x.png)

### SimSun 5.03 · Windows 7

- [12px资料页](https://legendtired.github.io/chinese-bitmap-specimens/fonts/simsun_v503_12.html)

![5.03 12px，4倍](../assets/specimens/simsun_v503_12_4x.png)

- [14px资料页](https://legendtired.github.io/chinese-bitmap-specimens/fonts/simsun_v503_14.html)

![5.03 14px，4倍](../assets/specimens/simsun_v503_14_4x.png)

## 版本与来源证据

[微软SimSun字体页](https://learn.microsoft.com/en-us/typography/font-list/simsun)把3.03列于Windows XP / Server 2003；[Windows 7字体清单](https://learn.microsoft.com/en-us/typography/fonts/windows_7_font_list)列5.03。这里检验的文件来自第三方保存镜像，name表分别明确为Version 3.03与Version 5.03，**不是经过微软安装介质或签名认证的原件**。官方版本对应关系不能代替文件来源认证，也不证明所有补丁版本的文件相同。

- 3.03：[保存件浏览页](https://huggingface.co/cabrel09/insect-detection/blob/4892f28189dd6eaad8c0087834d47aaff93982e5/simsun.ttc)，10,500,792字节，SHA256 `7a368113c36d516aac1a825acc4bbbc9906c4d197f7c649e7fe0f6f31e7475dd`。
- 5.03：[保存件浏览页](https://github.com/dolbydu/font/blob/master/unicode/SimSun.ttc)，15,323,200字节，SHA256 `ff7d69bfa6588d3fdedbddbe3a29ac11f0c50236723ee72a9ea49ec3e2553f5d`。

两个样本均取TTC font 0的12／14ppem原生1-bit层，不从轮廓临时取模。全量源像素、BBX和advance读回比对无差异；这一转换验证不代表完整字体的授权或历史认证。

## 覆盖与版本差异

两档均有相同的覆盖计数：3.03含21,742个Unicode、21,742个独立字形；5.03含28,429个Unicode、28,418个独立字形。两版交集21,741个Unicode，3.03独有U+3000全角空格；5.03多6,688个，其中扩展A为6,582个。Unicode数量与独立字形数量不同，别名不重复算独立字形。

按这21,741个共同码位逐字比较：

- 12px：在同一字符原点／基线坐标下，21,682个ON像素集合不同；剔除外缘空白并平移对齐后，21,658个紧裁形状仍不同。
- 14px：同原点／基线像素不同21,693个；紧裁形状不同21,662个。
- 两档共同字进全部相同。纯空白BBX边框的变化不算ON像素变化。

因此，两版差别不只是基线或空白边缘，5.03不能当作3.03的像素等价替代。比较只针对上面两个精确哈希样本，不断言其他版本、原创性或复制方向。

两版这两档原生位图均无可打印ASCII。文件的轮廓层可以有西文，这不意味着本次点阵层也有；短样图只显示原生中文和标点，不外补ASCII。

## 与方正像素的关系

方正12／14px仍使用原有官方逐字预览来源、原样图和原许可说明，不改成SimSun。历史有限样文核验保留：12px为24个不同汉字及2个中文标点，14px为当前样句10个汉字及2个中文标点；对应SimSun 5.03像素一致。本轮另以旧诊断子集核验了每档15个共同汉字，像素与字进全部相同。两组证据的样本范围不同，不能合并当作完整字库核验。

这些有限重合**不能证明方正完整字体与SimSun相同、同源、谁复制谁或许可相同**。现在按用户选择把版本资料并列，原来的`simsun_native_12/14`仅迁移到明确的`simsun_v503_12/14`，不再把它们作为方正条目的合并别名。原方正收藏ID不变。

## 许可与公开边界

SimSun为专有中易系统字体。公开镜像、镜像项目的MIT标签、可下载或技术上可提取，均不代表字体开放授权。[微软字体FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)不授予完整字库、转换点阵或子集的任意再分发权，也不能据此认定私人转换、设备嵌入、游戏或网站使用已经获准。

本次公开内容限介绍、聚合核验数字与固定十二字PNG。仓库不附TTC、BDF、完整字模、可还原完整字库的映射或配方，不提供任意文字重绘服务。正式使用请另行确认相应产品和字体许可。
