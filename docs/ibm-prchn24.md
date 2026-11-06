## IBM PC DOS 原配公共半角

PRCHN24.FNT 是同一简体中文 PC DOS 2000 发行包 Disk01.img 中的独立半角文件。FONT.EXE 同时包含 PRCHN24.FNT、SBCS1224 和 DBCS2424 标识。它是系统公共半角，不是楷体、黑体、仿宋分别设计的三款西文。

- 原生 12×24；每字连续 288 bit，共 256 槽、9216 字节。
- 本工具仅导出已核对的 U+0020–U+007E 共95个 ASCII 槽：空格为空白，其余94个非空；英文字母和数字齐全。0x5C 为反斜线。原始波浪号形状较高，保留原样。
- 可选与已有三款24点中文组合：中文24像素宽、英数12像素宽。现有中文像素及映射不改；基线24/0沿用现有导出约定，并非恢复的历史排版参数。
- 0x00–1F、0x7F–FF 未作 Unicode 映射。不推断 CP437。

输出路径必须不存在；脚本不覆盖已有文件。

用法：

    python scripts/ibm_prchn24_to_bdf.py Disk01.img local-research/ibm-prchn24-ascii.bdf
    python scripts/ibm_prchn24_to_bdf.py PRCHN24.FNT local-research/ibm-kai-combined.bdf --cjk-bdf local-research/prckt24.bdf

来源：https://winworldpc.com/product/pc-dos/2000
原包 SHA256：26f42bdef79f795d8d42ec6fbcd87b5214cf370540eb454c545d878a2779fc71
PRCHN24.FNT SHA256：202aea3f45004ac89d6ceb1a81c33b2ac252fc1f39baf3fe6b3d34959d86c740

发布仅包含转换脚本和文档；原包、源字体和完整导出文件保留本地，不随仓库分发。
