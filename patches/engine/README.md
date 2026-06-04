# xu4 繁中化引擎 patch

把 U4 中文化(en→zh load-time 查表 + CJK 點陣字渲染)套到上游 xu4。
`xu4/` 不入庫,本目錄保存所有引擎改動以供重現。

## 內容

| 檔案 | 說明 |
|---|---|
| `cht.h` / `cht.cpp` | 新模組:載入 `cjk_font.bin`/`u4_cht.tab`,提供 `chtLookup`(en→zh,二分查找)+ `chtGlyph`(CJK 16×16 alpha) |
| `cht-engine.patch` | 改 `src/screen.cpp`(+`cjkBlit`/`screenMessageCJK`/H1 hook/self-test)、`project.b`、`src/Makefile.common`(編譯掛載) |

## 套用

```bash
bash tools/apply_cht.sh            # 預設套到 ./xu4
docker build -f docker/Dockerfile.zh -t u4cht/xu4-allegro xu4
```

## Hook 點(對應 docs/P3-hooks.md)

- **H1 `screenMessageN`**:進入時 `chtLookup(buffer, buflen)`;命中 → `screenMessageCJK(zh)` 渲染後 return(load-time 替換,不改原 bytecode)。
- **H2 glyph**:`cjkBlit` 把 16×16 CJK **灰階 alpha 混色**(白字混黑底,二值 atlas 亦相容)blit 到 `xu4.screenImage`(全形佔 2 欄,行距 2)。
- **self-test**:`screenRender()` 開頭 `chtSelfTest()`,env `U4CHT_SELFTEST=1` 時用真實 `chtLookup` 渲染已知 en,headless 驗證全鏈路。

## 已知限制(PoC 階段)

- 文字區僅 16 欄 × 12 列 @ 8px → CJK 16×16 每行 8 字、6 行;長對白需更細的 CJK-aware 換行/捲動。
- 含 `%s/%d` format 的硬編字串在 runtime 已被替換,format 字串 key 不命中 → 需 format-aware / fragment(後續)。
- vendor 文字走 Boron `>>`,是否經 `screenMessageN` 待驗;NPC 對話 + stringtable 已確認命中。
