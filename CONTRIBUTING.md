# 贡献指南

通过 [Issue](https://github.com/legendtired/chinese-bitmap-specimens/issues) 提供线索或勘误，通过 [PR](https://github.com/legendtired/chinese-bitmap-specimens/pulls) 提交修改。

## 提供线索

尽量附上名称、作者／机构、版本、来源页面、点阵尺寸、字符范围和许可出处。重复字样请注明比较的文字、尺寸和结果；待核信息单独标记。

## 提交字样

- 保留原像素、字宽和缺字，不借其他字体补字。
- 编辑 `data/catalog.json`，保留稳定 ID、PNG 尺寸和校验值。
- 参考图注明原图、裁切范围和已知尺寸。
- 发布内容限固定预览、来源说明及工具；未经授权的字体、ROM、固件和私人文件不上传。

提交前运行：

```sh
python3 scripts/workspace.py build
python3 scripts/workspace.py check
```

界面改动另做浏览器检查。详见[开发说明](docs/DEVELOPMENT.md)。
