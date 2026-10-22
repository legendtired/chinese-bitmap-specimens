#!/usr/bin/env python3
"""Build crawler-readable pages from catalog.json. Requires Python 3 and Node.js; no network."""
from pathlib import Path
import json,re,html,subprocess
from urllib.parse import quote,urlsplit
ROOT=Path(__file__).resolve().parents[1]
BASE='https://legendtired.github.io/chinese-bitmap-specimens/'
E=lambda v:html.escape(str(v),quote=True)
rows=json.loads((ROOT/'data/catalog.json').read_text())
assert len({r['id'] for r in rows})==len(rows)
for r in rows:assert re.fullmatch(r'[A-Za-z0-9_-]+',r['id']),r['id']
# Reuse the application's comparator so first paint and JS enhancement have identical order.
ordered=json.loads(subprocess.check_output(['node','-e',"const a=require('./app.js');const r=require('./data/catalog.json');process.stdout.write(JSON.stringify(a.filterCatalog(r,{})));"],cwd=ROOT,text=True))
(ROOT/'data/catalog.js').write_text('window.FONT_CATALOG = '+json.dumps(rows,ensure_ascii=False,indent=2)+';\n')
def fmt(v):
 if isinstance(v,list):return '、'.join(map(fmt,v))
 if isinstance(v,dict):return '；'.join(f'{k}：{fmt(x)}' for k,x in v.items())
 return str(v) if v is not None else ''
def safe(u):return isinstance(u,str) and urlsplit(u).scheme in ('http','https')
def link(u,label):return f'<a href="{E(u)}" target="_blank" rel="noopener noreferrer">{E(label)}</a>' if safe(u) else E(label)
def missing(r):
 parts=[]
 for key,label in [('hanMissing','中文缺字'),('asciiMissing','拉丁字符／符号缺字')]:
  if r.get(key):parts.append(label+'：'+'、'.join('空格' if c==' ' else c for c in r[key]))
 if not parts:return ''
 tail='拉丁字符行全部缺失，样图省略该空白行；不借用其他字体补齐。' if 'ascii' in r.get('omittedEmptyLines',[]) else '对应位置留空，不借用其他字体补齐。'
 return '；'.join(parts)+'。'+tail
def picture(r,scale=1,prefix='',linked=False):
 image=f'<img class="specimen-image" src="{prefix}{E(r["specimen"])}" width="{r["specimenWidth"]*scale}" height="{r["specimenHeight"]*scale}" alt="{E(r["name"]+"："+r["text"])}" loading="lazy" decoding="async">'
 return f'<a class="static-specimen-link" href="fonts/{E(r["id"])}.html" aria-label="查看{E(r["name"])}资料">{image}</a>' if linked else image
external='<svg class="icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M7 17 17 7M7 7h10v10"/></svg>'
def article(r):
 return f'''<article class="specimen" data-row-id="{E(r['id'])}"><div class="specimen-header"><h2>{E(r['name'])}</h2><span class="specimen-meta">{r['width']}×{r['height']} · {E(fmt(r['scripts']))}</span><div class="row-actions"><a class="detail-button" href="fonts/{E(r['id'])}.html">详情{external}</a></div></div><div class="sample-panel"><div class="sample-enlarged"><div class="sample-label">放大观察 · 3×</div><div class="image-scroll" tabindex="0">{picture(r,3,linked=True)}</div></div><div class="sample-native"><div class="sample-label">原尺寸 · 1×</div><div class="image-scroll" tabindex="0">{picture(r,linked=True)}</div></div></div>{'<p class="missing-hint">'+E(missing(r))+'</p>' if missing(r) else ''}</article>'''
def meta(title,desc,url,kind='website'):
 return f'''<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{E(url)}">
<meta property="og:type" content="{kind}"><meta property="og:locale" content="zh_CN"><meta property="og:site_name" content="中文点阵字样"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{E(url)}"><meta property="og:image" content="{BASE}assets/share.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="中文点阵字样：实际点阵字标与样文字形">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}"><meta name="twitter:image" content="{BASE}assets/share.png">'''
def dlrow(label,value,raw=False):return '' if value is None or value=='' else f'<dt>{E(label)}</dt><dd>{value if raw else E(fmt(value))}</dd>'
def details(r):
 fields=[('家族',r['family']),('字符框',f"{r.get('cellWidth') or r['width']}×{r.get('cellHeight') or r['height']} px"),('字面／墨迹',f"{r['inkWidth']}×{r['inkHeight']} px" if r.get('inkWidth') and r.get('inkHeight') else None),('字符范围',r['scripts']),('样本文字',r['text']),('拉丁样文',r.get('asciiText')),('覆盖说明',r.get('coverage')),('缺字',missing(r) or '本次样本文字未发现缺字；不代表完整字库覆盖'),('风格',r.get('styles')),('用途',r.get('uses')),('字形来源',r.get('provenance')),('授权状态',r.get('licenseStatus')),('许可说明',r.get('licenseNote')),('说明',r.get('notes'))]
 out='<dl class="detail-list">'+''.join(dlrow(k,v) for k,v in fields)+dlrow('来源',link(r['sourceUrl'],r.get('sourceLabel') or '来源项目'),True)
 ev=r.get('nativeEvidence')
 if ev:
  labels={'summary':'说明','method':'提取方式','bitmap_tables':'内嵌位图表','native_ppem':'原生像素字号','grid_step':'原生网格步长','maximum_grid_error':'最大网格误差'}
  content=''.join(f'<p>{E(labels.get(k,k))}：{E(fmt(v))}</p>' for k,v in ev.items() if k not in ('sourceUrl','sha256')) if isinstance(ev,dict) else E(fmt(ev))
  if isinstance(ev,dict) and safe(ev.get('sourceUrl')):content+=link(ev['sourceUrl'],'查看原生设计来源')
  out+=dlrow('原生证据',content,True)
 out+='</dl>'
 if r.get('relatedSources'):
  out+='<section class="source-section"><h2>相关来源与合并说明</h2>'
  for s in r['relatedSources']:
   out+='<h3>'+E(s['name'])+'</h3>'+''.join('<p>'+E(s[k])+'</p>' for k in ['version','comparison','coverageNote','provenance','licenseNote'] if s.get(k))+link(s.get('sourceUrl'),'查看相关来源')
  out+='</section>'
 return out
