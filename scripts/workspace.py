#!/usr/bin/env python3
"""Single local entry point. No publication/network actions."""
from pathlib import Path
import argparse,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def run(args):subprocess.run(args,cwd=ROOT,check=True)
p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
for name in ['build','check']:sub.add_parser(name)
q=sub.add_parser('research-status');q.add_argument('--id')
for name in ['inspect-bdf','render-bdf']:
 q=sub.add_parser(name);q.add_argument('--font',required=True)
 if name=='render-bdf':
  q.add_argument('--encoding',required=True,choices=['unicode','gb2312','big5']);q.add_argument('--text',required=True);q.add_argument('--output',required=True)
q=sub.add_parser('apply-preview');q.add_argument('--id',required=True);q.add_argument('--report',required=True);q.add_argument('--reviewed-source-and-glyphs',action='store_true',required=True)
a=p.parse_args()
if a.command=='build':run([sys.executable,'scripts/generate_static.py'])
elif a.command=='check':
 run(['node','--check','app.js'])
 for test in sorted((ROOT/'tests').glob('*.test.py')):run([sys.executable,str(test)])
 for test in ['filters','priority','state','curation']:run(['node',f'tests/{test}.test.cjs'])
 print('Static/logic checks finished. Real-browser checks were not run by this command.')
elif a.command=='apply-preview':run([sys.executable,'scripts/apply_preview.py','--id',a.id,'--report',a.report,'--reviewed-source-and-glyphs'])
elif a.command=='research-status':
 folder=ROOT/'local-research';report=folder/'catalog-input-coverage.json'
 if not folder.exists():print('Local research assets are not present. Public PNGs remain usable; source re-extraction is not implied.');sys.exit(0)
 print('Local research folder present; read local-research/README.md before using archived scripts.')
 if report.exists():
  coverage=json.loads(report.read_text())
  if a.id:
   match=next((x for x in coverage if x.get('id')==a.id),None)
   print(json.dumps(match if match else {'error':'ID not found'},ensure_ascii=False,indent=2))
  else:
   from collections import Counter
   print(json.dumps({'entries':len(coverage),'statusCounts':dict(Counter(x.get('status','unknown') for x in coverage)),'hint':'Use research-status --id <catalog-id> for mapped local inputs.'},ensure_ascii=False,indent=2))
 else:print('No verified per-entry coverage report is available. Do not claim complete reconstruction.')
else:
 args=[sys.executable,'scripts/render_bdf.py','--font',a.font]
 if a.command=='inspect-bdf':args+=['--inspect']
 else:args+=['--encoding',a.encoding,'--text',a.text,'--output',a.output]
 run(args)
