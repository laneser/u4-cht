#!/usr/bin/env python3
"""Amiga mus*.bin 探索:讀 header offset 表 → 4 voice;抽各 voice 的 note 事件畫 piano-roll。
無 spec,純結構逆向:event = 命令 byte(高位 set,低位疑為時長)+ note byte(0x30-0x3f 半音)。"""
import sys,struct
from PIL import Image
d=open(sys.argv[1],"rb").read()
# header:前若干 BE16,取看似遞增且 < filesize 的當 voice offset
hdr=[struct.unpack_from(">H",d,i*2)[0] for i in range(8)]
print("header BE16:",[hex(x) for x in hdr])
# voice offsets:hdr[2:6] 多為遞增 offset
offs=[o for o in hdr[2:7] if 0<o<len(d)]
offs=sorted(set(offs))+[len(d)]
print("voice 區段:",[hex(o) for o in offs])
voices=[]
for i in range(len(offs)-1):
    seg=d[offs[i]:offs[i+1]]
    # 抽 note 事件:掃描,記錄 (前一 cmd 低6位=dur, note)
    events=[]; cmd=0
    for b in seg:
        if b&0x80: cmd=b&0x7f
        elif 0x20<=b<0x40:  # note 範圍
            events.append((cmd,b))
    voices.append(events)
    print(f"voice{i}: {len(seg)}B, {len(events)} note 事件, note 範圍 {min((e[1] for e in events),default=0):#x}-{max((e[1] for e in events),default=0):#x}")
# piano-roll:x=事件序,y=note;每 voice 一色
COLS=max(len(v) for v in voices) if voices else 1
H=64; img=Image.new("RGB",(min(COLS,1000)*3,H*4+12),(15,15,25)); p=img.load()
cols=[(120,220,140),(220,140,120),(140,160,240),(230,210,130)]
for vi,v in enumerate(voices[:4]):
    base=vi*(H+3)
    for x,(dur,note) in enumerate(v[:1000]):
        y=base+(0x3f-note); y=max(base,min(base+H-1,y))
        for dx in range(3):
            for dy in range(3): 
                if y+dy<base+H: p[x*3+dx,y+dy]=cols[vi]
img.save(sys.argv[2]); print("->",sys.argv[2])
