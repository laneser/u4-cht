#!/usr/bin/env python3
"""
read_hdm.py — Human68k FAT12 reader for X68000 Ultima IV .hdm disk images.

背景
----
X68000 版 Ultima IV(SHARP/Hudson, 1987)以 2HD 軟碟散布,映像副檔名 .hdm。
磁碟檔案系統是 Human68k FS —— 結構上就是「標準 FAT12」,但有一個關鍵差異:

    boot sector(sector 0)是 Hudson soft 自訂 boot loader,開頭即 68000 機器碼
    (`60 1c` = bra.s + OEM 字串 "Hudson soft 1.00"),**沒有標準 BPB**
    (BIOS Parameter Block)。因此 mtools / 一般 FAT 工具會回報
    "init :: non DOS media" 而拒絕掛載。

實測這套磁碟的版面參數(2HD,1232 sectors × 1024 bytes/sector,1,261,568 bytes):

    sector 0       : boot loader(Hudson,無 BPB)
    sector 1-2     : FAT #1(FAT12,media descriptor 0xFFFFFE)
    sector 3-4     : FAT #2(備份)
    sector 5-6     : root directory(32-byte entries,標準 FAT12 layout)
    sector 11+     : data region,cluster 2 起算
                     → cluster N 的資料在 sector 11 + (N - 2)
                     (sectors_per_cluster = 1)

驗證方式:Human68k .x 執行檔 magic = "HU"(0x4855)。ult4.x 目錄項 cluster=129,
預期落在 sector 11 + (129-2) = 138 —— 該 sector 確實以 "HU" 起始,
反推 data_start_sector = 11 成立。

目錄項採標準 FAT12 32-byte layout:
    [0:8]   name(空白補齊)
    [8:11]  ext
    [11]    attr
    [26:28] start cluster(little-endian)
    [28:32] size(little-endian)

已對兩片有素材的磁碟驗證可全檔抽出:
    Ultima IV (Britannia disk).hdm  → 32 檔(SWSHAPE.PAT / MAP.BIN / TALKDATA.BIN / ult4.x 等)
    Ultima IV (Program disk).hdm    → 32 檔(shape.pat / FONT.PAT / ult.mgd 音樂 / intro*.img 等)

用法
----
    python3 read_hdm.py <disk.hdm>                  # 列出檔案清單
    python3 read_hdm.py <disk.hdm> -o <out_dir>     # 抽出全部檔案到 out_dir

走 docker u4cht/extract(python3 + PIL)風格,純標準函式庫即可,無外部相依。
"""
import argparse
import os
import struct
import sys

SECTOR = 1024          # X68000 2HD: 1024 bytes/sector
FAT1_SECTOR = 1        # FAT #1 起始 sector
ROOT_SECTOR = 5        # root directory 起始 sector
ROOT_SECTORS = 2       # root dir 佔 2 sectors(64 entries)
DATA_SECTOR = 11       # cluster 2 對應的 sector(實測值,見模組 docstring)
FAT_END = 0xFF8        # FAT12 cluster chain 終止門檻


def _check_hudson_boot(data):
    """確認是 Hudson 自訂 boot(無 BPB)。回傳 True 並非硬性要求,僅作提示。"""
    return data[:2] == b"\x60\x1c" or b"Hudson soft" in data[:64]


class Fat12:
    """X68000 Human68k FAT12 解讀器(1024-byte sector,Hudson 自訂 boot 無 BPB)。"""

    def __init__(self, data):
        self.data = data
        # FAT #1 跨 FAT1_SECTOR.. 直到 root dir 之前
        self.fat = data[FAT1_SECTOR * SECTOR:ROOT_SECTOR * SECTOR]

    def fat_entry(self, cluster):
        """讀 FAT12 12-bit cluster 項。"""
        i = cluster + (cluster >> 1)  # cluster * 1.5
        if i + 1 >= len(self.fat):
            return FAT_END
        v = self.fat[i] | (self.fat[i + 1] << 8)
        return (v >> 4) if (cluster & 1) else (v & 0xFFF)

    def read_file(self, start_cluster, size):
        """依 FAT chain 讀出檔案內容(截到宣告 size)。"""
        out = bytearray()
        c = start_cluster
        guard = 0
        while 2 <= c < FAT_END and guard < 4000:
            sec = DATA_SECTOR + (c - 2)
            off = sec * SECTOR
            out += self.data[off:off + SECTOR]
            c = self.fat_entry(c)
            guard += 1
        return bytes(out[:size])

    def list_dir(self):
        """讀 root directory,回傳 [(filename, cluster, size, attr), ...]。"""
        entries = []
        for s in range(ROOT_SECTOR, ROOT_SECTOR + ROOT_SECTORS):
            base = s * SECTOR
            for e in range(SECTOR // 32):
                eo = base + e * 32
                first = self.data[eo]
                if first == 0x00:        # 目錄結束
                    break
                if first == 0xE5:        # 已刪除
                    continue
                if first < 0x20:         # 非法/控制字元起頭,跳過
                    continue
                name = self.data[eo:eo + 8].decode("ascii", "replace").rstrip()
                ext = self.data[eo + 8:eo + 11].decode("ascii", "replace").rstrip()
                attr = self.data[eo + 11]
                cluster = struct.unpack("<H", self.data[eo + 26:eo + 28])[0]
                size = struct.unpack("<I", self.data[eo + 28:eo + 32])[0]
                if cluster < 2 or not (0 < size < 4_000_000):
                    continue
                fn = f"{name}.{ext}" if ext else name
                entries.append((fn, cluster, size, attr))
        return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hdm", help="X68000 .hdm 磁碟映像")
    ap.add_argument("-o", "--out", help="抽檔輸出目錄(省略則僅列清單)")
    args = ap.parse_args()

    data = open(args.hdm, "rb").read()
    if not _check_hudson_boot(data):
        print("[warn] boot sector 非預期的 Hudson 格式,參數可能不符,仍嘗試解讀。",
              file=sys.stderr)

    fs = Fat12(data)
    files = fs.list_dir()
    print(f"# {len(files)} files in {os.path.basename(args.hdm)}")
    print(f"{'name':14s} {'cluster':>8s} {'size':>9s}  attr")
    for fn, clus, size, attr in files:
        print(f"{fn:14s} {clus:8d} {size:9d}  {attr:02x}")

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        for fn, clus, size, attr in files:
            safe = fn.replace("/", "_")
            with open(os.path.join(args.out, safe), "wb") as f:
                f.write(fs.read_file(clus, size))
        print(f"\n# extracted {len(files)} files -> {args.out}")


if __name__ == "__main__":
    main()
