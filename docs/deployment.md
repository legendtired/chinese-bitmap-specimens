# 本地浏览与部署

网站是资料档案的浏览入口，不需要数据库、构建工具、CDN 或应用服务器。

## 本地浏览

保留目录结构，直接打开 index.html。目录由 data/catalog.js 作为普通脚本加载，无须 fetch，支持 file://。也可使用常规静态文件服务器。

收藏保存在当前浏览器 localStorage，不上传。换域名、浏览器、设备或清除站点数据不会自动迁移；file:// 的存储行为由浏览器决定。

## GitHub Pages

项目仓库：https://github.com/legendtired/chinese-bitmap-specimens

目标地址：https://legendtired.github.io/chinese-bitmap-specimens/

首次上传文件并启用 Pages 后方可访问该站点。本文不代表已经部署。

1. 将目录内容放到仓库根目录，确保 index.html、assets、data 和 .nojekyll 同级；不要只上传 ZIP 文件，也不要多套一层文件夹。
2. 在仓库 Settings → Pages 中选择从分支部署，选择实际存放文件的分支与根目录。
3. 等待 GitHub 显示部署完成后，打开实际站点，核对图片、筛选、详情、收藏、对比、手机布局和来源链接。

应用资源采用相对路径，兼容仓库子路径。仓库不含自动发布脚本或账号凭据。发布前应检查公开文件的权利和分享范围。

## 检查

```sh
node --check app.js
node tests/filters.test.cjs
node tests/priority.test.cjs
node tests/state.test.cjs
node tests/curation.test.cjs
python tests/assets.test.py
python tests/html.test.py
python tests/controls.test.py
python tests/navigation.test.py
```

静态与逻辑检查不等于真实浏览器验收。可选 browser.test.cjs 和 browser-state.test.cjs 需要另行具备 Playwright/Chromium。建议在桌面和手机宽度分别核对键盘操作、滚动、整数倍显示、弹窗固定标题与外链。

## 维护结构

- index.html：入口、说明与对话框结构。
- app.js / styles.css：浏览行为与样式。
- data/catalog.json / catalog.js：同一目录的结构化和浏览器加载版本。
- assets/specimens：固定 PNG 字样，不包含原始字库。
- docs、CONTRIBUTING.md：研究与贡献文档。
- third_party：第三方组件来源与许可。

## 静态资料页与搜索可见性

首页包含预先生成的完整字样目录，不依赖 JavaScript 才能读取。每项在 fonts/ 下有独立 HTML 资料页，可直接引用；JavaScript 只增强筛选、收藏、比较与弹窗。普通点击「详情」仍打开弹窗，修饰键或新标签打开则可访问独立页面。

修改目录后，在项目根目录运行：

```sh
python scripts/generate_static.py
python tests/seo.test.py
```

生成器只读取 data/catalog.json，复用 app.js 的排序逻辑，需要 Python 3 与 Node.js。它同步 catalog.js、首页静态目录、155份资料页及 sitemap.xml。页面以相对路径引用资源，兼容 file:// 和 GitHub Pages 仓库子路径。生成目录中若有不在当前数据内的旧页面，脚本会停止并要求人工审阅，不静默删除文件。

分享图 assets/share.png 由现有真实字标和样图进行最近邻拼合，不使用新字体模拟字形。可选重建脚本 scripts/generate_share_image.py 需要 Pillow；网站本身不依赖 Pillow，也不依赖运行生成器。

canonical、Open Graph 与 sitemap 使用项目的正式 Pages 地址；更换域名时，应同步修改生成器中的 BASE 并重新生成。sitemap 不编造更新时间。项目子目录中的 robots.txt 不能替代域名根目录的爬虫控制，因此本项目没有添加这种文件。

预生成 HTML、独立资料页和结构化元数据有助于访问与引用，但不保证搜索引擎收录、排名或分享预览及时刷新。首次上传后仍须启用 Pages 并核对实际地址。
