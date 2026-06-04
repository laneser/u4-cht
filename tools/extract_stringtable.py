#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抽取 xu4 經 `u4read_stringtable` 載入的 DOS Ultima IV 字串表
(intro / 角色創建美德問題 / gypsy / codex / endgame / shrine advice),
產出雙語表雛形(en 來自 exe,zh 待填)+ 報告。

不改引擎、不碰二進位。offset / 數量依 xu4 source:
  src/intro.cpp、src/codex.cpp、src/shrine.cpp、src/u4file.cpp:u4read_stringtable

注意:title.exe 三段為**順序讀**(introText/gypsy 用 offset=-1 接續前一段)。

用法:
  python3 tools/extract_stringtable.py \
      --data-dir data \
      --out dumps/stringtable_bilingual.json \
      --out-report dumps/stringtable_report.md
"""
import argparse
import json
import os

# 每段:(section, 檔案, offset 或 None=接續, 數量, 來源說明)
# offset=None 代表沿用前一段讀完的位置(對應 xu4 的 offset == -1)
SPECS = [
    # title.exe — intro/角色創建(順序讀)
    ("intro_questions", "title.exe", 17445 - 1, 28,
     "intro.cpp:101 角色創建美德問題(gypsy 抽牌題目)"),
    ("intro_text", "title.exe", None, 24,
     "intro.cpp:102 開場故事字幕"),
    ("intro_gypsy", "title.exe", None, 15,
     "intro.cpp:103 gypsy 抽牌旁白"),
    # avatar.exe — codex / endgame / shrine
    ("codex_virtue_questions", "avatar.exe", 0x0fc7b, 11,
     "codex.cpp:43 知識寶典美德問答"),
    ("endgame_text1", "avatar.exe", 0x0fee4, 7,
     "codex.cpp:44 結局文字 1"),
    ("endgame_text2", "avatar.exe", 0x10187, 5,
     "codex.cpp:45 結局文字 2"),
    ("shrine_advice", "avatar.exe", 93682, 24,
     "shrine.cpp:54 聖壇冥想建議"),
]


def read_strings(fh, offset, n):
    if offset is not None:
        fh.seek(offset)
    out = []
    for _ in range(n):
        b = bytearray()
        while True:
            c = fh.read(1)
            if c in (b"\x00", b""):
                break
            b += c
        out.append(b.decode("latin-1"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-report", required=True)
    args = ap.parse_args()

    handles = {}
    sections = {}
    total = 0
    for section, fname, offset, n, desc in SPECS:
        path = os.path.join(args.data_dir, fname)
        fh = handles.get(fname)
        if fh is None:
            fh = handles[fname] = open(path, "rb")
        strs = read_strings(fh, offset, n)
        sections[section] = {
            "source": f"{fname} @ {('continue' if offset is None else hex(offset) if offset > 0xfff else offset)}",
            "desc": desc,
            "count": len(strs),
            "entries": [{"idx": i, "en": s, "zh": ""} for i, s in enumerate(strs)],
        }
        total += len(strs)

    out = {
        "_meta": {
            "sources": ["title.exe", "avatar.exe"],
            "mechanism": "u4read_stringtable (xu4 src/u4file.cpp:578)",
            "total_strings": total,
            "note": "en = DOS exe 原文(= H8/codex/shrine hook 的 lookup key);zh 待填。"
                    "title.exe 三段為順序讀。vendor 文字不在此(走 Boron module 腳本,見報告)。",
        },
        "sections": sections,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # 報告
    L = ["# u4read_stringtable 字串抽取報告\n",
         "> 自動產生 by `tools/extract_stringtable.py`(純資料抽取,不改引擎)\n",
         "## 摘要\n",
         f"- 來源:`title.exe`、`avatar.exe`(`ultima4.zip`,Origin © 1985,不入庫)",
         f"- 機制:`u4read_stringtable`(`src/u4file.cpp:578`)",
         f"- 抽出字串總數:**{total}**\n",
         "| section | 來源 | 數量 | 說明 |", "|---|---|---|---|"]
    for section, fname, offset, n, desc in SPECS:
        s = sections[section]
        L.append(f"| `{section}` | {s['source']} | {s['count']} | {desc} |")
    L.append("\n## 各段首句樣本\n")
    for section, *_ in [(s[0],) for s in SPECS]:
        s = sections[section]
        sample = (s["entries"][0]["en"] if s["entries"] else "").replace("\n", " ")
        L.append(f"- **{section}**:`{sample[:90]}`")
    L.append("\n## 尚未涵蓋(後續純資料項)\n")
    L.append("- **vendor 文字**:xu4 不走 `u4read_stringtable`,在 Boron module 腳本"
             "(`module/Ultima-IV/*.b` / `script_boron.cpp`)。需另寫 Boron 腳本字串抽取。")
    L.append("- **417 個硬編 `screenMessage` 字面**:見 `tools/extract_hardcoded.py` / "
             "`dumps/hardcoded_strings.*`。")
    open(args.out_report, "w", encoding="utf-8").write("\n".join(L))

    print(f"抽出字串總數: {total}")
    for section, *_ in [(s[0],) for s in SPECS]:
        print(f"  {section}: {sections[section]['count']}")
    print(f"→ {args.out}")
    print(f"→ {args.out_report}")


if __name__ == "__main__":
    main()
