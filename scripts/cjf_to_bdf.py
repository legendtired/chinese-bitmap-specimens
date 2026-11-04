#!/usr/bin/env python3
"""Static converter for the three audited Casio XD-A10000 CJF files.
No font data included. Requires a separately obtained, exact source file.
Usage: python cjf_to_bdf.py china12z.cjf output.bdf
No assertion of redistribution rights for input or output fonts.
"""
import sys,hashlib,pathlib
KNOWN={
 '0d83d8a638d1329c1b1a28bc2568c05594721eeeed012efa2f1bea0ab595d65b':12,
 'c9036da87827b2d3fc21d51586b383f2e6aed0987038dd2d66e7f78dfee2c5a2':16,
 '5daf1780bb0ff1e68989736d1f3858e215436c2e232f7ab13063adae07d9e2a1':24}
def main():
 if len(sys.argv)!=3:raise SystemExit(__doc__)
 b=pathlib.Path(sys.argv[1]).read_bytes();n=KNOWN.get(hashlib.sha256(b).hexdigest())
 if n is None:raise SystemExit('Unknown input SHA256; refusing to guess its format.')
 row=(n+7)//8;step=row*n
 assert len(b)==256+23940*step and b[:3]==b'CJF'
 chars=[];seen=set()
 for hi in range(0x81,0xff):
  for lo in list(range(0x40,0x7f))+list(range(0x80,0xff)):
   raw=bytes([hi,lo]);c=raw.decode('gb18030');assert len(c)==1 and c.encode('gb18030')==raw and c not in seen;seen.add(c);chars.append(c)
 assert len(chars)==23940
 with open(sys.argv[2],'x',encoding='ascii')as f:
  f.write(f'STARTFONT 2.1\nFONT -Casio-RecoveredCJF-Medium-R-Normal--{n}-{n*10}-75-75-C-{n*10}-ISO10646-1\nSIZE {n} 75 75\nFONTBOUNDINGBOX {n} {n} 0 0\nSTARTPROPERTIES 2\nFONT_ASCENT {n}\nFONT_DESCENT 0\nENDPROPERTIES\nCHARS 23940\n')
  for i,c in enumerate(chars):
   s=b[256+i*step:256+(i+1)*step];f.write(f'STARTCHAR U{ord(c):04X}\nENCODING {ord(c)}\nSWIDTH 1000 0\nDWIDTH {n} 0\nBBX {n} {n} 0 0\nBITMAP\n')
   for y in range(n):
    v=int.from_bytes(s[y*row:(y+1)*row],'big');v &= ((1<<n)-1)<<(row*8-n);f.write(f'{v:0{row*2}X}\n')
   f.write('ENDCHAR\n')
  f.write('ENDFONT\n')
 print(f'Wrote 23940 Unicode cells at {n}x{n}. Mapping uses this Python version\'s GB18030 codec; historical GB18030 revisions may differ at a few non-GB2312 code points.')
if __name__=='__main__':main()
