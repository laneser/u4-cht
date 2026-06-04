# U4 中文化共享 Glossary(翻譯權威詞表)

> 所有平行翻譯 agent **必須**遵守本表,確保術語一致(避免 U6 坑 #7 術語漂移)。
> 譯名體系沿用台灣《創世紀聖者之書》+ u6-cht,與 Ultima 系列一致。

## 翻譯總則

- **文白並用**:古英文 thee/thou/thy/hath/dost 對應半文言;避免太白(嗨)或太古(之乎者也過頭)。
  - `thee/thou` → 汝；`thy` → 汝之；`thou art` → 汝乃。
- 語氣中性莊重,保留 Ultima 的史詩感。NPC 各有身分(法師、衛兵、乞丐、孩童)語氣略調整。
- **保留佔位/控制字元原樣**:`\n`(換行)、`%s`/`%d`/`%c` 等不動。
- **長度**:U4 文字框窄,譯文盡量精簡(中文比英文短,通常沒問題);保留原 `\n` 斷行位置。

## 欄位特別規則

| 欄位 | 規則 |
|---|---|
| `name` | NPC 名:知名角色用下方固定譯名;一般人名音譯;角色化名稱(a guard / a child)意譯為「衛兵 / 孩童」等 |
| `pronoun` | He→他、She→她、It→它 |
| `description` | 「a charming bard.」→「一位迷人的吟遊詩人。」保留句末句點 |
| `health` | Good.→好。 Well.→安好。 Fair.→尚可。 Poor.→欠佳。(固定) |
| `keyword_1` / `keyword_2` | **不譯,zh 留空字串 ""**。這是玩家輸入的指令關鍵字(英文 4 字),維持英文 |
| 其餘對白 | 文白並用翻譯 |

## 核心專有名詞(固定譯名)

| 英文 | 中文 |
|---|---|
| Avatar | 聖者 |
| Stranger | 異鄉人 |
| Lord British | 不列顛王 |
| Britannia | 不列顛尼亞 |
| Codex of Ultimate Wisdom | 知識寶典 |
| Mondain / Minax / Exodus | 蒙丹 / 米娜克斯 / 米索 |
| moongate | 月之門 |
| shrine | 聖壇 |
| rune | 符文 |
| mantra | 真言 |
| gypsy | 吉普賽人 |
| virtue | 美德 |
| dungeon | 地牢 |
| Mystic Arms / Mystic Robes | 神秘武器 / 神秘長袍 |

## 八德 / 城市 / 真言 / 職業

| 美德 | 中文 | 真言 | 城市 | 城市中文 | 職業 | 職業中文 |
|---|---|---|---|---|---|---|
| Honesty | 誠實 | ahm | Moonglow | 月光城 | Mage | 法師 |
| Compassion | 慈悲 | mu | Britain | 不列顛城 | Bard | 吟遊詩人 |
| Valor | 勇敢 | ra | Jhelom | 哲倫 | Fighter | 戰士 |
| Justice | 正義 | beh | Yew | 紫衫城 | Druid | 德魯依 |
| Sacrifice | 犧牲 | cah | Minoc | 米諾克 | Tinker | 技工 |
| Honor | 榮譽 | summ | Trinsic | 特林希克 | Paladin | 聖騎士 |
| Spirituality | 靈性 | om | Skara Brae | 史卡拉布雷 | Ranger | 遊俠 |
| Humility | 謙卑 | lum | New Magincia | 新馬精西亞 | Shepherd | 牧人 |

其他地名:Lycaeum→學院（Lyceum 學院）、Cove→寇夫、Paws→帕斯、Vesper→維斯帕、Den→丹恩、Serpent's Hold→巨蛇要塞、Empath Abbey→共感修道院、Castle Britannia / LCB→不列顛城堡（Lord British 城堡）。

## 八位夥伴 / 知名 NPC 固定譯名

| 英文 | 中文 | 備註 |
|---|---|---|
| Iolo | 尤洛 | 吟遊詩人夥伴 |
| Dupre | 壯普雷 | 聖騎士夥伴 |
| Shamino | 夏米諾 | 遊俠夥伴 |
| Geoffrey | 傑佛瑞 | 戰士 |
| Mariah | 瑪萊雅 | 法師 |
| Julia | 茱莉雅 | 技工 |
| Katrina | 卡崔娜 | 牧人 |
| Jaana | 雅娜 | 德魯依 |
| Sentri | 山特利 | |
| Lord British | 不列顛王 | 自稱「朕」,稱聖者「卿」 |
| Hawkwind | 霍克溫 | 靈魂先知 |

## 施法材料 / 物品(若出現)

硫磺灰(sulfurous ash)、大蒜(garlic)、人蔘(ginseng)、蜘蛛絲(spider silk)、血苔(blood moss)、黑珍珠(black pearl)、夜影(nightshade)、曼陀羅根(mandrake root)。

## 風格範例

| 英文 | ✅ 採用 |
|---|---|
| a charming bard. | 一位迷人的吟遊詩人。 |
| Do you like my music? | 汝喜愛我的樂曲嗎？ |
| I would join thee! | 我願追隨汝！ |
| A shame. | 真是可惜。 |
| Welcome friend! | 歡迎，朋友！ |

> 新增同義詞 / 不確定譯名前,先回報釐清,勿各自發揮。
