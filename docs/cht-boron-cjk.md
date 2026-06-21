# Boron 模組 × CJK 渲染:商店亂碼 / 位移 / 缺字灰框 與翻譯涵蓋缺口

> 2026-06 實機測試商店買賣時發現一連串 CJK 顯示問題,逐一追到根因並修復。
> 本文記錄機制與修法,供日後維護與「補譯」工作參考。

相關檔案:
- 引擎:`xu4/src/script_boron.cpp`(`cf_screenMessage`)、`xu4/src/screen.cpp`(CJK 渲染)
- 模組:`xu4/module/Ultima-IV/vendors.b`
- 工具:`tools/patch_vendor_boron.py`、`tools/test_boron_cjk.cpp`(回歸測試)
- patch:`patches/engine/cht-engine.patch`(含 `cf_screenMessage` hunk)

---

## 背景:vendor 文字為何走「不同的路」

非 vendor 的玩家文字(NPC 對話、系統訊息、硬編字串)都是**英文進 C → `chtLookup` 查表 → 中文出**,翻譯與輸出全在 C 端,由 `chtSelfTest` 涵蓋。

vendor(商店)不同:中文**住在 Boron 模組** `vendors.b` 裡,經
`>>` / `=>` / `input-shop` → `construct`(代入佔位符)→ `script_boron.cpp:cf_screenMessage`
→ `screenMessage()` → `screenMessageN` → CJK 渲染。

這條「Boron 模組內 CJK → C」的路徑是 vendor 獨有,**沒有任何既有自測涵蓋**,因此一連串 bug 直到實機才現形。

---

## Bug 1:整段亂碼 + 一堆空白(UCS2 被當 UTF-8)

**症狀**:店家對白是亂碼夾雜大量空白;但按 Y/Enter 仍能買到 → 純顯示問題。

**根因**:Boron 把含 CJK(codepoint 256–65535)的字串字面存成 **UR_ENC_UCS2**
(每字 16-bit;見 Boron `ur_strInitUtf8`:≤255→Latin1、256–65535→**UCS2**、>65535→UTF-8)。
`construct` 又沿用輸入編碼。修復前 `cf_screenMessage` 直接把 buffer 的 `ptr.c` 當 UTF-8
byte 字串輸出:

```c
screenMessage(si.buf->ptr.c + si.it);   // ← UCS2 被當 UTF-8 byte 讀
```

UCS2 當 byte 讀:ASCII/空白/`^/`(如 `0x0A 0x00`)高位 0x00 → C 字串被 NUL 截斷(空白);
CJK 低位 byte → 壞 UTF-8(亂碼)。

**修法**:依 `buf->form` **自行逐 codepoint 編 UTF-8**(`chtAppendUtf8`),再
`screenMessage("%s", utf)`("%s" 防文字內 `%` 被當 printf 格式)。

> ⚠️ **不要用 `ur_toText` 寫進 UR_ENC_UTF8 buffer**(本檔 `script_reportError` 的範式)。
> 實測它按「字數」而非 UTF-8 byte 數配置容量,CJK(3 byte/字)會 **heap 溢位**
> (`corrupted size vs. prev_size`)。逐 codepoint 自編可完全繞開。

---

## Bug 2:武器/醫療/材料店「整段右移」

**症狀**:某些店進場對白整段往右位移、換行錯亂;food / inn 卻正常。

**根因**:原始英文用 `{{ 多行縮排 }}` 雙括號字串,每行有 12 格**原始碼縮排空白**。
抽取→翻譯→回填時這些空白被當成內容保留(`vendor_bilingual.json` 的 en、zh 都含)。
文字區只有 `TEXT_AREA_W = 16` 欄、`CHAR_WIDTH = 24`,12 格空白吃掉 12 欄 → 嚴重右移。
food / inn 因翻成沒縮排的單行字串而正常。

**修法**:去掉每行(`^/` 之後)的前導空白/tab → 全部靠左對齊(同 food/inn 風格)。
見 `patch_vendor_boron.py` 的 `re.sub(r"\^/[ \t]+", "^/", text)`。

---

## Bug 3:買賣物品清單「B/C/D 後面是灰白色方塊」

**症狀**:買單列出 `B`、`C`、`D` 選擇鍵正常,但其後的中文物品名是灰白色方塊。

**根因**:`vendors.b` 的 `inventory: ""` 是**空 Latin1 字串**。`build-items` 用
`append inventory rejoin [uppercase key ' ' name '^/']` 組清單:

