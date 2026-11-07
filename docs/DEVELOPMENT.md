# 本地开发

## 环境与命令

浏览网站直接打开 `index.html`。维护需要 Python 3.9+、Node.js 18+；渲染 BDF 与分享图另需 Pillow。

```sh
python3 scripts/workspace.py build
python3 scripts/workspace.py check
python3 scripts/workspace.py research-status
python3 scripts/workspace.py research-status --id gnu_unifont_16
```

`build` 从 `data/catalog.json` 同步目录 JS、首页、资料页、sitemap 与统计。`check` 运行静态和逻辑检查。界面修改另在浏览器核对桌面／手机、键盘、弹窗、收藏、对比及外链。

## 编辑入口

- `data/catalog.json`：目录单源。
- `index.html`：导航与说明，生成标记区由脚本维护。
- `app.js`、`styles.css`：交互与样式。
- `scripts/generate_static.py`：静态模板与正式站点 BASE。
- `assets/specimens/`：固定字样 PNG。

先检查已有改动。保留稳定 ID、像素、字宽、bearing、缺字及来源。

## 元数据

- 普通条目按字符框高筛选，ppem、设计尺寸和墨迹另记。
- `reference` 为资料图，未实测字框保持空值，适屏显示。
- `variableGrid:true` 为不定字框原生格点，保留整数倍率，`designEmGrid` 记录设计单位。
- 全角英数标 `asciiOrigin=fullwidth-native`；无普通 ASCII 标 `absent`。
- 汉仪按 `han-design-grid` 记录设计字高；PSA按 `han-ink-grid` 记录有效字面，同时保留存储框。

## BDF 渲染

研究输入放在被忽略的 `local-research/`。查看输入覆盖表后，选取对应编码：

```sh
python3 scripts/workspace.py inspect-bdf --font local-research/sources/bitmap_survey/linux/sources/unifont.bdf.gz
python3 scripts/workspace.py render-bdf --font local-research/sources/bitmap_survey/linux/sources/unifont.bdf.gz --encoding unicode --text "视野无限广，窗外有蓝天。" --output local-research/generated/unifont-new.png
```

支持 BDF／gzip BDF，编码可选 Unicode、GB2312、Big5。输出 PNG 和 JSON 报告，记录 SHA、尺寸、样文与缺字。其他格式使用相应解析工具。

核对输入、PNG与报告后更新现有条目：

```sh
python3 scripts/workspace.py apply-preview --id gnu_unifont_16 --report local-research/generated/unifont-new.json --reviewed-source-and-glyphs
python3 scripts/workspace.py build
python3 scripts/workspace.py check
```

`apply-preview` 先在 `local-research/before-apply/` 备份原行与图片，再同步样文、尺寸和校验值。来源、许可和说明需单独复核。移除条目时，先审阅并整理旧生成页。

## 设备输入

- [四通 MS-2401H](stone-ms2401h.md)：四套32点压缩汉字，校验BIOS和CA1／CA2／CA3后导出。

- [字体获取与导出](font-export.md)：各类输入、适用工具及尚未整理的处理方法。
- [Panasonic FS-UV1 / FS-A1F](panasonic-fs-uv1.md)：16点ROM导出Unicode BDF。

- [NC1020](nc1020.md)：镜像转换为 BDF。
- [Casio Ex-word](casio-exword.md)：CJF转换为 BDF。
- PSA：`python3 scripts/render_psa_specimens.py --firmware local-research/psa-c-screen/read1.bin`，需要已核验私有输入与 Pillow；保留14×14／16×17存储框。

## 发布

只提交核查过的文件集合。原字体、ROM、研究输入和缓存留在 `local-research/`。发布前检查 `git status`、`git ls-files` 和部署列表；旧资料包的覆盖范围按对应版本记录。详见[部署说明](deployment.md)。

- [Sharp X68000 16点获取与导出](sharp-x68000.md)：原生JIS字模、字符映射与ANK边界。

- [IBM PC DOS 中文24点](ibm-pcdos.md)：校验指定FNT，离线导出7444个标准GB2312字符及未编码IBM扩展。

- [Nokia DCT3 1999](nokia-dct3.md)：静态解出9385个原Unicode码位，含9004个原生11×12汉字，保留西文与度量字段。


- [FM Towns F20 20点](fmtowns-f20.md)：JIS原生汉字及ANK样图，导出边界分别记录。
- [Solaris 中易宋体五个字号](solaris-gbk.md)：12／14／16／20／24点原生PCF与Unicode／原码导出。

## 最近收录排序

“最近收录”表示本站收录批次，不是字体发行年代。`data/collection-history.json`按已核发布清单从旧到新列批次，`build`生成浏览器版`collection-history.js`。本次13个新条目同批，不能直接把FM较早预留的sourceIndex当作较早上线。

