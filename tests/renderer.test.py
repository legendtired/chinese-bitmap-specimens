"""Small authored bitmap fixtures test mechanics, not real font design quality."""
from pathlib import Path
import tempfile,sys,importlib.util
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('render_bdf',root/'scripts/render_bdf.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
# Pillow is optional for public checks. Explicit rendering needs it.
try:import PIL
except ImportError:print('Renderer pixel test skipped: optional Pillow not installed.');sys.exit(0)
bdf='''STARTFONT 2.1
FONTBOUNDINGBOX 4 4 0 0
STARTPROPERTIES 4
FONT_ASCENT 4
FONT_DESCENT 0
CHARSET_REGISTRY "ISO10646"
CHARSET_ENCODING "1"
ENDPROPERTIES
CHARS 1
STARTCHAR A
ENCODING 65
DWIDTH 4 0
BBX 3 3 0 0
BITMAP
40
A0
E0
ENDCHAR
ENDFONT
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.bdf').write_text(bdf)
 result=mod.render(p/'test.bdf','A\U0010ffffA','unicode',p/'test.png')
 assert result['missing']==['\U0010ffff'] and result['specimenWidth']==12
 from PIL import Image
 im=Image.open(p/'test.png');assert im.crop((4,0,8,4)).getbbox() is None
 assert im.getpixel((1,1))[3]==255 and im.getpixel((0,1))[3]==0
 assert im.crop((0,0,4,4)).tobytes()==im.crop((8,0,12,4)).tobytes()
print('BDF renderer checks passed: direct bitmap pixels, advance preservation, transparent missing cell and explicit report; no fallback.')
