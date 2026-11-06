# Psion 618C 8／11点

中文Revo/618C 1.08(14)系统的Unicode.gdr位图。8点有15,441个非空汉字，11点有15,447个；均包含全部6,763个GB2312汉字。通常字进分别为9、12px，保留原始bearing和行数据。

来源：[ROM历史资料](https://github.com/explit28/Psion-ROM/tree/main/Revo/Revo_v1.08%2814%29_chitr)、[原厂中文系统说明](https://enfour.com/psion/uftc.html)。文件署名DynaLab、Shanghai eBook、Enfour，未查到开放字体许可。存档设备归属未重新通过实机读取验证。

## 本地导出

自行取得并确认有权处理上述ROM。脚本不联网、不执行ROM，不覆盖已有输出：

```sh
python scripts/psion_gdr_to_bdf.py Revo.bin --rom --size 8 --output psion8.bdf
python scripts/psion_gdr_to_bdf.py Revo.bin --rom --size 11 --output psion11.bdf
```

也可直接以Unicode.gdr作为输入并去掉`--rom`。脚本校验GDR精确SHA256，按原Unicode索引导出非空字形，保留DWIDTH、BBX与基线；空占位不计覆盖。此文件不含普通ASCII，不能据此推断整台设备缺少西文。

## 查重

8点与8套可得来源逐字比对，未见整库重复；最高ELISA为108/5,506字同形。丁卯商业全库未取得。11点与HZK11、MingLiU、Firefly、LanaPixel、Mplus比对，未见整库重复；部分其他条目仅核对固定样张。15点与国乔eb5-15f的13,061个共同汉字中13,000个同形，不独立收录。

公开内容仅固定字样和无字模脚本，不包含ROM、GDR、完整BDF或字模数组。

## Arial 英数字样

[同系统 Arial 搭配与导出](psion618c-arial.md)：8／11点各补95个ASCII，保留原生不等宽；按用户选择搭配。