批次从新到旧；同批按有效数字sourceIndex倒序，再以名称／ID稳定排序。未记录批次的早期资料沿用来源编号；编号缺失、非数字或非有限值置后。不补造精确时间。新增条目应登记已核批次；不改变默认推荐、原字源行、收藏或其他筛选规则。

## 文曲星 PC505 14×15

[提取方法与边界](wqx-pc505.md)。仅接受已校验的原厂仿真器obj，导出7445个GB映射字符和95个可打印ASCII；原生汉字14×15，不能裁为14×14。共同基线和advance为导出约定，原始输入并非已证实的实机dump。公开目录只提供固定样图和本地提取脚本，不附完整字库。

- [MStar 电视/DVB 简体18点](mstar-18.md)：18×18存储、最大字面14×14；完整GB2312与原生ASCII，附离线导出方法。


## 三国志Ⅴ DOS 固定预览

[来源、映射与重绘方法](san5-dos.md)。`scripts/render_san5_specimen.py`仅接受精确SHA的本地ZIKU.16P，重绘已核两行PNG，不导出完整字体或候选映射。可用`SAN5_SOURCE=本地输入路径 python3 tests/san5.test.py`运行私有源像素核对；未提供输入时不会声称已通过源文件验证。


- [Windows 3.2 CWIN30](windows32-cwin30.md)：固定SHA安装盘存档、原生字框与ASCII、标准GB2312映射及无字模离线导出方法。


- [中国版PS2 24×24](ps2-china.md)：固定SHA完整ROM2、同ROM西文、已核GB2312/GBK映射及存储框导出边界。


- [Sunplus SPHE8202L 简体两款](sunplus-sphe8202l.md)：12×12重复不新增，16×16／20×24原GB2312槽标准Unicode解释、无半角ASCII、源像素独立审计与本地导出边界。


- [Samsung SGH-R208 16×16](samsung-r208.md)：固件原汉字、同源8×16英数及逗号映射，独立源像素核验与本地导出边界。

- [HP-UX繁体宋体](hpux-sung.md)：24／34／42点及同源ASCII固定样文重绘；设置 `HPUX_PCF_DIR` 可在完整检查中运行精确源回归。

- [HP-UX打印宋体40点](hpux-song.md)：固定中文样文重绘；设置 `HPUX_SONG_PCF` 运行精确源回归。

- [IBM AIX / ISAS繁体宋体24点字面](aix-isas-cns.md)：保留26×27存储与原Unicode编码；设置 `AIX_CNS_PCF_DIR` 运行三份精确源的固定样图回归。

- [P908与Nokia 9210C](phone-gdr.md)：SHA锁定的PD1/SFX/PPM/GDR静态输入、原生度量两行样图。设置 `P908_GDR` 与 `NOKIA9210C_GDR` 可运行精确源重绘回归。

- [P802小号](p802.md)：严格SHA的ZIP/PD2/GDR静态重绘；设置 `P802_GDR`、`P802_PD2`、`P802_ZIP` 可运行私有源与容器链回归。

- [Alcatel OT-715](alcatel-ot715.md)：SHA锁定固件与固定四行样图重绘，实机字进未核。

- [MS Ming 14×14](ms-ming14.md)：SHA锁定TTF内原生位图固定两行重绘，不补ASCII。

- [Sony PSP 中文BWFont 16×18](psp-bwfont.md)：SHA锁定的本地BWFont与intraFont映射源码，只重绘固定两行；设置 `PSP_BWFONT_SOURCE`、`PSP_MAPPING_SOURCE` 可运行源像素回归。

- [Olympus m:robe MR-100 12×12](mrobe-mr100.md)：SHA锁定本地FNT，只重绘固定三行；设置 `MROBE_MR100_SOURCE` 可运行原源与独立Pillow像素回归。

- [Samsung YP-T6 14×16](samsung-ypt6.md)：SHA锁定的本地resource.bin，仅固定三行；设置 `SAMSUNG_YPT6_SOURCE` 运行源像素回归。

- [SC_Song 13×13与外补Arial](sc-song13.md)：双SHA锁定本地TTF/GDR的固定三行重绘。设置 `SC_SONG13_SOURCE` 与 `SC_SONG13_ARIAL_SOURCE` 运行源像素回归；未提供时明确跳过私有源验证。

- [MS Song 14×14与外补Arial13](ms-song14.md)：双SHA锁定本地TTF/GDR，仅固定简体及英数两行；设置 `MS_SONG14_SOURCE` 与 `MS_SONG14_ARIAL_SOURCE` 运行源像素回归。原层没有ASCII，外补不计为原生覆盖。

- [Siemens Xelibri 2/4 原生14×14](siemens-xelibri14.md)：SHA和大小锁定本地SW511 CLA，仅重绘固定简繁与同层ASCII三行；设置 `XELIBRI14_SOURCE` 运行源像素及安全路径回归。未提供原源时明确跳过，不把私有研究输入纳入发布。
