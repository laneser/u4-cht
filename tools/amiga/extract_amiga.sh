#!/usr/bin/env bash
# 從使用者自有的 Amiga U4(WHDLoad 包已解)抽出 Amiga 主題 tileset。
#   U4SH.LWZ --(xu4 LZW)--> 32B palette + 256 tile --(逐列交錯 bitplane)--> tileset PNG
# 需 xu4 源碼(lzw 解碼器)+ docker u4cht/xu4-allegro(編 lzw_unpack)+ u4cht/extract(PIL)。
# 用法:bash extract_amiga.sh <U4SH.LWZ> <xu4_src_dir> <out_tileset.png>
set -euo pipefail
LWZ="${1:?需 U4SH.LWZ}"; XSRC="${2:?需 xu4/src}"; OUT="${3:?需輸出 png}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; WORK="$(mktemp -d)"
# 1) 編 LZW 解碼器(連 xu4 lzw 源碼)
docker run --rm --entrypoint bash -v "$XSRC:/src" -v "$ROOT/tools/amiga:/t" -v "$WORK:/w" \
  u4cht/xu4-allegro -c 'cd /src && gcc -I. /t/lzw_unpack.c lzw/u4decode.cpp lzw/lzw.c lzw/hash.c -lstdc++ -o /w/lzwu'
# 2) 解壓(skip=0)
cp "$LWZ" "$WORK/in.lwz"
docker run --rm --entrypoint /w/lzwu -v "$WORK:/w" u4cht/xu4-allegro /w/in.lwz /w/dec.bin 0
# 3) 解碼成 tileset
docker run --rm --entrypoint python3 -v "$ROOT/tools/amiga:/t" -v "$WORK:/w" \
  u4cht/extract:latest /t/build_amiga_tileset.py /w/dec.bin "/w/out.png"
cp "$WORK/out.png" "$OUT"; rm -rf "$WORK"
echo "完成:Amiga tileset → $OUT"
