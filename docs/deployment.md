# 本地浏览与部署

## 浏览

保留目录结构，直接打开 `index.html`，或运行 `python3 -m http.server 8000`。网站为静态 HTML／CSS／JavaScript，目录由普通脚本加载，支持 `file://`。

收藏保存在当前浏览器的 `localStorage`；更换域名或清除数据后需重新收藏。

## 地址

- 网站：https://fonts.resmx.com/
- 仓库：https://github.com/legendtired/chinese-bitmap-specimens
- GitHub Pages：https://legendtired.github.io/chinese-bitmap-specimens/

## 构建与检查

```sh
python3 scripts/workspace.py build
python3 scripts/workspace.py check
```

生成器同步目录 JS、首页、`fonts/`、sitemap 和统计。每项有独立资料页；JavaScript增强筛选、收藏、对比和弹窗。

资源使用相对路径。canonical、Open Graph 与 sitemap 使用生成器的 `BASE`；部署到其他域名时，在部署副本中同步地址。

## GitHub Pages 部署

1. 将公开文件放在仓库根目录，保留 `.nojekyll`。
2. Settings → Pages 选择对应分支与根目录。
3. 部署完成后检查页面、图片、筛选、详情、收藏、对比及手机布局。

仅上传公开文件，不上传整个研究工作区。检查 `git status` 与 `git ls-files`，排除原字库、ROM和私有输入。

## 浏览器验收

可选 `tests/browser.test.cjs` 和 `tests/browser-state.test.cjs` 使用 Playwright／Chromium。检查键盘导航、缩放、滚动、弹窗关闭与返回、收藏增删和对比操作。

分享图由真实字标及字样拼合，重建脚本为 `scripts/generate_share_image.py`，需要 Pillow。
