# u4read_stringtable 字串抽取報告

> 自動產生 by `tools/extract_stringtable.py`(純資料抽取,不改引擎)

## 摘要

- 來源:`title.exe`、`avatar.exe`(`ultima4.zip`,Origin © 1985,不入庫)
- 機制:`u4read_stringtable`(`src/u4file.cpp:578`)
- 抽出字串總數:**114**

| section | 來源 | 數量 | 說明 |
|---|---|---|---|
| `intro_questions` | title.exe @ 0x4424 | 28 | intro.cpp:101 角色創建美德問題(gypsy 抽牌題目) |
| `intro_text` | title.exe @ continue | 24 | intro.cpp:102 開場故事字幕 |
| `intro_gypsy` | title.exe @ continue | 15 | intro.cpp:103 gypsy 抽牌旁白 |
| `codex_virtue_questions` | avatar.exe @ 0xfc7b | 11 | codex.cpp:43 知識寶典美德問答 |
| `endgame_text1` | avatar.exe @ 0xfee4 | 7 | codex.cpp:44 結局文字 1 |
| `endgame_text2` | avatar.exe @ 0x10187 | 5 | codex.cpp:45 結局文字 2 |
| `shrine_advice` | avatar.exe @ 0x16df2 | 24 | shrine.cpp:54 聖壇冥想建議 |

## 各段首句樣本

- **intro_questions**:`Entrusted to deliver an uncounted purse of gold, thou dost meet a poor beggar. Dost thou A`
- **intro_text**:`  The day is warm, yet there is a cooling breeze.  The latest in a series of personal cris`
- **intro_gypsy**:`The gypsy places the first two cards `
- **codex_virtue_questions**:`What dost thou possess if all may rely upon your every word?`
- **endgame_text1**:`The boundless knowledge of the Codex of Ultimate Wisdom is revealed unto thee.`
- **endgame_text2**:`You open your eyes to a familiar circle of stones.  You wonder of your recent adventures.`
- **shrine_advice**:`Take not the gold of others found in towns and castles for yours it is not! `

## 尚未涵蓋(後續純資料項)

- **vendor 文字**:xu4 不走 `u4read_stringtable`,在 Boron module 腳本(`module/Ultima-IV/*.b` / `script_boron.cpp`)。需另寫 Boron 腳本字串抽取。
- **417 個硬編 `screenMessage` 字面**:見 `tools/extract_hardcoded.py` / `dumps/hardcoded_strings.*`。