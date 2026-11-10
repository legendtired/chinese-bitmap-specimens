"""Exactly undo the reviewed SimSun version release for historical audits only."""
from pathlib import Path
import copy, hashlib, json, re, sys
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'data/release-simsun-versions.json').read_text())
IDS=MANIFEST['addedIds']
def sha(data):return hashlib.sha256(data).hexdigest()
def digest(value):return sha(json.dumps(value,ensure_ascii=False,sort_keys=True).encode())
def original_rows():
    value=MANIFEST.get('modifiedRowsBefore',{})
    return value if isinstance(value,dict) else {r['id']:r for r in value}
def before_simsun_rows(rows):
    old=original_rows();result=[]
    for row in rows:
        ident=row['id']
        if ident in IDS:
            assert digest(row)==MANIFEST['rowHashes'][ident], 'Unreviewed SimSun row'
        elif ident in old:
            assert digest(row) in (digest(old[ident]),MANIFEST['modifiedRowsAfterSha256'][ident]), 'Unreviewed Founder change'
            result.append(copy.deepcopy(old[ident]))
        else:result.append(row)
    assert len({r['id'] for r in rows})==len(rows), 'Duplicate catalog row'
    return result

def before_simsun_data(path,value):
    if path=='data/catalog.json':return before_simsun_rows(value)
    value=copy.deepcopy(value)
    if path=='data/collection-history.json':
        found=[b for b in value['batches'] if b.get('sourceManifest')=='release-simsun-versions.json']
        if found:
            assert found==[MANIFEST['batch']] and value['batches'][-1]==MANIFEST['batch'], 'Unreviewed SimSun batch'
            value['batches'].pop()
    elif path=='data/summary.json':
        def undo(v,after,before):
            for k,a in after.items():
                b=before[k]
                if isinstance(a,dict):undo(v[k],a,b)
                elif isinstance(a,int) and not isinstance(a,bool):v[k]-=a-b
        undo(value,MANIFEST['summary'],MANIFEST['baseSummary'])
    elif path in MANIFEST.get('baseChangedFiles',{}):
        raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
        if sha(raw)==MANIFEST['changedFileHashes'].get(path):
            value=json.loads(MANIFEST['baseChangedFiles'][path])
    return value

def before_simsun_bytes(path,root=ROOT):
    data=(root/path).read_bytes()
    if path in ('data/catalog.json','data/collection-history.json','data/summary.json'):
        return (json.dumps(before_simsun_data(path,json.loads(data)),ensure_ascii=False,indent=2)+'\n').encode()
    if path in ('data/catalog.js','data/collection-history.js'):
        prefix,payload=data.decode().split(' = ',1)
        value=before_simsun_data(path.replace('.js','.json'),json.loads(payload.rstrip().removesuffix(';')))
        return (prefix+' = '+json.dumps(value,ensure_ascii=False,indent=2)+';\n').encode()
    if path=='sitemap.xml':
        text=data.decode()
        for ident in IDS:
            text,count=re.subn(r'<url><loc>https://legendtired.github.io/chinese-bitmap-specimens/fonts/'+ident+r'\.html</loc></url>\n','',text)
            assert count==1
        return text.encode()
    if path=='index.html':
        sys.path.insert(0,str(ROOT/'scripts'))
        import generate_static as generator
        text=data.decode()
        for asset in ('data/catalog.js','data/collection-history.js','app.js'):
            current=sha((root/asset).read_bytes())[:16];previous=sha(before_simsun_bytes(asset,root))[:16]
            tag=f'src="{asset}?v={current}"';assert text.count(tag)==1
            text=text.replace(tag,f'src="{asset}?v={previous}"',1)
        for ident in IDS:
            text,count=re.subn(r'<article class="specimen" data-row-id="'+ident+r'">.*?</article>\n','',text,flags=re.S);assert count==1
        for ident,row in original_rows().items():
            pattern=r'<article class="specimen" data-row-id="'+ident+r'">.*?</article>\n'
            match=re.search(pattern,text,re.S);assert match
            current=next(r for r in json.loads((root/'data/catalog.json').read_text()) if r['id']==ident)
            assert match.group()==generator.article(current)+'\n'
            text=re.sub(pattern,lambda _:generator.article(row)+'\n',text,flags=re.S)
        assert text.count('>256 个字样</span>')==1
        return text.replace('>256 个字样</span>','>252 个字样</span>',1).encode()
    # Restore only reviewed byte-identical changes. Any unrelated mutation survives
    # normalization, so every historical baseline hash still detects tampering.
    if path in MANIFEST.get('baseChangedFiles',{}) and sha(data)==MANIFEST['changedFileHashes'].get(path):
        old=MANIFEST['baseChangedFiles'][path].encode()
        assert sha(old)==MANIFEST['baseFilesSha256'][path],path
        return old
    if path.startswith('fonts/') and Path(path).stem in original_rows():
        sys.path.insert(0,str(ROOT/'scripts'))
        import generate_static as generator
        if sha(data)==MANIFEST['changedFileHashes'].get(path):
            old=generator.font_page(original_rows()[Path(path).stem]).encode()
            assert sha(old)==MANIFEST['baseFilesSha256'][path]
            return old
    return data
