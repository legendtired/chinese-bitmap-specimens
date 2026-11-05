# 研究记录

## SimSun 与方正像素

SimSun 5.03 内嵌点阵与方正像素的已核样本一致：12px 为24个汉字及2个标点，14px 为10个汉字及2个标点。目录采用方正自身字形，SimSun 记入相关来源。所查 SimSun 位图层不含可打印 ASCII，轮廓层含西文。

来源：[方正项目](https://nzj.foundertype.com/208.html?font_id=479)、[SimSun 历史镜像](https://github.com/dolbydu/font/blob/master/unicode/SimSun.ttc)。

## CCIC chkan24 与 ISAS 宋体24点

当前612×52样图逐像素一致，两项均标注 ISAS 1988，合并展示并保留来源。

来源：[CCIC BDF 目录](https://www.ibiblio.org/pub/packages/ccic/software/fonts/gb/bdf/)、[GNU intlfonts](https://ftp.gnu.org/gnu/intlfonts/)。

## 设备字样

- **MN1871681**：按1998–1999年文档网格重建，疑似客户版本。[文档](https://datasheet4u.com/pdf/511850/)。
- **Sony G90**：实际字体 ROM 解码，前景规则参考同系芯片资料，实机显示待核。[来源](https://www.curtpalme.com/SonyG90_Downloads.shtm)。
- **NC1020**：模拟器镜像中的12×12字模。[提取说明](nc1020.md)。
- **Casio XD-A10000**：CJF 文件中的12／16／24点阵。[提取与比对](casio-exword.md)。

## 尺寸与版本

- Osaka：9／14／18／24ppem 的保存字框分别为9×11、14×15、18×18、24×22。
- ELISA：8×8设计，10×8字框。
- 所查 Silver 附带版本与 M+ j12r 共有6,355个汉字，其中6,172字紧裁墨迹一致（97.12%）。相关来源并入 M+ 代表条目。[Silver](https://poppyworks.itch.io/silver)。

各条目的尺寸、覆盖、版本和许可见[目录数据](../data/catalog.json)。
