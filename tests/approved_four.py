"""Exact reversal of four approved rows for historical regression checks only."""
from pathlib import Path
import copy,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'data/release-approved-four.json').read_text())
IDS=MANIFEST['addedIds']
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def before_four_rows(rows):
    for ident in IDS:
        matches=[r for r in rows if r['id']==ident]
        if matches:
            assert len(matches)==1 and digest(matches[0])==MANIFEST['rowHashes'][ident], 'Unreviewed approved-four row'
    return [r for r in rows if r['id'] not in IDS]
def before_four_data(path,value):
    if path=='data/catalog.json':return before_four_rows(value)
    value=copy.deepcopy(value)
    if path=='data/collection-history.json':
        found=[b for b in value['batches'] if b.get('sourceManifest')=='release-approved-four.json']
        if found:
            assert found==[MANIFEST['batch']] and value['batches'][-1]==MANIFEST['batch'], 'Unreviewed approved-four batch'
            value['batches'].pop()
    elif path=='data/summary.json':
        def undo(v,after,before):
            for k,a in after.items():
                b=before[k]
                if isinstance(a,dict):undo(v[k],a,b)
                elif isinstance(a,int) and not isinstance(a,bool):v[k]-=a-b
        undo(value,MANIFEST['summary'],MANIFEST['baseSummary'])
    return value

def before_four_bytes(path,root=ROOT):
    data=(root/path).read_bytes()
    if path in ('data/catalog.json','data/collection-history.json','data/summary.json'):
        return (json.dumps(before_four_data(path,json.loads(data)),ensure_ascii=False,indent=2)+'\n').encode()
    if path in ('data/catalog.js','data/collection-history.js'):
        prefix,payload=data.decode().split(' = ',1)
        value=before_four_data(path.replace('.js','.json'),json.loads(payload.rstrip().removesuffix(';')))
        return (prefix+' = '+json.dumps(value,ensure_ascii=False,indent=2)+';\n').encode()
    if path=='sitemap.xml':
        text=data.decode()
        for ident in IDS:
            text,count=re.subn(r'<url><loc>https://legendtired.github.io/chinese-bitmap-specimens/fonts/'+ident+r'\.html</loc></url>\n','',text)
            assert count==1
        return text.encode()
    if path=='index.html':
        text=data.decode()
        for asset in ('data/catalog.js','data/collection-history.js','app.js'):
            current=hashlib.sha256((root/asset).read_bytes()).hexdigest()[:16]
            previous=hashlib.sha256(before_four_bytes(asset,root)).hexdigest()[:16]
            tag=f'src="{asset}?v={current}"';assert text.count(tag)==1
            text=text.replace(tag,f'src="{asset}?v={previous}"',1)
        for ident in IDS:
            text,count=re.subn(r'<article class="specimen" data-row-id="'+ident+r'">.*?</article>\n','',text,flags=re.S);assert count==1
        assert text.count('>252 个字样</span>')==1
        return text.replace('>252 个字样</span>','>248 个字样</span>',1).encode()
    return data
