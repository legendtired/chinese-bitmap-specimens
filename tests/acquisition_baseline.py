"""Restore only the approved acquisition-guide delta for historical release checks."""
from approved_unionway_name import before_name_row
from pathlib import Path
import json
BASE=json.loads((Path(__file__).parent/'fixtures/acquisition-before.json').read_text())
def before_acquisition(row):
 row=before_name_row(row)
 result={k:v for k,v in row.items() if k!='acquisitionGuide'}
 if row['id'] in BASE['originalGuides']:result['acquisitionGuide']=BASE['originalGuides'][row['id']]
 return result
