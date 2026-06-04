# 硬編 screenMessage 字串抽取報告

> 自動產生 by `tools/extract_hardcoded.py`(純靜態分析,不改引擎)

## 摘要

- 有字面引數的 call site:**420**
- 去重後唯一字串:**318**
- 含 format specifier(`%s`/`%d`…,需 format-aware hook):**128**
- 第一引數為變數(dynamic,不入翻譯表):**26**

### 各函式 call site(有字面)

| 函式 | 數 |
|---|---|
| `screenMessage` | 405 |
| `screenTextAt` | 14 |
| `screenMessageN` | 1 |

## 最高頻字串(前 25)

| 次數 | format? | 字串(escape 顯示) |
|---|---|---|
| 10 |  | `\n` |
| 10 | 是 | `%s\n` |
| 8 | 是 | `%s` |
| 6 |  | `\nHmm...No effect!\n` |
| 5 | 是 | `%cNot here!%c\n` |
| 4 | 是 | `%cNot Here!%c\n` |
| 4 |  | `Dir: ` |
| 4 | 是 | `Music: %d%s\n` |
| 4 |  | `Not here!\n` |
| 4 | 是 | `Sound: %d%s\n` |
| 3 |  | `\nHmmm--No Effect!\n` |
| 3 |  | `\nNone owned!\n` |
| 3 |  | `\nPassage is not granted.\n\n` |
| 3 | 是 | `%c` |
| 3 | 是 | `%cBlocked!%c\n` |
| 3 | 是 | `%cNone left!%c\n` |
| 3 | 是 | `%cSlow progress!%c\n` |
| 3 |  | `Leaving...\n` |
| 3 |  | `Missed!\n` |
| 2 |  | `\n\n` |
| 2 | 是 | `\n\n%s` |
| 2 | 是 | `\n%cYou don't have enough reagents to mix %d spells!%c\n` |
| 2 | 是 | `\n%s` |
| 2 | 是 | `\n%s\n` |
| 2 |  | `\nNo place to Use them!\n` |

## Dynamic(第一引數為變數)前 15 筆

這些 call 的文字來自 runtime 變數(如對話 reply / 角色名),走 H1 hook 的查表 + fragment 替換,不在硬編表內。

- `screenMessage` @ creature.cpp:14
- `screenMessage` @ combat.cpp:643
- `screenMessage` @ discourse_tlk.cpp:65
- `screenMessage` @ script_boron.cpp:290
- `screenMessage` @ screen.cpp:399
- `screenMessageN` @ screen.cpp:413
- `screenMessageN` @ screen.cpp:446
- `screenMessageN` @ screen.cpp:449
- `screenMessageCenter` @ screen.cpp:419
- `screenTextAt` @ screen.cpp:353
- `screenMessage` @ screen.h:133
- `screenMessageN` @ screen.h:135
- `screenMessageCenter` @ screen.h:134
- `screenTextAt` @ screen.h:140
- `screenMessage` @ death.cpp:108