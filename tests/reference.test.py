"""Reference rendering regressions: pure template calls, no build and no browser launch."""
from pathlib import Path
from html.parser import HTMLParser
import importlib.util
import subprocess

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('generate_static_reference_test',ROOT/'scripts/generate_static.py')
generator=importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)

class Document(HTMLParser):
 def __init__(self,source):
  super().__init__();self.tags=[];self.feed(source)
 def handle_starttag(self,tag,attrs):self.tags.append((tag,dict(attrs)))

reference={'id':'test_reference','name':'测试资料 <&>','family':'资料','sampleKind':'reference','referenceType':'官方试字截图','referenceNote':'尚未核定原生字符框；图中尺寸是图片尺寸。','width':None,'height':None,'cellWidth':None,'cellHeight':None,'specimen':'assets/specimens/test_reference.png','specimenWidth':900,'specimenHeight':420,'scripts':['简体'],'styles':['黑体'],'uses':['资料研究'],'text':None,'missing':[],'sourceUrl':'https://example.com/source?a=1&b=2','coverage':'来源图展示的可见字形，非逐字覆盖验证。'}
native={**reference,'id':'test_native','name':'原生字样','sampleKind':'standard','width':12,'height':12,'cellWidth':12,'cellHeight':12,'specimenWidth':120,'specimenHeight':30,'text':'实际字样','coverage':'普通样文'}

for kind in ['官方试字截图','标准图样','历史外字资料']:
 row={**reference,'referenceType':kind}
 card=generator.article(row)
 page=generator.font_page(row)
 for output in [card,page]:
  assert '原始资料图 · '+kind in output
  assert 'None' not in output and 'null' not in output
  assert '原尺寸' not in output and '放大观察' not in output
  assert '1×' not in output and '3×' not in output
  assert '未发现缺字' not in output
  assert '<dt>字符框</dt>' not in output
  assert '测试资料 &lt;&amp;&gt;' in output, 'All source labels remain escaped'
  assert row['referenceNote'] in output
  images=[attrs for tag,attrs in Document(output).tags if tag=='img' and 'specimen-image' in attrs.get('class','')]
  assert len(images)==1
  assert images[0]['width']=='900' and images[0]['height']=='420'
  assert 'reference-image' in images[0]['class']
 assert 'href="fonts/test_reference.html"' in card
 assert 'href="../index.html"' in page
 assert 'href="https://example.com/source?a=1&amp;b=2"' in page
 assert '<dt>资料类型</dt><dd>'+kind+'</dd>' in page
 assert '<dt>核验边界</dt>' in page
 assert generator.REFERENCE_WARNING in page
 assert generator.REFERENCE_COVERAGE in page
 tags=Document(page).tags
 descriptions=[attrs['content'] for tag,attrs in tags if tag=='meta' and attrs.get('name')=='description']
 assert len(descriptions)==1 and kind in descriptions[0]
 assert '原生尺寸' not in descriptions[0] and 'None' not in descriptions[0]
 assert any(tag=='link' and attrs.get('rel')=='canonical' and attrs.get('href')==generator.BASE+'fonts/test_reference.html' for tag,attrs in tags)
 assert any(tag=='meta' and attrs.get('property')=='og:image' and attrs.get('content')==generator.BASE+'assets/share.png' for tag,attrs in tags)

assert generator.picture(reference,4)==generator.picture(reference,1), 'Reference pictures ignore integer zoom'
assert generator.cell_dimensions(reference) is None
assert generator.cell_dimensions({**reference,'cellWidth':12}) is None
assert generator.missing({**reference,'hanMissing':['字'],'asciiMissing':['A']})==''
assert generator.cell_dimensions(native)=='12×12 px'
assert '12×12 原生尺寸' in generator.page_description(native)
for output in [generator.article(native),generator.font_page(native)]:
 assert '原尺寸 · 1×' in output and '放大观察 · 3×' in output
 assert 'reference-image' not in output
 images=[attrs for tag,attrs in Document(output).tags if tag=='img' and 'specimen-image' in attrs.get('class','')]
 assert [(image['width'],image['height']) for image in images]==[('360','90'),('120','30')]
assert '本次样本文字未发现缺字' in generator.details(native)
assert '中文缺字：字' in generator.details({**native,'hanMissing':['字']})
fullwidth={**native,'asciiOrigin':'fullwidth-native','asciiText':'ＡＢ１２'}
assert '<dt>全角英数样文（非ASCII）</dt><dd>ＡＢ１２</dd>' in generator.details(fullwidth)
assert '拉丁样文' not in generator.details({**native,'asciiOrigin':'absent','asciiText':''})
menu={**native,'sampleKind':'osd','sampleLabel':'来源限定设备菜单'}
assert '来源限定设备菜单' in generator.article(menu)
assert '来源限定设备菜单' in generator.details(menu)
assert '来源限定设备菜单' in generator.page_description(menu)
assert 'OSD' not in generator.page_description(menu)
for em,width,height in [(14,137,32),(9,99,25)]:
 variable={**native,'id':f'pixels_han_{em}','name':f'Pixels Han {em}','variableGrid':True,'designEmGrid':em,'width':None,'height':None,'cellWidth':None,'cellHeight':None,'specimenWidth':width,'specimenHeight':height,'notes':f'canvasBounds: 0,0,{width},{height}；glyphAdvances: 7,9,14。'}
 label=f'不定字框 · em {em} 格'
 assert generator.is_variable_grid(variable) and not generator.is_reference(variable)
 assert generator.dimensions(variable)==label
 assert generator.cell_dimensions(variable) is None
 assert label in generator.page_description(variable)
 assert '原生尺寸' not in generator.page_description(variable)
 for output in [generator.article(variable),generator.font_page(variable)]:
  assert label in output
  for invalid in ['None','null','未核定','0×0','9×9','14×14','原始资料图','reference-image','<dt>字符框</dt>']:
   assert invalid not in output,(em,invalid)
  assert '原尺寸 · 1×' in output and '放大观察 · 3×' in output
  assert generator.VARIABLE_GRID_NOTE in output
  images=[attrs for tag,attrs in Document(output).tags if tag=='img' and 'specimen-image' in attrs.get('class','')]
  assert [(image['width'],image['height']) for image in images]==[(str(width*3),str(height*3)),(str(width),str(height))]
 details=generator.details(variable)
 assert '<dt>字框类型</dt><dd>'+label+'</dd>' in details
 assert variable['notes'] in details
 assert generator.REFERENCE_COVERAGE not in details
 assert generator.VARIABLE_GRID_WARNING in generator.preview(variable)
assert not generator.is_variable_grid({**reference,'variableGrid':True})
css=(ROOT/'styles.css').read_text()
assert '.reference-image{max-width:100%;height:auto;image-rendering:auto;mix-blend-mode:normal}' in css
assert '.sample-panel.reference-panel{display:block}' in css
assert '.reference-warning{' in css
# workspace.py discovers every *.test.py; include the synthetic DOM suite without changing its runner.
subprocess.run(['node',str(ROOT/'tests/reference.test.cjs')],cwd=ROOT,check=True)
print('Reference / variable-grid template checks passed: separate source images and true flexible grids, honest em/coverage/SEO, native multipliers, links/OG and responsive styles. No build or browser was run.')
