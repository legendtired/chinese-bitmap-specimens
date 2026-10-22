#!/usr/bin/env python3
"""Optional regeneration of share.png using actual PNG pixels. Requires Pillow; no font engine."""
from pathlib import Path
from PIL import Image, ImageDraw
r=Path(__file__).resolve().parents[1]
canvas=Image.new('RGB',(1200,630),'white');d=ImageDraw.Draw(canvas)
d.line((80,270,1120,270),fill='#e8e9eb',width=2)
word=Image.open(r/'assets/wordmark.png').convert('RGBA').resize((576,144),Image.Resampling.NEAREST)
canvas.paste(word,(80,70),word)
for name,y in [('founder_pixel12',320),('apple_kai_12',450)]:
 img=Image.open(r/f'assets/specimens/{name}.png').convert('RGBA');img=img.resize((img.width*3,img.height*3),Image.Resampling.NEAREST);canvas.paste(img,(80,y),img)
canvas.save(r/'assets/share.png')
