#!/usr/bin/env python3
"""Render one reviewed short Zhenhan V3.00 specimen from exact local disk files."""
import argparse
import hashlib
from pathlib import Path
from PIL import Image

SC = '视野无限广，窗外有蓝天。'
TC = '視野無限廣，窗外有藍天。'
EN = '0123456789 AaBb GgMm !?:+-.'
FILES = {
    'SIMPLE1.15': (1, '2d7df620f825b7c168ef456fb3323320e9652a669b9e29741fd480e006b7a3fb'),
    'SIMPLE2.15': (1, '32cb0d8ed44f8c5d40ec899891cab8a558a10d2060cb49b9c7d696aa079419e7'),
    'HANSTD1.15': (1, '5c91a77f5d65e43d4ebaff3f5fd5d5d8701e7e6af74081daa3dc1985df794799'),
    'HANSTD2.15': (1, 'a82a9a126279f32a396c44538f9cf246a5803d7e775158787ba990110bd77e47'),
    'HAN-GR.15': (1, 'b3b06c9224ecd650982713d78905a91eddbd298fc78ced1608c4fb8a96b1582b'),
    'HAN-ASC.15': (1, '621222d1fdeef1589e8ed41464d9af52643c81dcb1b409890cff5601821c57d4'),
    'CK.24': (8, '05705fb8dd0554b6b9094898a2c0764732ff3c8cc6107b76465ae5bafdf94f9e'),
    'HAN-GR.24': (3, 'b0fd8928259e8ca3b85ae588de3345cca66b37e405921e2ce7a7ce7132385de2'),
    'HAN-ASC.24': (3, '32843a1fd4f9b922a7288a95a0469f462a9cc49071be01dfe16985ab63d169f6'),
}

def checked(disks, name):
    disk, sha = FILES[name]
    raw = (disks / f'original_043-{disk}-unwrapped' / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('Unrecognized source: ' + name)
    return raw

def big5_slot(ch):
    lead, trail = ch.encode('big5')
    if not (0xa4 <= lead <= 0xf9 and lead not in (0xc7, 0xc8)):
        raise ValueError('Out-of-range fixed Han slot')
    t = trail - (0x40 if trail <= 0x7e else 0xa1 - 63)
    return (lead - 0xa4)*157 + t - (408 if lead >= 0xc9 else 0)

def paint(image, data, x0, y0, width, height, stride, ink_expected=True):
    if len(data) != height*stride:
        raise ValueError('Short fixed cell')
    found = False
    for y in range(height):
        for x in range(width):
            if data[y*stride+x//8] & (0x80 >> (x%8)):
                image.putpixel((x0+x, y0+y), (0, 0, 0, 255))
                found = True
    if found != ink_expected:
        raise ValueError('Unexpected blank or inked fixed cell')

def render(disks, mode):
    if mode == '16x15':
        w,h,aw,stride,astride = 16,15,8,2,1
        banks = [checked(disks,prefix+'1.15')+checked(disks,prefix+'2.15') for prefix in ('SIMPLE','HANSTD')]
        syms = checked(disks,'HAN-GR.15')
        ascii_data = checked(disks,'HAN-ASC.15')
    elif mode == 'ck24':
        w,h,aw,stride,astride = 24,24,12,3,2
        banks = [checked(disks,'CK.24')]
        syms = checked(disks,'HAN-GR.24')
        ascii_data = checked(disks,'HAN-ASC.24')
    else:
        raise ValueError('Unsupported specimen mode')
    if any(len(bank) != 13094*h*stride for bank in banks) or len(ascii_data)!=256*h*astride:
        raise ValueError('Unexpected original table size')
    gap = 4
    image=Image.new('RGBA',(max(w*len(SC),aw*len(EN)),h*(len(banks)+1)+gap*len(banks)))
    for i,bank in enumerate(banks):
        for j,ch in enumerate(TC):
            if ch in '，。':
                slot=ch.encode('big5')[1]-0x40
                src=syms
            else:
                slot=big5_slot(ch)
                src=bank
            offset=slot*h*stride
            paint(image,src[offset:offset+h*stride],j*w,i*(h+gap),w,h,stride)
    for j,ch in enumerate(EN):
        offset=ord(ch)*h*astride
        paint(image,ascii_data[offset:offset+h*astride],j*aw,len(banks)*(h+gap),aw,h,astride,ch!=' ')
    return image

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disks',type=Path,required=True)
    parser.add_argument('--mode',choices=('16x15','ck24'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.suffix.lower()!='.png':
        parser.error('--output must be a new PNG')
    image=render(args.disks,args.mode)
    with args.output.open('xb') as out:
        image.save(out,format='PNG')

if __name__=='__main__':
    main()
