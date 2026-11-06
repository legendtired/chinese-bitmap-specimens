"""Stage a clean, allowlisted public Pages upload. Does not deploy."""
from pathlib import Path, PurePosixPath
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.pages-public'
ROOT_FILES = {'.nojekyll', 'index.html', 'app.js', 'styles.css', 'sitemap.xml',
              'README.md', 'CONTRIBUTING.md', 'data-review.md'}
DIRECTORIES = {'assets', 'data', 'docs', 'fonts', 'scripts', 'third_party'}
EXTENSIONS = {'.html', '.css', '.js', '.mjs', '.cjs', '.json', '.md', '.txt',
              '.py', '.png', '.jpg', '.jpeg', '.svg', '.webp', '.xml', '.h'}
LICENSE_FILES = {'scripts/vendor/ftcomp/COPYING', 'third_party/LUCIDE_LICENSE'}
DENIED_PARTS = {'local-research', 'node_modules', 'private', 'preview',
                'preview-worker', 'functions', '.git', '.github', '__pycache__'}
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
selected = []
for name in filter(None, tracked):
    rel = PurePosixPath(name)
    if name not in ROOT_FILES and rel.parts[0] not in DIRECTORIES:
        continue
    if rel.is_absolute() or '..' in rel.parts or any(p in DENIED_PARTS for p in rel.parts):
        raise SystemExit(f'Unsafe public path: {name}')
    if name != '.nojekyll' and name not in LICENSE_FILES and rel.suffix.lower() not in EXTENSIONS:
        raise SystemExit(f'Unreviewed public file type: {name}')
    if any(p.startswith('.env') for p in rel.parts) or rel.name in {'_worker.js', '_routes.json', 'wrangler.toml', 'wrangler.json', 'wrangler.jsonc'}:
        raise SystemExit(f'Deployment configuration must not be uploaded: {name}')
    src = ROOT / name
    if src.is_symlink() or not src.is_file() or not src.resolve().is_relative_to(ROOT):
        raise SystemExit(f'Not a regular public file: {name}')
    if src.stat().st_size > 25 * 1024 * 1024:
        raise SystemExit(f'Pages file limit exceeded: {name}')
    selected.append(name)
for required in ['index.html', 'styles.css', 'assets/wordmark.png', 'data/catalog.js']:
    if required not in selected:
        raise SystemExit(f'Missing required public asset: {required}')
if len(selected) > 20000:
    raise SystemExit('Pages file count exceeded')
if OUT.exists():
    raise SystemExit('Staging directory already exists; use a clean checkout')
OUT.mkdir()
for name in selected:
    target = OUT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)
print(f'Staged {len(selected)} public files. Worker, R2 and routes are not modified.')
