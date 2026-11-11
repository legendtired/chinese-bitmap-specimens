"""Undo only the one reviewed Emperor addition for immutable historical audits."""
from pathlib import Path
import copy,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'data/release-emperor-dos.json').read_text())
IDS=MANIFEST['addedIds']
def sha(value):return hashlib.sha256(value).hexdigest()
def digest(value):return sha(json.dumps(value,ensure_ascii=False,sort_keys=True).encode())
def before_emperor_rows(rows):
    found=[r for r in rows if r['id'] in IDS]
    if found:
        assert len(found)==1 and digest(found[0])==MANIFEST['rowSha256'], 'Unreviewed Emperor row'
    assert len({r['id'] for r in rows})==len(rows), 'Duplicate row'
    return [r for r in rows if r['id'] not in IDS]
def before_emperor_data(path,value):
    if path=='data/catalog.json':return before_emperor_rows(value)
    value=copy.deepcopy(value)
    if path=='data/collection-history.json':
        found=[b for b in value['batches'] if b.get('sourceManifest')=='release-emperor-dos.json']
        if found:
            assert found==[MANIFEST['batch']] and value['batches'][-1]==MANIFEST['batch'], 'Unreviewed Emperor batch'
            value['batches'].pop()
    elif path=='data/summary.json' and value.get('rows')==257:
        assert value==MANIFEST['summary'], 'Unreviewed Emperor summary'
        value=copy.deepcopy(MANIFEST['baseSummary'])
    return value

def before_emperor_bytes(path,root=ROOT):
    data=(root/path).read_bytes()
    if path in ('data/catalog.json','data/collection-history.json','data/summary.json'):
        return (json.dumps(before_emperor_data(path,json.loads(data)),ensure_ascii=False,indent=2)+'\n').encode()
    if path in ('data/catalog.js','data/collection-history.js'):
        prefix,payload=data.decode().split(' = ',1)
        value=before_emperor_data(path.replace('.js','.json'),json.loads(payload.rstrip().removesuffix(';')))
        return (prefix+' = '+json.dumps(value,ensure_ascii=False,indent=2)+';\n').encode()
    if path=='sitemap.xml':
        text,count=re.subn(r'<url><loc>https://legendtired.github.io/chinese-bitmap-specimens/fonts/emperor_dos_16x15\.html</loc></url>\n','',data.decode())
        assert count==1
        return text.encode()
    if path=='index.html':
        text=data.decode()
        for asset in ('data/catalog.js','data/collection-history.js','app.js'):
            current=sha((root/asset).read_bytes())[:16];prior=sha(before_emperor_bytes(asset,root))[:16]
            tag=f'src="{asset}?v={current}"';assert text.count(tag)==1
            text=text.replace(tag,f'src="{asset}?v={prior}"',1)
        text,count=re.subn(r'<article class="specimen" data-row-id="emperor_dos_16x15">.*?</article>\n','',text,flags=re.S);assert count==1
        assert text.count('>257 个字样</span>')==1
        return text.replace('>257 个字样</span>','>256 个字样</span>',1).encode()
    if path in MANIFEST.get('baseChangedFiles',{}):
        assert sha(data)==MANIFEST['changedFileHashes'][path], 'Unreviewed file: '+path
        data=MANIFEST['baseChangedFiles'][path].encode()
        assert sha(data)==MANIFEST['baseFilesSha256'][path]
    return data
