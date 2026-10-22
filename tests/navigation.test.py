from pathlib import Path
from html.parser import HTMLParser
r=Path(__file__).resolve().parents[1]
h=(r/'index.html').read_text();head=h.split('</header>')[0]
assert head.index('id="favorites-open"')<head.index('id="repository-link"')<head.index('id="about-open"')
assert '待开放' not in h and '原仓库' not in h
assert '<span>仓库</span>' in head and '<span>说明</span>' in head
repo='https://github.com/legendtired/chinese-bitmap-specimens'
class Parser(HTMLParser):
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and a.get('href','').startswith(repo):
   assert a.get('target')=='_blank';assert 'noopener' in a.get('rel','') and 'noreferrer' in a.get('rel','')
Parser().feed(h)
for u in [repo,repo+'/issues',repo+'/pulls']:assert 'href="'+u+'"' in h
assert 'https://legendtired.github.io/chinese-bitmap-specimens/' in (r/'README.md').read_text()
about=head.split('id="about-open"',1)[1];assert '<path d="M12 5v16"/>' in about
css=(r/'styles.css').read_text();assert '.header-actions .repository-link{' in css and '.header-actions .about-button{background:#111;color:#fff;' in css
print('Navigation tests passed: ordered actions, real planned project paths, safe external links, secondary pill/primary explanation icon; no publication claim.')

assert (r/'third_party/LUCIDE_LICENSE').read_text().startswith('ISC License')
