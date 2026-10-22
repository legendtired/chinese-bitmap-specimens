from pathlib import Path
import subprocess,tempfile,shutil
r=Path(__file__).resolve().parents[1]
for f in ['AGENTS.md','docs/DEVELOPMENT.md','docs/PROJECT_STATE.md','scripts/workspace.py','scripts/render_bdf.py','scripts/apply_preview.py','.gitignore']:assert (r/f).exists()
assert '网页手动上传' in (r/'AGENTS.md').read_text()
if not shutil.which('git'):print('Git ignore check skipped: Git not installed.');raise SystemExit(0)
with tempfile.TemporaryDirectory() as t:
 p=Path(t);subprocess.run(['git','init','-q',str(p)],check=True)
 shutil.copy2(r/'.gitignore',p/'.gitignore')
 cases=['local-research/source.ttf','local-research/manifest.json','font.TTC','old.bdf.gz','rom.mot','.env','delivery.zip','__pycache__/cache.pyc']
 for f in cases:
  dest=p/f;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text('test sentinel')
 (p/'index.html').write_text('public sentinel')
 subprocess.run(['git','-C',str(p),'add','.'],check=True)
 tracked=subprocess.check_output(['git','-C',str(p),'ls-files'],text=True).splitlines()
 assert tracked==['.gitignore','index.html'],tracked
print('Workspace checks passed: local research, raw fonts/ROM, ZIP, secrets and caches excluded in temporary Git staging; no real repository modified.')
