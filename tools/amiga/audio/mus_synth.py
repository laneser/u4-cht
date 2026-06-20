#!/usr/bin/env python3
"""Amiga mus*.bin → WAV(方波合成,證明旋律)。note=MIDI 半音,cmd 低 nibble=時長。
無 spec 的第一版近似:旋律 voice 用方波,多 voice 混音。"""
import sys,struct,wave,math
d=open(sys.argv[1],"rb").read()
hdr=[struct.unpack_from(">H",d,i*2)[0] for i in range(8)]
offs=sorted(set(o for o in hdr[2:7] if 0<o<len(d)))+[len(d)]
SR=22050; TICK=0.10  # 每時長單位秒數(近似)
def parse(seg):
    ev=[]; cmd=0
    for b in seg:
        if b&0x80: cmd=b
        elif 0x20<=b<0x40:
            dur=(cmd&0x0f) or 4
            ev.append((b,dur))
    return ev
def render(ev):
    buf=[]
    for note,dur in ev:
        f=440*2**((note-69)/12); n=int(SR*TICK*dur)
        for i in range(n):
            buf.append(0.25 if (i*f//SR)%2 else -0.25)  # 方波
    return buf
# 取兩條最長的 voice 當旋律+和聲,混音
voices=[parse(d[offs[i]:offs[i+1]]) for i in range(len(offs)-1)]
voices.sort(key=len,reverse=True)
tracks=[render(v) for v in voices[:2] if v]
L=max(len(t) for t in tracks)
mix=[0.0]*L
for t in tracks:
    for i,s in enumerate(t): mix[i]+=s
pcm=b"".join(struct.pack("<h",int(max(-1,min(1,s))*32767)) for s in mix)
w=wave.open(sys.argv[2],"wb");w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR)
w.writeframes(pcm);w.close()
print(f"{sys.argv[1].split('/')[-1]} → {L/SR:.1f}s, {len(voices)} voice")
