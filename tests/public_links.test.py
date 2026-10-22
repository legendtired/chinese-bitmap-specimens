"""Public sources are information pages, not direct font/archive downloads."""
from pathlib import Path
from urllib.parse import urlsplit, unquote, parse_qs
import re, html
ROOT=Path(__file__).resolve().parents[1]
URL=re.compile(r'''https?://[^\s<>"'`\\]+''')
DOWNLOAD=re.compile(r'\.(?:zip|tar|tgz|gz|z|bz2|xz|7z|rar|ttf|ttc|otf|otc|woff2?|bdf|pcf|fon|fnt|rom|mot|nftr|hbf|bin)$',re.I)
def direct_download(url):
 url=re.split(r'[\u3000-\u303f\uff00-\uffef]',html.unescape(url))[0].rstrip('.,);')
 p=urlsplit(url); path=unquote(p.path); query=parse_qs(p.query,keep_blank_values=True)
 if p.hostname=='github.com' and '/blob/' in path and not any(k in query for k in ['raw','download']): return False
 return any(k in query for k in ['raw','download']) or bool(DOWNLOAD.search(path)) or ('/releases/download/' in path) or (p.hostname=='github.com' and '/archive/' in path)
scheme='https'+'://'
assert not direct_download(scheme+'github.com/example/fonts/blob/main/font.ttf')
for tail in ['font.ttf?raw=true','font.ttf?raw=1','font.ttf?download=1','font.ttf?download']:
 assert direct_download(scheme+'github.com/example/fonts/blob/main/'+tail)
for hostpath in ['cdn.example.org/font.woff2','raw.githubusercontent.com/example/main/font.bdf','example.org/archive.tar.gz']:
 assert direct_download(scheme+hostpath)
fail=[];count=0
for f in ROOT.rglob('*'):
 if not f.is_file() or set(f.relative_to(ROOT).parts)&{'local-research','.git','__pycache__'}:continue
 if f.suffix not in {'.md','.json','.js','.html','.xml','.py','.cjs'}:continue
 for url in URL.findall(f.read_text(encoding='utf-8')):
  count+=1
  if direct_download(url):fail.append((str(f.relative_to(ROOT)),url))
assert not fail,fail
print(f'Public link checks passed: {count} URL references inspected; no direct font/archive links. Information/source browser pages remain allowed.')