- `append` 把 CJK 物品名塞進 Latin1 buffer 時,Boron **有損降轉**:每個中文字變 `0x BF`(¿)。
- `rejoin` 以 char(`uppercase key`)起頭也會先成 Latin1 buffer,隨後 `name` 一樣降轉。

`0xBF` 不在 CJK 字型 atlas → `cjkBlitPx` 畫灰框(`fillRect 60,60,60`)= 灰白色方塊。
(`B/C/D` 是 ASCII 所以正常。)

> 對照:`>> rejoin ["^/汝只買得起 " <數> " 份。^/"]`(L583/L652)以 **CJK 字串起頭**,
> 整個 rejoin buffer 即為 UCS2,故安全。問題只在「以 char/空字串起頭」的情形。

**修法**(`patch_vendor_boron.py`):
1. `inventory: ""` → `inventory: "　"`:種一個全形空白(U+3000)使 buffer 為 **UCS2**
   (`build-items` 會先 `clear`,種子不顯示;`clear` 保留 buffer 編碼)。
2. 把 `rejoin` 拆成逐段 `append`,讓 `name`(CJK 字串)直接 append 到已是 UCS2 的
   `inventory`,不經 rejoin 的 Latin1 中間 buffer。

實測(`tools/test_boron_cjk.cpp` 同手法):seed UCS2 + 逐段 append 字串 → `form=2`、codepoint 正確。

---

## 回歸測試

`tools/test_boron_cjk.cpp` 在**真實 Boron 直譯器**裡重現 vendor 情境(字面 / construct 價格 /
construct 多佔位店名店主 / 行首換行),用與修復後 `cf_screenMessage` 相同的轉碼比對 UTF-8,
並斷言來源確為 UCS2(證明舊路徑必壞)。執行:

```sh
bash tools/run_boron_cjk_test.sh     # 於 u4cht/xu4-allegro image 內編譯+執行
```

這補上 `chtSelfTest` 的盲區(它走 `chtLookup`,不走 Boron 字串路徑)。

---

## 翻譯涵蓋缺口(待補譯)

四大來源(對話 256 / stringtable 114 / 硬編 318 / vendor 278,約 859 entry)已全譯,但
`extract_hardcoded.py` **只抓 `screenMessage*()` 呼叫點**的字面,漏掉了:

### (a) `text = "..."` 變數賦值式硬編字串

這些檔多已有 `chtLookup` hook,只差字串沒進翻譯表:

| 檔案 | 內容 | 約數 |
|---|---|---|
| `discourse_castle.cpp` | Lord British 對白 / `help` 漸進指引 | 9+ |
| `codex.cpp` | 深淵(Abyss)結局問答 | ~11 |
| `death.cpp` | 死亡 / 復活 | ~2 |
| `shrine.cpp` | 聖壇 | ~1 |
| `item.cpp` | 部分物品使用訊息 | 數條 |

例:王城問 Lord British `help` → `discourse_castle.cpp:208`
`"Travel not the open lands alone..."` 維持英文。

### (b) NPC 名稱(`DS_NAME`)未查表

`discourse_tlk.cpp:413` `case DS_NAME: return USTR(name);` **沒有 `chtLookup`**
(對比同檔 `DS_LOOK` 有 hook、`DS_PRONOUN` 有 He/She/It→他/她/它)。
故問 NPC 名字時:`message("%s says: I am %s\n", pronoun, name)` 的格式雖譯成
「我是 %s」,但 `name`(如 `a guard`)原樣輸出 → **「我是 a guard」**。

修法:給 `DS_NAME` 加 `chtLookup` hook,並把 NPC 名稱抽取進表。NPC 名稱對應表(節錄):

| en | zh |
|---|---|
| `a guard` | 衛兵 |
| `a fighter` | 鬥士 |
| `a merchant` | 商人 |
| `a beggar` | 乞丐 |
| `a jester` | 弄臣 |

> 註:格式字串若為「我是 %s」會留一個半形空格(「我是 衛兵」)。要「我是衛兵」需同時把
> 格式改為「我是%s」(去空格),或將 zh 設為含前綴(如「一位衛兵」)。實作時擇一即可。

### 非玩家面(不需譯)

CLI `--help`、`gpu_opengl` shader 編譯錯誤、debug 訊息等掃描到的英文字面屬此類,略過。