folder=ROOT/'fonts';folder.mkdir(exist_ok=True)
expected={r['id']+'.html' for r in rows}
# Generated directory only. Refuse silently deleting any unexpected file.
extra={x.name for x in folder.glob('*.html')}-expected
if extra:raise SystemExit('Unexpected generated pages; review before removal: '+str(sorted(extra)))
for r in rows:
 title=r['name']+'｜中文点阵字样'
 desc=f"{r['name']}字样资料：{r['width']}×{r['height']} 原生尺寸、实际 PNG 预览、字符覆盖、来源与许可线索。"+('来源限定设备 OSD 样张。' if r['sampleKind']=='osd' else '缺字及核验边界按条目记录。')
 url=BASE+'fonts/'+quote(r['id'])+'.html'
 body=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{meta(title,desc,url,'article')}<link rel="stylesheet" href="../styles.css"></head><body class="font-page"><header class="site-header"><a class="wordmark" href="../index.html" aria-label="中文点阵字样首页"><img src="../assets/wordmark.png" width="192" height="48" alt="中文点阵字样"></a><a class="back-link" href="../index.html">返回全部字样</a></header><main class="font-document"><p class="document-eyebrow">字样资料 / {E(r['family'])}</p><h1>{E(r['name'])}</h1><p class="document-intro">{E(r.get('coverage',''))} · {r['width']}×{r['height']} · {E(fmt(r['scripts']))}</p><section class="document-preview" aria-label="实际点阵字样"><p class="sample-label">放大观察 · 3×</p><div class="image-scroll" tabindex="0">{picture(r,3,'../')}</div><p class="sample-label native-label">原尺寸 · 1×</p><div class="image-scroll" tabindex="0">{picture(r,1,'../')}</div>{'<p class="missing-hint">'+E(missing(r))+'</p>' if missing(r) else ''}</section><section class="source-section"><h2>来源与字样信息</h2>{details(r)}</section><p class="license-note">仅展示固定字样，不提供字体文件。预览不授予字体使用许可；样文覆盖不等于完整字库覆盖，实际使用前请核实来源项目的适用授权。</p><p class="document-bottom"><a href="../index.html">返回目录，筛选与对比更多字样</a></p></main><footer class="font-page-footer">中文点阵字样 · 收集、展示与研究</footer></body></html>'''
 (folder/(r['id']+'.html')).write_text(body)
p=ROOT/'index.html';h=p.read_text()
if '<!-- STATIC_CATALOG_START -->' not in h:h=h.replace('<div id="catalog" class="catalog"></div>','<div id="catalog" class="catalog"><!-- STATIC_CATALOG_START --><!-- STATIC_CATALOG_END --></div>')
h=re.sub(r'<!-- STATIC_CATALOG_START -->.*?<!-- STATIC_CATALOG_END -->','<!-- STATIC_CATALOG_START -->\n'+'\n'.join(article(r) for r in ordered)+'\n<!-- STATIC_CATALOG_END -->',h,flags=re.S)
h=re.sub(r'<title>.*?</title>','',h,flags=re.S);h=re.sub(r'<meta name="description"[^>]*>','',h)
# Replace only this script's managed head block.
h=re.sub(r'<!-- GENERATED_SEO_START -->.*?<!-- GENERATED_SEO_END -->','',h,flags=re.S)
structured={'@context':'https://schema.org','@graph':[{'@type':'WebSite','@id':BASE+'#website','url':BASE,'name':'中文点阵字样','inLanguage':'zh-CN'},{'@type':'CollectionPage','@id':BASE+'#catalog','url':BASE,'name':'中文点阵字样目录','isPartOf':{'@id':BASE+'#website'},'description':'收集、展示与研究中文点阵字形的资料档案。','inLanguage':'zh-CN'}]}
block=meta('中文点阵字样｜收集、展示与研究','收集、展示与研究中文点阵字形的资料档案。浏览实际字样，按字高与风格筛选，比较原生像素，追溯字体来源、字符覆盖和核验记录。',BASE)+'<script type="application/ld+json">'+json.dumps(structured,ensure_ascii=False).replace('<','\\u003c')+'</script>'
h=h.replace('</head>','<!-- GENERATED_SEO_START -->'+block+'<!-- GENERATED_SEO_END -->\n</head>')
h=re.sub(r'(<span id="result-count"[^>]*>).*?(</span>)',r'\g<1>'+str(len(rows))+' 个字样'+r'\2',h,count=1)
h=re.sub(r'\n{2,}', '\n', h)
p.write_text(h)
urls=[BASE]+[BASE+'fonts/'+quote(r['id'])+'.html' for r in rows]
(ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join('<url><loc>'+E(u)+'</loc></url>\n' for u in urls)+'</urlset>\n')
print(f'Generated index {len(rows)} rows, {len(rows)} font pages, {len(urls)} sitemap URLs; no invented timestamps.')
