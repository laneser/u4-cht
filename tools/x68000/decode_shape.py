#!/usr/bin/env python3
"""
decode_shape.py — X68000 Ultima IV tileset (SWSHAPE.PAT / shape.pat) 解碼器。

輸入 read_hdm.py 抽出的 SWSHAPE.PAT(Britannia disk,62464 bytes)或
shape.pat(Program disk,212544 bytes),解成可檢視的 PNG 接觸表(sprite sheet)。

格式現況(recon 已確認 / 仍待 pixel-perfect 校正)
-------------------------------------------------
已確認:
  * 無壓縮(gzip 再壓比 ≈1.0;對照 .LWZ 的 Amiga 版才是 LZW 壓縮)。
  * 4bpp / 16 色。X68000 GVRAM 原生即 16 色。
  * tile 基本尺寸 16×16(U4 標準 tile)。
  * 以 chunky-4bpp(2 px/byte,row-major,8 byte/row,128 byte/tile)解碼時,
    已能 dump 出可辨識字形(數字 "2"/"$"/"0"/"1" 清晰)→ 證明 pixel 資料就在裡面。

TODO(尚未定到 pixel-perfect,本工具預設 chunky4 但保留 planar 模式):
  * chunky4 模式下,字元呈「8px 寬成對 + 水平錯位」,強烈暗示真實排列可能是
    **planar(4 個 bitplane 分離)** 而非 chunky nibble,或 tile 內部以 8×16
    為單位再組成 16×16。需對 ult4.x / init.x 內的繪圖常式反組譯確認
    plane 排列(連續 / word-interleaved)與 row stride。
  * 調色盤未定:X68000 16 色 palette 應在 ult4.x / init.x 的初始化碼或
    某 .PAT/.DAT 內(GVRAM palette 暫存器寫入)。目前用灰階占位,
    可用 --palette 餵入外部 RGB 表(見下)。

用法
----
    python3 decode_shape.py <SWSHAPE.PAT> -o sheet.png
    python3 decode_shape.py <shape.pat>  -o sheet.png --mode planar --tile 16x16
    python3 decode_shape.py <SWSHAPE.PAT> -o sheet.png --palette pal.bin   # 16*3 bytes RGB

走 docker u4cht/extract(python3 + Pillow)。
"""
import argparse

from PIL import Image

# 占位灰階 palette(16 色);bg(0)用深藍以便看出 tile 邊界。真實 palette 待抽。
DEFAULT_PALETTE = [(0, 0, 80)] + [
    (16 * i, 16 * i, 16 * i) for i in range(1, 16)
]


def load_palette(path):
    """讀 16*3 = 48 bytes 的 RGB palette;不足則退回預設。"""
    if not path:
        return DEFAULT_PALETTE
    raw = open(path, "rb").read()
    if len(raw) < 48:
        return DEFAULT_PALETTE
    return [(raw[i * 3], raw[i * 3 + 1], raw[i * 3 + 2]) for i in range(16)]


def decode_tile_chunky4(data, off, tw, th, pal):
    """chunky 4bpp:2 px/byte,row-major,(tw//2) byte/row。已驗證可 dump 字形。"""
    img = Image.new("RGB", (tw, th))
    px = img.load()
    row_bytes = tw // 2
    for y in range(th):
        for x in range(tw):
            bi = off + y * row_bytes + x // 2
            if bi >= len(data):
                continue
            b = data[bi]
            v = (b >> 4) if (x % 2 == 0) else (b & 0x0F)
            px[x, y] = pal[v]
    return img


def decode_tile_planar(data, off, tw, th, pal):
    """planar 4bpp:4 個 bitplane 連續存放,每 plane (tw//8)*th bytes。

    TODO: plane 排列(連續 vs word-interleaved)與 bit 順序待從繪圖常式反組譯確認;
    這裡先用「連續 plane、MSB-first」最常見假設。
    """
    img = Image.new("RGB", (tw, th))
    px = img.load()
    plane_bytes = (tw // 8) * th
    for y in range(th):
        for x in range(tw):
            v = 0
            for p in range(4):
                po = off + p * plane_bytes + y * (tw // 8) + x // 8
                if po >= len(data):
                    bit = 0
                else:
                    bit = (data[po] >> (7 - (x % 8))) & 1
                v |= bit << p
            px[x, y] = pal[v]
    return img


DECODERS = {"chunky4": decode_tile_chunky4, "planar": decode_tile_planar}


def parse_tile(s):
    w, h = s.lower().split("x")
    return int(w), int(h)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shape", help="SWSHAPE.PAT 或 shape.pat")
    ap.add_argument("-o", "--out", default="shape_sheet.png", help="輸出 PNG")
    ap.add_argument("--mode", choices=DECODERS, default="chunky4",
                    help="解碼模式(預設 chunky4;planar 待校正)")
    ap.add_argument("--tile", default="16x16", help="tile 尺寸 WxH(預設 16x16)")
    ap.add_argument("--cols", type=int, default=16, help="接觸表每列 tile 數")
    ap.add_argument("--scale", type=int, default=3, help="輸出 nearest 放大倍率")
    ap.add_argument("--palette", help="16*3 bytes RGB palette(省略用灰階占位)")
    args = ap.parse_args()

    data = open(args.shape, "rb").read()
    tw, th = parse_tile(args.tile)
    bpt = (tw * th) // 2          # 4bpp = 0.5 byte/px,chunky 與 planar 同 size
    pal = load_palette(args.palette)
    decode = DECODERS[args.mode]

    ntile = len(data) // bpt
    rows = (ntile + args.cols - 1) // args.cols
    sheet = Image.new("RGB",
                      (args.cols * (tw + 2), rows * (th + 2)), (30, 30, 30))
    for i in range(ntile):
        tile = decode(data, i * bpt, tw, th, pal)
        ox = (i % args.cols) * (tw + 2) + 1
        oy = (i // args.cols) * (th + 2) + 1
        sheet.paste(tile, (ox, oy))

    if args.scale > 1:
        sheet = sheet.resize((sheet.width * args.scale, sheet.height * args.scale),
                             Image.NEAREST)
    sheet.save(args.out)
    print(f"# {args.shape}: {len(data)} bytes, {ntile} tiles "
          f"({tw}x{th}, {args.mode}) -> {args.out}")


if __name__ == "__main__":
    main()
