#!/usr/bin/env python3
"""MGD 單 track → YM2151 register events(用 ch0)。
事件:0x92 nn=選 voice;note(<0x80)+dur 對=發音;0xff=結束;其他 0x8x yy=控制(略)。
note→KC:YM2151 KC 非線性(每 octave 12 半音,跳 3/7/11/15)。"""
import sys
d=open(sys.argv[1],"rb").read()
trk_idx=int(sys.argv[2]); out=sys.argv[3]
import struct
# track table @ header[2]
ttab=struct.unpack_from(">H",d,4)[0]
toff=struct.unpack_from(">H",d,ttab+trk_idx*2)[0]
print(f"track table@{ttab:#x} track{trk_idx}@{toff:#x}")
KC=[0,1,2,4,5,6,8,9,10,12,13,14]
def note_kc(n):
    return ((n//12)<<4)|KC[n%12]
def voice_regs(vn):
    base=0x09+(vn-1)*0x2a; p=d[base+1:base+25]; cf=d[base+25]
    ev=[(0x20,0xC0|(cf&0x3f))]; SLOT=[0,8,16,24]
    pr=[p[i*4:i*4+4] for i in range(6)]
    for op in range(4):
        s=SLOT[op]
        ev+= [(0x40+s,pr[0][op]&0x7f),(0x60+s,pr[1][op]&0x7f),(0x80+s,pr[2][op]&0x1f),
              (0xA0+s,pr[3][op]&0x9f),(0xC0+s,pr[4][op]&0x9f),(0xE0+s,pr[5][op])]
    return ev
events=[]; i=toff; TICK=900  # 每 dur 單位的取樣數
def emit(a,v,w=0): events.append((a,v,w))
cur_voice=1
for a,v in voice_regs(1): emit(a,v)
n=0
while i<len(d) and n<400:
    b=d[i]
    if b==0xff: break
    if b&0x80:
        cmd=b; param=d[i+1] if i+1<len(d) else 0; i+=2
        if cmd==0x92:  # voice select
            for a,v in voice_regs(param or 1): emit(a,v)
        # 其他控制略過
    else:
        note=b; dur=d[i+1] if i+1<len(d) else 8; i+=2; n+=1
        emit(0x28, note_kc(note))
        emit(0x30, 0x00)
        emit(0x08, 0x78, dur*TICK)   # KON,持續 dur
        emit(0x08, 0x00, TICK//4)    # KOFF 短 gap
fo=open(out,"w")
for a,v,w in events: fo.write(f"{a:02x} {v:02x} {w}\n")
fo.close()
print(f"{n} 音符 → {out}")
