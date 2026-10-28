# 本地协作指南

## 项目定位

本仓库是中文点阵字形的收集、展示与研究档案。网站是资料浏览入口，不是项目全部内容。面向访客的说明使用中文，记录可核验事实和不确定性，不以收录数量为目标。

开始修改前阅读 README.md、docs/PROJECT_STATE.md、docs/DEVELOPMENT.md，按任务需要查看 docs/methodology.md、CONTRIBUTING.md。先检查 git status 和用户已有改动，不覆盖无关编辑。

## 当前架构

静态 HTML/CSS/原生 JavaScript，无构建框架、数据库、CDN或运行时服务器依赖。首页及 fonts/ 资料页已预生成，支持直接打开 index.html；JavaScript 增强筛选、收藏、对比与详情弹窗。

- 目录单源：data/catalog.json。
- 界面：index.html 的非生成区、styles.css、app.js。
- 生成器：scripts/generate_static.py，同步 catalog.js、首页标记区、fonts/*.html、sitemap.xml。
- 固定预览：assets/specimens/*.png；sampleKind=reference的官方截图/标准图/外字档案与原生字样分层。
- 统计：scripts/update_summary.py，build会自动刷新，参考图/全角行/原库无ASCII不算ASCII全覆盖。
- v16/v17边界与基线校验：data/release-v16.json、data/release-v17.json、tests/release.test.py、tests/release17.test.py；不为了过测试擅自修改已确认收录范围。
- 本地研究输入：local-research/，默认不附带，只有另行提供资料包并放入根目录时存在，且不进入 Git。

不要手改 catalog.js、首页 STATIC_CATALOG 标记区或 fonts/ 生成页；修改目录或生成模板后重新生成。字体来源 URL 与项目仓库地址是两种信息，不做全局错误替换。

## 已确认的设计与交互

保持白底、常规系统 UI 字体、轻分隔线和克制的留白；不添加大灰底圆角卡片或报刊式装饰。顶部字标保留文泉驿16点阵原图，每个像素2×3，192×48，不平滑拉伸。

顶部顺序：收藏、仓库（浅灰胶囊）、说明（黑底白字胶囊与 Lucide book-open）。说明集中在白底分节弹窗，页脚仅短句。弹窗标题与关闭按钮固定，正文单独滚动。

四组筛选：字高是紧凑宫格单选；其他组同组多选为或、组间为且。推荐排序保留具体条目权重。字形比名称醒目，名称不过重。原生字样保留真实尺寸，1×/整数倍显示，不归一化不同字号。reference资料图必须适屏展示，不能启用原生整数倍率或把PNG像素当字框；原格未实测时width/height/cellWidth/cellHeight为null，字高筛选归“未核定”。

点击字样打开详情，键盘 Enter/Space 可用，拖动滚动不误触。详情链接支持普通点击弹窗及修饰键新页。收藏只在 localStorage，保留旧ID映射；对比2–4项，不能擅自改变或丢弃用户收藏逻辑。

## 字体和研究约束

- 不将普通矢量字体任意取模后当作原生点阵，也不通过放大制造新字号。已收参考资料必须保持reference标签，不因用户允许展示就升级为原生证据。
- 当前199条目包括198原生／设计格点/来源限定样张、1资料图，不是199套独立完整字体。v17之后移除蒙纳方／圆点阵、汉仪像素力量、汉仪像素入侵、方正基础像素、点阵冯及48点阵永字标准图样，未经明确要求不得提交或推送。/efont/ Unicode 全系已按用户要求移除，不得重新引入。未获批准的研究候选不能自动加入；多巴胺像素体不在收录范围。
- 保留原生像素、字宽与 bearing，不补画、不借其他字体填缺字。简繁使用实际对应码位。
- 区分字符框、墨迹、ppem；缺字与覆盖按具体位图层记录，不能从位图缺ASCII推断整文件没有西文。
- 样文相同不代表完整字库相同。近似项不无证据合并，已合并项保留来源与许可差异。
- 只展示固定预览，不公开完整字体、ROM、固件、字模数组或来源不明的子集。
- 历史脚本是研究参考，不保证路径、样文或提取规则适用于当前目录。先检查覆盖报告，再声称可以重建。
- 不把猜测写成结论，不把第三方镜像视为授权。不要擅自给所有字体或全仓库套 MIT 等统一许可。

## 修改与验证流程

1. 确认任务是界面、资料文案、目录或样图变更，限定影响范围。
2. 修改单源或模板；新样图先输出到 local-research/generated/，核实字形、尺寸、缺字、来源、许可与SHA后才按明确任务纳入固定预览。
3. 运行 python scripts/workspace.py build。
4. 运行 python scripts/workspace.py check；涉及截图或交互时另做真实浏览器验收。
5. 检查 git diff 与 git status，报告修改内容、验证范围和未完成事项。静态测试不能冒充浏览器视觉通过。

本地 BDF 诊断与渲染入口见 docs/DEVELOPMENT.md。该入口直接读取原像素，不保证支持全部历史编码和设备格式；失败时报告原因，不能自动改用系统字体。

## 公开边界

未经明确要求，不创建远端仓库、不推送、不发布 Pages、不修改账号或权限。仓库：https://github.com/legendtired/chinese-bitmap-specimens；Pages：https://legendtired.github.io/chinese-bitmap-specimens/。

local-research/ 包含仅本地使用的第三方研究输入，始终保持 ignored。注意：.gitignore 不能阻止网页手动上传，也不能使已被Git跟踪的文件自动消失。发布和CI必须使用经过核查的干净文件集合，绝不能上传完整本地工作区ZIP。提交前检查 git ls-files 与 git status；有原始字库混入时停止并说明，不擅自清理用户历史。

## v16 本地输入边界

本次新增 25 项原生字样与 11 项参考资料图。没有研究资料包也能修改界面、目录、构建和检查；重绘新增原生字样仍需对应的本地输入及已核验解析方法。参考图不是可重新生成任意文字的字体。旧 v15 独立资料包没有覆盖本次新增输入，不应据此宣称全部 191 项可以重生。新资料仅在另行明确需要时整理，默认发布包不包含它们。

公开来源链接只指向项目介绍、文档或可浏览的来源页面，不提供字体、ROM 或压缩包直链。GitHub blob 浏览页可以保留，但 raw/download 查询及直接文件 CDN 不可。私有研究下载记录不混入公开元数据；修改后运行 public_links.test.py 和完整检查。

## v17 设计与输入约束

variableGrid:true 是实际原生格点但不定字框，不是 reference。width/height/cellWidth/cellHeight 保持 null，designEmGrid 仅是设计单位；独立“不定字框”筛选、整数倍率和 pixelated 显示都要保留。新条目默认 priority=0，既定首页权重不改。

新增候选去重必须同时对照当前目录与已移除项，不能以改名字或改厂商重新引入已删字模。MS6459 是2013文档17字重建而非90年代ROM；DEC与CCDB的真实bitmap不自动证明全部手调。旧资料包不能声称覆盖全部现有条目；本地新资料仍独立、忽略且不随默认包交付。

汉仪9/11/13/行楷15用designHeight与heightBasis=han-design-grid按汉字设计字高筛选，固定字符框字段保持null；gridReconstruction标明正交轮廓还原，不是EBDT。renderOmitted与原库缺字分开，11px冒号有字形但未绘制，不伪造、不移动内部两点凑格。原8项推荐权重不改，汉仪13与行楷15按用户要求置10/9。

没有有效收藏时隐藏右上角收藏入口，首次收藏后显示。清空或取消最后一个收藏后应有可退出空态及可见焦点目标，卡片收藏按钮始终保留。初始HTML隐藏入口，避免载入闪现。

PSA条目的heightBasis=han-ink-grid按有效中文12／14点筛选，但cell保留14×14／16×17真实存储框，不能裁去边距或改成汉仪轮廓还原。sourceType=physical-extraction允许sourceUrl=null并显示文字来源，Issue仅联系试用，不冒充字体来源链接。原固件、完整字模、车辆识别信息不得公开。新增条目priority=0，原推荐不变。
