"""One source-backed naming correction; immutable rows, recommendations and pixels."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
from approved_unionway_name import UPDATE, before_name_row
from approved_about_copy import before_about_copy

ROOT = Path(__file__).resolve().parents[1]
sha = lambda data: hashlib.sha256(data).hexdigest()
digest = lambda value: sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
rows = json.loads((ROOT / 'data/catalog.json').read_text())
assert UPDATE['baseCommit'] == '05c5b71d585a1dbdc7fc955f5de782cc307c7c08'
assert len(rows) == len({row['id'] for row in rows}) == UPDATE['totalRows'] == 239
assert [(c['id'], c['field']) for c in UPDATE['changes']] == [('ccic_uwb5_16m', 'name'), ('san5_dos_16x14', 'notes')]
for change in UPDATE['changes']:
    assert next(row[change['field']] for row in rows if row['id'] == change['id']) == change['after']
    assert change['after'] == change['before'].replace('双桥 ', '').replace('双桥', '')
assert digest(rows) == UPDATE['afterRowsSha256']
assert digest([before_name_row(row) for row in rows]) == UPDATE['beforeRowsSha256']
recommended = [row['id'] for row in sorted(rows, key=lambda row: -row['priority']) if row['priority'] > 0]
assert recommended == UPDATE['recommendedIds'] and len(recommended) == 16
assert digest({row['id']: sha((ROOT / row['specimen']).read_bytes()) for row in rows}) == UPDATE['specimensSha256']
row = next(row for row in rows if row['id'] == 'ccic_uwb5_16m')
assert row['name'] == 'UnionWay 繁体明体 16 · 16×16'
assert row['specimenSha256'] == sha((ROOT / row['specimen']).read_bytes()) == '4c798b5e18f472c98f15928bdcbf2145a5ee5dc0a851c3eab3a68a680ff3f33b'
assert row['priority'] == 0
assert set(UPDATE['changedPublicFiles']) == {'data/catalog.json', 'data/catalog.js', 'index.html', 'fonts/ccic_uwb5_16m.html', 'fonts/san5_dos_16x14.html', 'docs/san5-dos.md', 'docs/research-notes.md'}
replacements = [('UnionWay 繁体明体 16 · 16×16', '双桥 UnionWay 繁体明体 16 · 16×16'), ('UnionWay16', 'UnionWay双桥16'), ('UnionWay 16', 'UnionWay 双桥16')]
for path, hashes in UPDATE['changedPublicFiles'].items():
    current = (ROOT / path).read_bytes()
    if path == 'index.html':
        # Later approved explanatory copy is unrelated to this naming audit.
        current = before_about_copy(current.decode()).encode()
    assert sha(current) == hashes['after'], path
    old = current.decode()
    if path == 'index.html':
        sys.path.insert(0, str(ROOT / 'scripts'))
        from generate_static import article
        historical = [before_name_row(row) for row in rows]
        # Reproduce the old name-dependent ordering with the unchanged generator.
        program = "const fs=require('fs'), api=require('./app.js');process.stdout.write(JSON.stringify(api.filterCatalog(JSON.parse(fs.readFileSync(0,'utf8')),{})))"
        ordered = json.loads(subprocess.check_output(['node', '-e', program], input=json.dumps(historical).encode(), cwd=ROOT))
        old = re.sub(r'<!-- STATIC_CATALOG_START -->.*?<!-- STATIC_CATALOG_END -->', '<!-- STATIC_CATALOG_START -->\n' + '\n'.join(article(row) for row in ordered) + '\n<!-- STATIC_CATALOG_END -->', old, flags=re.S)
        assert sha(old.encode()) == hashes['before'], path
        continue
    for new, before in replacements:
        old = old.replace(new, before)
    assert sha(old.encode()) == hashes['before'], 'Non-naming edit: ' + path
print('UnionWay naming: only unsupported TwinBridge label removed; 239 IDs, 16 recommendation weights, all other fields and every PNG preserved.')
