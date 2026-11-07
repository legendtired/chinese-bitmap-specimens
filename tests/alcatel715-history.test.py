"""Ensure historical reconstruction exactly matches the approved 239-row baseline.

Hashes were captured from commit 61c981435e86b0d97656712f2867f8a3d35ea5f7.
No runtime Git history or private inputs are needed.
"""
from approved_alcatel715 import before_alcatel_file_sha

BASELINE = {'data/catalog.json': '9a37258b421c3d219acfd7a3063c1e4f9d904b949952fbc534d406a18db3fd72', 'data/catalog.js': 'f865047282a9253387909cc6d3f215853fe711c0907a966ec0e3f8b7a17bc81c', 'data/collection-history.json': '5baea43bab71326c4e2491ff40ac8555f4317e67ac949f82e90b9eed8314178b', 'data/collection-history.js': '0452a8463de12ea97f773cdbdcee0551524c5ad934ffffccc6ebcf79ce1f30c6', 'data/summary.json': 'c5c1b1a97af2f594654ab9cd099b81bf7bbd8f22e01f7856aea710d5d7bf2439', 'index.html': '96314f665cb7e41f8eb020aa06e7bee5c59d5c3f3581bbe3410836d21858c230', 'sitemap.xml': 'ed4841e9cfea656c22c72f8b0e7f9f480592e7323ebd0ee0d0629f2011c60249'}
for path, expected in BASELINE.items():
    assert before_alcatel_file_sha(path) == expected, path
print('OT-715/MS Ming historical audit: exact prior catalog, JS, collection history, summary, index and sitemap reconstructed.')
