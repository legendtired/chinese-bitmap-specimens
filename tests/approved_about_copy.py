"""Approved explanatory copy, shared by regression tests only."""

README_ADDITION = """## 项目缘起

中文点阵字体的资料年代久远，散落在旧网站、论坛、软件和设备中。随着链接失效、内容向移动平台迁移，以及 AI 生成内容增多，原始资料越来越难寻找，有价值的信息也更难筛选。

这个项目希望把分散的字样和资料整理起来，记录来源与获取线索，方便查阅、比较和研究。

## 收录原则

- 收录中文点阵字样，包括历史字库、系统与设备字体，以及现代像素字体。
- 以原始位图或可核验的像素网格为依据，不收录普通矢量取模或简单放大得到的重复字样。
- 注重字形差异与代表性，重复或高度近似的版本择取代表，并保留相关来源。
- 保留原有像素、字宽和缺字情况，注明来源、尺寸、字符覆盖及许可线索。

"""

INDEX_ADDITION = '''<section class="explanation-section"><h3>项目缘起</h3><p>中文点阵字体的资料年代久远，散落在旧网站、论坛、软件和设备中。随着链接失效、内容向移动平台迁移，以及 AI 生成内容增多，原始资料越来越难寻找，有价值的信息也更难筛选。</p><p>这个项目希望把分散的字样和资料整理起来，记录来源与获取线索，方便查阅、比较和研究。</p></section>
<section class="explanation-section"><h3>收录原则</h3><ul>
<li>收录中文点阵字样，包括历史字库、系统与设备字体，以及现代像素字体。</li>
<li>以原始位图或可核验的像素网格为依据，不收录普通矢量取模或简单放大得到的重复字样。</li>
<li>注重字形差异与代表性，重复或高度近似的版本择取代表，并保留相关来源。</li>
<li>保留原有像素、字宽和缺字情况，注明来源、尺寸、字符覆盖及许可线索。</li>
</ul></section>
'''


def before_about_copy(html):
    """Remove only the exact approved addition for the older naming audit."""
    assert html.count(INDEX_ADDITION) == 1
    return html.replace(INDEX_ADDITION, '', 1)
