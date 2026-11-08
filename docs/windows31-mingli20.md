# Windows 3.1 MINGLI20 20×20

本项只展示获准的「視野無限廣，窗外有藍天。」固定原格预览。1×为240×20，4×为960×80的最近邻整数复制，没有借字、补画或追加ASCII。

## 来源与边界

[Windows 3.1 Traditional Chinese保存页](https://archive.org/details/windows-3.1-traditional-chinese)中的3.10.151保存件包含MINGLI20.FON。成员目录日期1993-05-02只是保存元数据，不认证设计年份、微软原盘或作者。同包旧MINGLI.TTF存在CompuFont/MingLi43保存异常，不以其文件名或标识推断本层作者及设计谱系。保存来源不等于开放再分发授权。

| 本地输入 | 字节 | SHA256 |
| --- | ---: | --- |
| MINGLI20.FO_ | 643392 | f6a29a5083186e56cabaac7acc08cb2d672776b277f0512557cfe76142aaf05f |
| MINGLI20.FON | 832088 | 5b0d5a506b03b9f6ab981ff220c1e14aafda7966960cc4234ba3bb6f76003b09 |

CWIN30/ChineseBig5头记录20×20原生1bpp框；双字节原槽从5408起，每槽60字节、每行3字节，MSB在左，0为墨迹。行末4bit是背景。驱动原区间A140–A3E0、A440–C67E、C940–F9D5对应基槽0、684、6085，Big5行内157列。独立解压、逐位解码和反向回填覆盖全部13906槽（128 ASCII及13778双字节槽），不是现代轮廓取模。

基本Big5非空汉字13061/13061，另2兼容汉字，共13063唯一Han和13065原Han变体。十、卅别名保留，原汉字矩阵互异。GB2312仅4383/6763，不称完整简体。原生ASCII为10×20，95可打印码位中94非空、空格为空；当前批准图只含中文标点，不展示ASCII，不称原库无ASCII。

固定预览以20px字进排列原格。原运行时advance、bearing、baseline未完全恢复，不称复原Windows界面排版；预存位图也不证明上游全为手工设计。

## 与MingLiU20及MINGLI24的关系

与现库MingLiU20有明确近缘：13063共同Han，1794墨迹精确相同；完整墨迹±1px平移的均Dice为0.845565947，中位0.869888476，4499字低于0.80。最高近邻已从原BDF独立全量重算。不是近整层复制，也不据此称独立原创、认定作者或复制方向。

250比较记录、46补充层及19原槽池加CCDOS原槽阈值控制已核；有限预览与条件映射不升级为整库语义比较。仍有12个原源／布局未闭合及参考图限制，不能叫全库穷尽。同包MINGLI24与HITECH CFONT.24全部13494共同Big5原码、完整72字节框反相后全同，因此24层合并来源，不另增款。

## 离线重绘

自行取得有权处理且SHA一致的本地MINGLI20.FON。公开脚本不含字模、映射数组或任意文本导出，不联网、不执行旧程序，只重绘上述固定句。

```sh
python scripts/windows31_mingli20_specimen.py --source /本地/MINGLI20.FON --output /新目录/preview.png --scale 1
python scripts/windows31_mingli20_specimen.py --source /本地/MINGLI20.FON --output /新目录/preview4.png --scale 4
WINDOWS31_MINGLI20_SOURCE=/本地/MINGLI20.FON python tests/windows31_mingli20.test.py
```

输出父目录须已存在，输出不得存在。输入校验大小与SHA，拒绝非普通文件、符号链接、硬链接与祖先符号链接；输出使用排他创建且不覆盖。只支持POSIX安全no-follow文件访问。编码PNG的字节SHA必须与批准图一致，否则失败退出。未提供私有输入时测试明确跳过源验证，不将其当成已通过。

- 1× PNG SHA256：692fd91faef8fed21c152ed85fb35e29af98ff210a4d4734459addbf479803a5。
- 4× PNG SHA256：9d3d57d4f363802ed994503524cc564f027d1db420076895bcbf37da29fdb8e9。

仅公开固定PNG、事实说明和无字模重绘工具；不公开原件、完整字模、私有JSON、映射数组或来源不明子集。
