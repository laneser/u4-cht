#!/usr/bin/env python3
"""簡易頻譜圖:顯示音高隨時間(驗證旋律 contour)。用 numpy STFT。"""
import sys,wave,struct
import numpy as np
from PIL import Image
w=wave.open(sys.argv[1],"rb"); n=w.getnframes(); sr=w.getframerate()
s=np.frombuffer(w.readframes(n),dtype=np.int16).astype(float)
# 只看前 30 秒
s=s[:sr*30]
N=2048; hop=512
cols=(len(s)-N)//hop
spec=np.zeros((N//4,cols))
win=np.hanning(N)
for c in range(cols):
    seg=s[c*hop:c*hop+N]*win
    mag=np.abs(np.fft.rfft(seg))[:N//4]
    spec[:,c]=np.log1p(mag)
spec=spec/spec.max()
H=N//4
img=Image.new("RGB",(cols,H),(0,0,0)); p=img.load()
for x in range(cols):
    for y in range(H):
        v=int(spec[y,x]*255)
        p[x,H-1-y]=(v,int(v*0.8),int(v*0.4))
img=img.resize((min(cols,900),360),Image.BILINEAR)
img.save(sys.argv[2]); print("->",sys.argv[2],f"{cols} frames {sr}Hz")
