# HP-UX 打印宋体 40点

仅收录经确认的简体 Song40，保留原40×40 PCF像素。未找到匹配的半宽西文，固定样图只显示中文，不从其他字体补字。

## 来源、编码与度量

[HP-UX 11i Version 1，2005年9月原盘存档](https://archive.org/details/hp-ux-11i-version-1-mission-critical-operating-environment-sept-2005)，第1盘 B7994-10044，Asian-PRINTER/PRNTR-SCH-RUN/usr/lib/asx/fonts/chinese-s/song40h.pcf。光盘条目为gzip包装；[源元数据](../data/hpux-song-sources.json)记录偏移、长度和SHA256，不含字模。

原PCF标注HP Song Medium、GB2312.1980-1；版权年份1988、1989、1990、1994不是已证实的首次设计时间。2005年9月为本次介质日期，原生位图存储不证明逐字手绘历史。

- 全部6,763个GB2312汉字均有非空点阵；不是完整GBK。
- 原字框40×40、advance 40、ascent 34、descent 6。固定中文一行，四周4px，PNG为488×48，不裁边、不加字距、不缩放。
- 所选PCF没有普通ASCII；全角英数不是半角ASCII覆盖。未找到匹配配套不等同整个HP-UX系统没有西文字体。
- [独立审计](../data/hpux-song-independent-audit.json)以独立原始位解码与Pillow核对全部7,546字形、12,073,600像素及编码／度量，结果一致。

## 去重边界

[聚合审计](../data/hpux-song-dedup.json)：读取221份历史主BDF，其中211份含可映射非空汉字。40点在同Unicode逐汉字整框及裁白比较中均零精确匹配。另检索当前233条基线的232张非reference PNG，同Unicode样文字形也均无匹配。

样文检索不能替代完整字库比较；先前45项完整来源缺口和映射限制仍存在。撤下资料在可得历史源范围内参与核对，但未恢复原图的撤下项不能做PNG补查。未映射槽不算不同字形，零精确重合不证明原创或不存在历史衍生关系。

32点与DEC Songti34的6,726／6,763个汉字裁白相同，属近重复，不收录；16×18与北京16、24×24与ISAS宋24也为高重复，不随本次加入。

## 离线重绘固定样文

自行取得并确认有权使用匹配SHA的解压PCF，安装Pillow后运行：

```sh
python3 scripts/render_hpux_song.py /本地/song40h.pcf /本地/尚不存在的输出目录
```

脚本先核对精确SHA，仅输出这张固定中文PNG；不联网、不安装、不导出完整字体或字模数组。错误输入或已有输出目录会拒绝。私有输入回归可运行：

```sh
HPUX_SONG_PCF=/本地/song40h.pcf python3 tests/hpux-song.test.py
```

## 公开与权利边界

公开内容仅固定样图、源元数据、聚合审计及无字模脚本。不附PCF、ROM、ISO、完整BDF或字模数组。HP版权仍适用，第三方存档不是开放再分发或商用授权；本仓库不授予相关字体权利。
