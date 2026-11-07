# 中文点阵字样

收集中文点阵字形，记录来源、尺寸与提取方法。

**[在线浏览](https://fonts.resmx.com/)** · [GitHub Pages](https://legendtired.github.io/chinese-bitmap-specimens/) · [研究记录](docs/research-notes.md) · [提供线索](CONTRIBUTING.md)

## 项目缘起

中文点阵字体的资料年代久远，散落在旧网站、论坛、软件和设备中。随着链接失效、内容向移动平台迁移，以及 AI 生成内容增多，原始资料越来越难寻找，有价值的信息也更难筛选。

这个项目希望把分散的字样和资料整理起来，记录来源与获取线索，方便查阅、比较和研究。

## 收录原则

- 收录中文点阵字样，包括历史字库、系统与设备字体，以及现代像素字体。
- 以原始位图或可核验的像素网格为依据，不收录普通矢量取模或简单放大得到的重复字样。
- 注重字形差异与代表性，重复或高度近似的版本择取代表，并保留相关来源。
- 保留原有像素、字宽和缺字情况，注明来源、尺寸、字符覆盖及许可线索。

## 字样

### 方正像素 12×12

![方正像素12×12](assets/specimens/founder_pixel12.png)

### Mac OS / Ikarus Kai 12×12

![Mac OS Ikarus Kai 12×12](assets/specimens/apple_kai_12.png)

### Sony G90

![Sony G90 OSD字样](assets/specimens/sony-g90-original.png)

## 目录

当前 **242 个条目**：241 个原生、设计格点或设备字样，1 个参考资料图。固定字框高度为 8–64px。

- 原生字样按原尺寸和整数倍显示，可筛选、收藏和对比。
- 来源、版本、字符覆盖和许可见各条目详情。
- 同尺寸的近似版本选取代表展示，保留其他来源。
- 资料图和不定字框单独标记。缺字留空。
- 收藏保存在当前浏览器。

## 获取字库

- [Sony PSP 中文BWFont 16×18](docs/psp-bwfont.md)：官方6.61字节来源、第三方Unicode映射边界与无ASCII固定样图重绘。

- [Sony Ericsson P802 小号12点字面](docs/p802.md)：原生14高行格、完整GB2312汉字与部分繁体、同层ASCII；只提供固定样图和无字模离线重绘方法。

- [Nokia 9210C与P908研究变体](docs/phone-gdr.md)：9210C三款及已合并到Sun GBK14来源说明的P908；区分14／15／17／19点典型字面与16／18／20高行格，仅固定两行样图和SHA锁定的离线重绘方法。

- [IBM AIX / ISAS 繁体宋体24点字面](docs/aix-isas-cns.md)：保留26×27存储与同源13×27 ASCII，记录同源扩展及编码冲突；仅固定样图与无字模重绘方法。

- [HP-UX 打印宋体40点](docs/hpux-song.md)：完整GB2312汉字，未找到配套半角ASCII；仅固定中文预览与无字模重绘方法。

- [HP-UX 繁体宋体24／34／42点](docs/hpux-sung.md)：原CNS平面1／2及同源半宽ASCII，仅固定样文和无字模方法。

- [Samsung SGH-R208 16×16](docs/samsung-r208.md)：完整GB2312汉字及同固件8×16英数，保留原8px逗号映射；仅固定样图、聚合审计与无字模离线提取方法。

- [Sunplus SPHE8202L 简体16×16／20×24](docs/sunplus-sphe8202l.md)：各含完整GB2312汉字；12×12与已有HZK12完全相同不新增，无半角ASCII，不收录繁体，仅固定样图与无字模离线提取方法。

- [中国版PS2 24×24](docs/ps2-china.md)：ROM2中文点阵与同ROM英数，完整GB2312汉字；仅固定样图、已核映射及离线提取方法。

- [Windows 3.2 宋体13／20点](docs/windows32-cwin30.md)：安装盘存档中的原生CWIN30点阵，完整GB2312与同文件ASCII；固定样图及无字模的离线提取工具。

- [三国志Ⅴ DOS 16×14](docs/san5-dos.md)：13,052个主汉字的映射与去重记录；仅提供固定样文重绘，不公开完整字库。

- [Psion 618C 8／11点](docs/psion618c.md)：简繁汉字及GDR离线导出。

- [文曲星 PC505 14×15](docs/wqx-pc505.md)：原厂仿真器obj中的原生汉字和8×16 ASCII；完整字库仅本地提取。

- [FM Towns F20 20点](docs/fmtowns-f20.md)：JIS原生汉字及ANK样图，导出边界分别记录。
- [Solaris 中易宋体五个字号](docs/solaris-gbk.md)：12／14／16／20／24点原生PCF与Unicode／原码导出。

- [Nokia DCT3 1999](docs/nokia-dct3.md)：9004个原生11×12汉字，简繁兼有，保留西文原字框与度量字段。

- [IBM PC DOS 三套24点](docs/ibm-pcdos.md)：楷体、黑体和仿宋；标准GB2312映射及未编码扩展的离线导出。

- [Sharp X68000 16点](docs/sharp-x68000.md)：校验CGROM后导出原生16点字模；不重复收录24点。

- [四通 MS-2401H 四套32点](docs/stone-ms2401h.md)：校验BIOS与CA字库ROM，解压导出每套6763个汉字。

- [字体获取与导出](docs/font-export.md)：按输入格式查找方法与限制。
- [Panasonic FS-UV1 / FS-A1F 16点](docs/panasonic-fs-uv1.md)：校验ROM后导出Unicode BDF。

- [文曲星 NC1020 12点](docs/nc1020.md)：下载来源镜像，用脚本提取为 BDF。
- [Casio Ex-word 12／24点](docs/casio-exword.md)：下载 CJF，用脚本转换为 BDF。12点列为推荐。
- 其他条目的获取入口见网站详情。

本站提供固定字样和提取工具。字体使用与再分发按原来源许可执行。

## 资料

- [研究方法](docs/methodology.md) · [研究记录](docs/research-notes.md)
- [目录数据](data/catalog.json) · [统计](data/summary.json)
- [v16](docs/release-v16.md) · [v17](docs/release-v17.md) · [当前状态](docs/PROJECT_STATE.md)
- [贡献指南](CONTRIBUTING.md) · [第三方声明](third_party/README.md)

## 本地维护

直接打开 `index.html` 即可浏览。维护需要 Python 3.9+ 和 Node.js 18+：

```sh
python3 scripts/workspace.py build
python3 scripts/workspace.py check
```

目录单源为 `data/catalog.json`。原字体、ROM 和研究输入放在被忽略的 `local-research/`，不随网站发布。详见[开发说明](docs/DEVELOPMENT.md)与[部署说明](docs/deployment.md)。

- [MStar 电视/DVB 简体18点](docs/mstar-18.md)：18×18存储、最大字面14×14；完整GB2312与原生ASCII，附离线导出方法。
