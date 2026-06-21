# 多平台 tileset 解碼經驗(Amiga / FM Towns)

把 Amiga 與 FM Towns 版 Ultima IV 的 256-tile shapes 解成 xu4 可用的 `16×4096`
tileset 時,各踩到一個「形狀對、顏色全錯」的解碼 bug。兩者根因不同,但定位方法一樣,
記在這裡供日後處理 X68000 / MSX2 / SMS 等其他平台時參考。

對應工具:`tools/amiga/build_amiga_tileset.py`、`tools/build_fmtowns_tileset.py`。
版權遊戲資料(shapes / TIL)不入 repo,放使用者本機 `materals/`;這裡只記格式與方法。

## 共通方法:用「已知顏色」當錨點,先 dump 再下結論

不要盲試解碼參數。每塊 16×16 tile 在 canonical U4 256-tile 順序裡的位置是固定的,
其中有幾塊顏色是「常識已知」的,拿來當判斷錨點最快:

| slot | tile | 應有顏色 |
|---|---|---|
| 0 / 1 | sea / water | 以**藍**為主 |
| 4 | grass | **綠** |
| 6 | forest | 綠(樹) |
| 8 | mountains | 灰 |
| 31 | avatar | 人形 + 膚色 |
| 32–47 | mage/bard/… | 人形,各 2 影格(`frames: 2 animation: frame`)|

流程:

1. **先 dump 原始位元組**,別急著套解碼器。挑一塊結構單純的 tile(海水通常是規律波紋),
   把它的 raw bytes 印成二進位,人眼找規律。
2. **解碼後立刻 render 錨點 tile**(水 / 草 / avatar)放大看,判斷「水是不是藍、草是不是綠、
   人物是不是人形且顏色合理」。
3. 形狀對但顏色錯 → 多半是**色彩維度**的問題(plane 位元組合 / 像素格式),不是空間排列;
   形狀也錯(雜訊 / 條紋)→ 是**空間維度**(byte 分組 / 像素順序 / 影像是否為連續 tile 或整張 raster)。
4. 暴搜要有**評分函式**(例:水的藍像素數 + 草的綠像素數;或「相鄰像素色變少 = 平滑 = 較可能正確」),
   不要靠肉眼掃幾十張圖。

## Amiga:bitplane 的 byte 分組

- **格式**:`U4SH.LWZ` 經 xu4 的 12-bit LZW 解壓(`tools/amiga/lzw_unpack.c`,skip=0)得
  `32 byte 調色盤(16 色 Amiga 0x0RGB)+ 256 tile × 128 byte`。每 tile 16×16 × 4 bitplane
  (4bpp = 16 色)。
- **bug**:解碼器把每 row 的 8 byte 當成「每個 plane 的 2 byte 相鄰」
  (`tb[r*8 + pl*2 + byi]`)。實際 Amiga 是**交錯式**:每 row 8 byte = 兩半
  (pixels 0–7 / 8–15),每半 4 byte = plane0..3 各 1 byte。錯誤分組下只有 plane0 生效,
  顏色全錯(水的 index 變 1=紅 而非 3=藍)。
- **定位**:dump 海水 tile r0 = `00011000 00011000 00000000 …`。在錯排列下只 plane0 有值
  → index 1(紅);在正確排列下 byte0=plane0、byte1=plane1 → pixel 3,4 = plane0+plane1 =
  index 3 = **藍**,與水色相符 → 確認排列。
- **修法**:`out[r*16 + h*8 + bit] |= 1 << pl`,`bb = tb[r*8 + h*4 + pl]`(h=哪一半、pl=plane)。
  一行之差。先前怎麼暴搜 plane **順序**都不對,因為錯的是 byte **分組方式**。

## FM Towns:16-bit 直色,但非標準 RGB565

- **格式**:`ULTIMA4.TIL`(光碟 `U4OPEN/U4_J|U4_E/`)= 256 個連續 16×16 tile,每像素 2 byte
  16-bit **直色**(無調色盤、無 bitplane),共 `256×16×16×2 = 131072` byte。
- **bug**:原解碼器當標準 RGB565 LE,解出的水偏**紫**(紅+藍)。實測 RGB565 / RGB555 /
  BGR 的 LE/BE 各變體**都解不出藍水**;把整檔當 256×256 raster 也是雜訊。FM Towns 的
  16-bit 像素位元佈局確切為何,本次未解開。
- **繞過**:`materals/fmtowns/mshapes4.png` 是同份 shapes 已正確還原的圖(1024×1024 =
  16×16 格 × 每格 64×64,canonical 順序)。改成從它逐格抽出、降採樣回 16×16、堆成
  `16×4096`,整套乾淨。`build_fmtowns_tileset.py` 因此改吃 `--msh`,TIL 直解留待日後補。
- **教訓**:形狀對(tile-by-tile 結構沒錯)但顏色錯且各 16-bit 變體都不對時,代表是
  非標準的私有像素格式;手邊若有已知正確的參考圖,直接採用比硬解私有格式划算。

## 留待日後

- FM Towns `ULTIMA4.TIL` 的 16-bit 像素格式(需反查 FM Towns 顯示晶片或遊戲繪圖常式)。
- X68000(`docs/x68000-mgd-format.md`)、MSX2、SMS(`docs/sms-tileset-extraction.md`)
  尚未納入 build;處理時沿用上面「錨點 + 先 dump + 形狀/顏色二分」的方法。
