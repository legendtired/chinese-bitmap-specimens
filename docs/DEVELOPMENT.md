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
