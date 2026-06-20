#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Amiga Ultima IV:U4SH.LWZ → xu4 tileset PNG(16×4096)。

管線:
  1. U4SH.LWZ 是 U4 專屬 12-bit LZW(用 xu4 lzw_unpack.c 解,skip=0)→ 32800 byte。
  2. 解壓資料 = 前 32 byte palette(16 色 Amiga 0x0RGB)+ 256 tile × 128 byte。
  3. 每 tile = 16×16,**逐列交錯 bitplane**(每 row 8 byte = 4 plane × 2 byte,MSB 左)。
  4. tile 序 = canonical U4 = xu4 256 序。
資料屬版權,輸出留本機。
用法:python3 build_amiga_tileset.py <U4SH_decompressed.bin> <out.png>
"""
import sys,struct
from PIL import Image
d=open(sys.argv[1],"rb").read()
pal=[]
for i in range(16):
    w=struct.unpack_from(">H",d,i*2)[0]
    pal.append((((w>>8)&0xF)*17,((w>>4)&0xF)*17,(w&0xF)*17))
tiles=d[32:]; NT=256
def decode(tb):
    out=[0]*256
    for r in range(16):
        for pl in range(4):
            for byi in range(2):
                bb=tb[r*8+pl*2+byi]
                for bit in range(8):
                    if (bb>>(7-bit))&1: out[r*16+byi*8+bit]|=(1<<pl)
    return out
img=Image.new("RGB",(16,16*NT)); p=img.load()
for t in range(NT):
    tb=tiles[t*128:(t+1)*128]
    if len(tb)<128: break
    px=decode(tb)
    for i,v in enumerate(px): p[i%16,t*16+i//16]=pal[v&0xF]
img.save(sys.argv[2]); print(f"Amiga tileset: {NT} tile -> {sys.argv[2]}")
# 放大預覽頭 96 tile
prev=Image.new("RGB",(8*16*4,12*16*4),(40,0,40)); pp=prev.load()
for t in range(96):
    tb=tiles[t*128:(t+1)*128]
    if len(tb)<128: break
    px=decode(tb); ox,oy=(t%8)*16*4,(t//8)*16*4
    for i,v in enumerate(px):
        for dy in range(4):
            for dx in range(4): pp[ox+(i%16)*4+dx,oy+(i//16)*4+dy]=pal[v&0xF]
prev.save(sys.argv[2].replace(".png","_prev.png"))
