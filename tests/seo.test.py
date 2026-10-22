from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json,subprocess,xml.etree.ElementTree as ET
r=Path(__file__).resolve().parents[1];rows=json.loads((r/'data/catalog.json').read_text());base='https://legendtired.github.io/chinese-bitmap-specimens/'
class Doc(HTMLParser):
 def __init__(self,text):super().__init__();self.tags=[];self.title='';self.inTitle=False;self.feed(text)
 def handle_starttag(self,t,a):self.tags.append((t,dict(a)));self.inTitle=self.inTitle or t=='title'
 def handle_endtag(self,t):
  if t=='title':self.inTitle=False
 def handle_data(self,s):
  if self.inTitle:self.title+=s
seenTitles=set();seenDescriptions=set();canonicals=set();expected={base}|{base+'fonts/'+x['id']+'.html' for x in rows}
for file in [r/'index.html']+list((r/'fonts').glob('*.html')):
 d=Doc(file.read_text());title=d.title;assert title and title not in seenTitles;seenTitles.add(title)
 desc=[a['content'] for t,a in d.tags if t=='meta' and a.get('name')=='description'];assert len(desc)==1 and desc[0] not in seenDescriptions;seenDescriptions.add(desc[0])
 canon=[a['href'] for t,a in d.tags if t=='link' and a.get('rel')=='canonical'];assert len(canon)==1 and canon[0] in expected and canon[0] not in canonicals;canonicals.add(canon[0])
 assert len([1 for t,a in d.tags if t=='h1'])==1
 for t,a in d.tags:
  for key in ('href','src'):
   u=a.get(key,'');parts=urlsplit(u)
   if u and not parts.scheme and not u.startswith('#'):
    path=(file.parent/unquote(parts.path)).resolve();assert path.exists(),(file,u)
    assert path.is_relative_to(r),(file,u)
 # Font pages have no JS requirement, use real image and source metadata.
 if file.parent.name=='fonts':
  row=next(x for x in rows if x['id']==file.stem);text=file.read_text()
  for field in ('name','specimen','sourceUrl'):assert str(row[field]).replace('&','&amp;') in text,(file,field)
  assert '../index.html' in text
idx=Doc((r/'index.html').read_text());ids=[a['data-row-id'] for t,a in idx.tags if t=='article' and 'data-row-id'in a]
ordered=json.loads(subprocess.check_output(['node','-e',"console.log(JSON.stringify(require('./app.js').filterCatalog(require('./data/catalog.json'),{}).map(x=>x.id)))"],cwd=r,text=True));assert ids==ordered
urls=[x.text for x in ET.parse(r/'sitemap.xml').findall('.//{*}loc')];assert len(urls)==len(set(urls))==len(rows)+1 and set(urls)==expected
assert not ET.parse(r/'sitemap.xml').findall('.//{*}lastmod');assert not (r/'robots.txt').exists()
assert len(canonicals)==len(rows)+1
print(f'SEO checks passed: {len(rows)} indexed rows/pages, {len(rows)+1} unique canonicals and sitemap URLs; relative links and source consistency. No indexing guarantee.')
