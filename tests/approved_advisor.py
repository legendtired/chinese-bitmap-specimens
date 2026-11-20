"""Undo only the exact, reviewed Advisor release for historical snapshot audits."""
from approved_wonder import before_wonder_bytes, before_wonder_data, before_wonder_rows
from pathlib import Path
import copy, hashlib, json, re
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'data/release-motorola-advisor.json').read_text())
IDS=MANIFEST['addedIds']
def sha(data):return hashlib.sha256(data).hexdigest()
def digest(value):return sha(json.dumps(value,ensure_ascii=False,sort_keys=True).encode())
def before_advisor_rows(rows):
    rows=before_wonder_rows(rows)
    found=[r for r in rows if r['id'] in IDS]
    if found:
        assert len(found)==1 and digest(found[0])==MANIFEST['rowSha256'], 'Unreviewed Advisor row'
        assert rows[-1]==found[0], 'Advisor must be appended'
    assert len({r['id'] for r in rows})==len(rows), 'Duplicate row'
    return [r for r in rows if r['id'] not in IDS]
def before_advisor_data(path,value):
    value=before_wonder_data(path,value)
    if path=='data/catalog.json':return before_advisor_rows(value)
    value=copy.deepcopy(value)
    if path=='data/collection-history.json':
        found=[b for b in value['batches'] if b.get('sourceManifest')=='release-motorola-advisor.json']
        if found:
            assert found==[MANIFEST['batch']] and value['batches'][-1]==MANIFEST['batch'], 'Unreviewed Advisor batch'
            value['batches'].pop()
    elif path=='data/summary.json' and value.get('rows')==258:
        assert value==MANIFEST['summary'], 'Unreviewed Advisor summary'
        value=copy.deepcopy(MANIFEST['baseSummary'])
    return value

def before_advisor_bytes(path,root=ROOT):
    data=before_wonder_bytes(path,root)
    if path in MANIFEST['changedFileHashes']:
        assert sha(data)==MANIFEST['changedFileHashes'][path], 'Unreviewed Advisor file: '+path
    if path in ('data/catalog.json','data/collection-history.json','data/summary.json'):
        return (json.dumps(before_advisor_data(path,json.loads(data)),ensure_ascii=False,indent=2)+'\n').encode()
    if path in ('data/catalog.js','data/collection-history.js'):
        prefix,payload=data.decode().split(' = ',1)
        value=before_advisor_data(path.replace('.js','.json'),json.loads(payload.rstrip().removesuffix(';')))
        return (prefix+' = '+json.dumps(value,ensure_ascii=False,indent=2)+';\n').encode()
    if path=='sitemap.xml':
        text,count=re.subn(r'<url><loc>https://legendtired.github.io/chinese-bitmap-specimens/fonts/motorola_advisor_16\.html</loc></url>\n','',data.decode())
        assert count==1
        return text.encode()
    if path=='index.html':
        text=data.decode()
        for asset in ('data/catalog.js','data/collection-history.js','app.js'):
            current=sha(before_wonder_bytes(asset,root))[:16];prior=sha(before_advisor_bytes(asset,root))[:16]
            tag=f'src="{asset}?v={current}"';assert text.count(tag)==1
            text=text.replace(tag,f'src="{asset}?v={prior}"',1)
        text,count=re.subn(r'<article class="specimen" data-row-id="motorola_advisor_16">.*?</article>\n','',text,flags=re.S);assert count==1
        assert text.count('>258 个字样</span>')==1
        return text.replace('>258 个字样</span>','>257 个字样</span>',1).encode()
    if path in MANIFEST['baseChangedFiles']:
        original=MANIFEST['baseChangedFiles'][path].encode()
        assert sha(original)==MANIFEST['baseFilesSha256'][path], path
        return original
    return data
