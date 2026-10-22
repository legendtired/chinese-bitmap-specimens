# 本地开发与资料维护

## 环境

网页运行：现代浏览器即可，不需要 Node、Python、服务器或字体安装。直接打开 index.html；可选 `python -m http.server 8000` 后访问 http://localhost:8000。

维护工具：Python 3.9+、Node.js 18+。本版验证环境为 Python 3.12.14、Node.js 24.19.0；可选图像工具验证使用 Pillow 12.3.0。静态生成与常规检查只使用 Python / Node 标准库；BDF 渲染和分享图生成需要 Pillow，可在虚拟环境安装 `Pillow==12.3.0`。未设置 npm 运行时依赖，也不需要 npm install。

## 立即开始

```sh
python scripts/workspace.py check
python scripts/workspace.py build
python scripts/workspace.py research-status
python scripts/workspace.py research-status --id gnu_unifont_16
```

check 运行静态资源、数据、导航、SEO和核心逻辑检查，不自动启动浏览器。build 从 data/catalog.json 同步 catalog.js、首页静态目录、fonts/ 资料页和 sitemap。每次改目录、资料页模板或静态首页生成逻辑后，都应 build 再 check。

## 改界面

- styles.css：视觉、响应式、弹窗独立滚动。
- app.js：筛选、收藏、比较、详情及图片交互。
- index.html：非生成区的导航和说明内容；不要手改 STATIC_CATALOG 或 GENERATED_SEO 区域。
- scripts/generate_static.py：静态卡片和独立资料页模板、正式站点 BASE。

静态首页和 JS 增强后的列表都要考虑。不要只改一侧。测试通过后，实际浏览器核对桌面与手机、键盘、图片缩放、详情新标签、收藏与对比。可选浏览器脚本依赖 Playwright/Chromium，不属于当前统一入口已执行的验收。

## 本地资料结构

默认交付仅含干净仓库，不附带研究资料。修改界面、编辑目录、build、check和浏览现有字样均不需要这些输入。研究资料仅在明确索要时单独提供；将资料包中的 local-research/ 文件夹放到仓库根目录，无需改动公开源码。先读其 README.md 和 catalog-input-coverage.json：输入存在，不等于能重新生成当前全部字样。历史脚本可能有旧绝对路径、旧样文或联网步骤，只作参考，不直接批量执行。

当前可移植渲染入口支持保存原像素的 BDF／gzip BDF；暂不覆盖 TTF/TTC内嵌位图、PCF、MOT/ROM、NFTR或所有逐字JSON变体。这些材料仍可用于研究，但需要经过对应格式解析与单独验证，不能用矢量fallback代替。

## 从原始 BDF 生成新字样

例子使用本地已映射的 GNU Unifont BDF。先检查实际编码，再渲染；以下命令不会联网，也不会安装字体。

```sh
python scripts/workspace.py inspect-bdf --font local-research/sources/bitmap_survey/linux/sources/unifont.bdf.gz
python scripts/workspace.py render-bdf --font local-research/sources/bitmap_survey/linux/sources/unifont.bdf.gz --encoding unicode --text "视野无限广，窗外有蓝天。\n0123456789 AaBb GgMm !?:+-." --output local-research/generated/unifont-new.png
```

输出 PNG 与同名 JSON 报告。报告记录源文件SHA、尺寸、文本、缺字和提取方法，不包含完整字模数组。渲染读取 BITMAP、DWIDTH、BBX，保留基线与字宽，无抗锯齿、轮廓取模或其他字体补字；缺字按默认字符框透明留空。

`--encoding unicode` 适用于 ISO10646/Unicode BDF。`gb2312` 和 `big5` 使用相应编码的字节值作为BDF编码；不支持把所有旧 GB/JIS 区位编码自动猜成同一种编码，遇到编码不符应停止检查。缺字是报告结果，不是自动换字体的理由。

本版使用现存 GNU Unifont 输入实测了上述完整中文＋ASCII样文，以及包含 U+10FFFF 的缺字案例。此验证只证明该入口和该输入的结果，不代表139项原始输入都已完成移植。

## 审核后更新现有目录项

确认实际源文件、字号、文本、缺字、字宽、版权线索与所选条目对应，检查PNG，不要把不同版本的新图静默冒充旧来源。示例不应在未审阅时直接执行：

```sh
python scripts/workspace.py apply-preview --id gnu_unifont_16 --report local-research/generated/unifont-new.json --reviewed-source-and-glyphs
python scripts/workspace.py build
python scripts/workspace.py check
```

apply-preview 只更新已有ID，先在 local-research/before-apply/ 保存可回退的原行与原PNG，再同步文本、缺字、画布尺寸、SHA、样张类型与统计。若同ID已有备份会停止，防止覆盖历史。来源、许可、原生字号及 notes 不会自动改写，必须复核其是否仍与新样文一致；新源或新字号应另行编辑明确的目录记录。

生成器不会静默删除已不在数据中的旧资料页；有移除项时，应先审阅并可恢复地整理旧生成页面，再运行 build。

## 发布边界

只发布核查过的干净文件集合。local-research/ 及原字体、固件、缓存、压缩包均被 .gitignore 排除，但网页手动上传不读取 .gitignore，已跟踪文件也不会自动解除跟踪。发布前检查 git status、git ls-files 和部署文件列表。完整工作区ZIP只能用于本地，不能上传至仓库或Pages。

具体部署步骤见 deployment.md。维护工具不含 push、发布或账号操作。
