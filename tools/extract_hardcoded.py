#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抽取 xu4 source 內硬編的 `screenMessage("…")` 字面字串(及 screenMessageN/
screenTextAt 的字面),產出去重字串清單(en + zh 待填)+ 報告。

純靜態分析,不改引擎、不執行。處理:
  - C 相鄰字串自動串接:screenMessage("a " "b")
  - escape 解碼(\\n \\t \\" \\\\ 等)→ 真實字元(% format specifier 保留原樣)
  - 第一個引數非字面(變數,如 screenMessage(reply))→ 記為 dynamic,不入翻譯表

用法:
  python3 tools/extract_hardcoded.py \
      --src-dir xu4/src \
      --out dumps/hardcoded_strings.json \
      --out-report dumps/hardcoded_report.md
"""
import argparse
import json
import os
import re

# 鎖定的文字函式:函式名 → 字面引數是第幾個(0-based)
FUNCS = {
    "screenMessage": 0,
    "screenMessageN": 0,
    "screenMessageCenter": 0,
    "screenTextAt": 2,   # (x, y, fmt, …)
}

ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\",
           "0": "\0", "a": "\a", "b": "\b", "f": "\f", "v": "\v", "'": "'"}


def parse_string_literals(s, i):
    """從 s[i] 起(應為 '"')解析一或多個相鄰 C 字串字面,回傳 (decoded, next_i)。
    若 s[i] 非 '"' 回傳 (None, i)。"""
    n = len(s)
    # 跳過前導空白
    while i < n and s[i] in " \t\r\n":
        i += 1
    if i >= n or s[i] != '"':
        return None, i
    out = []
    while i < n and s[i] == '"':
        i += 1  # skip opening quote
        while i < n and s[i] != '"':
            if s[i] == "\\" and i + 1 < n:
                out.append(ESCAPES.get(s[i + 1], s[i + 1]))
                i += 2
            else:
                out.append(s[i])
                i += 1
        i += 1  # skip closing quote
        # 跳過相鄰字面間的空白
        j = i
        while j < n and s[j] in " \t\r\n":
            j += 1
        if j < n and s[j] == '"':
            i = j
        else:
            break
    return "".join(out), i


def skip_args(s, i, count):
    """從 '(' 之後跳過 count 個引數(以頂層逗號分隔),回傳逗號後位置。"""
    n = len(s)
    depth = 0
    skipped = 0
    while i < n and skipped < count:
        c = s[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                return None  # 引數不足
            depth -= 1
        elif c == '"':
            _, i = parse_string_literals(s, i)
            continue
        elif c == "," and depth == 0:
            skipped += 1
        i += 1
    return i


def extract_file(path, results, dynamic):
    text = open(path, encoding="utf-8", errors="replace").read()
    rel = path
    for fname, argpos in FUNCS.items():
        for m in re.finditer(r"\b%s\s*\(" % re.escape(fname), text):
            i = m.end()  # just after '('
            if argpos > 0:
                i = skip_args(text, i, argpos)
                if i is None:
                    continue
            lit, _ = parse_string_literals(text, i)
            line = text.count("\n", 0, m.start()) + 1
            if lit is None:
                dynamic.append({"func": fname, "file": rel, "line": line})
            else:
                results.append({"func": fname, "file": rel, "line": line, "en": lit})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-report", required=True)
    args = ap.parse_args()

    results, dynamic = [], []
    for root, _, files in os.walk(args.src_dir):
        for fn in files:
            if fn.endswith((".cpp", ".c", ".h")):
                extract_file(os.path.join(root, fn), results, dynamic)

    # 去重(以 en 為 key),保留出現位置
    uniq = {}
    for r in results:
        e = uniq.setdefault(r["en"], {"en": r["en"], "zh": "",
                                      "has_format": bool(re.search(r"%[-0-9.]*[sdcuxX%]", r["en"])),
                                      "occurrences": []})
        e["occurrences"].append({"func": r["func"],
                                 "at": f"{os.path.relpath(r['file'], args.src_dir)}:{r['line']}"})

    entries = sorted(uniq.values(), key=lambda x: (-len(x["occurrences"]), x["en"]))
    fmt_n = sum(1 for e in entries if e["has_format"])

    out = {
        "_meta": {
            "source": "xu4/src(靜態抽取 screenMessage/N/Center/TextAt 字面)",
            "total_call_sites_with_literal": len(results),
            "unique_strings": len(entries),
            "with_format_specifier": fmt_n,
            "dynamic_first_arg": len(dynamic),
            "note": "en = 硬編格式字串(含 %s/%d、\\n);zh 待填。含 % 者於 H1 hook "
                    "需 format-aware 處理(post-vsnprintf 比對 / fragment 替換)。",
        },
        "strings": entries,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 報告
    by_func = {}
    for r in results:
        by_func[r["func"]] = by_func.get(r["func"], 0) + 1
    L = ["# 硬編 screenMessage 字串抽取報告\n",
         "> 自動產生 by `tools/extract_hardcoded.py`(純靜態分析,不改引擎)\n",
         "## 摘要\n",
         f"- 有字面引數的 call site:**{len(results)}**",
         f"- 去重後唯一字串:**{len(entries)}**",
         f"- 含 format specifier(`%s`/`%d`…,需 format-aware hook):**{fmt_n}**",
         f"- 第一引數為變數(dynamic,不入翻譯表):**{len(dynamic)}**\n",
         "### 各函式 call site(有字面)\n", "| 函式 | 數 |", "|---|---|"]
    for f, c in sorted(by_func.items(), key=lambda x: -x[1]):
        L.append(f"| `{f}` | {c} |")
    L.append("\n## 最高頻字串(前 25)\n")
    L.append("| 次數 | format? | 字串(escape 顯示) |")
    L.append("|---|---|---|")
    for e in entries[:25]:
        disp = e["en"].replace("\n", "\\n").replace("\t", "\\t")
        L.append(f"| {len(e['occurrences'])} | {'是' if e['has_format'] else ''} | `{disp[:70]}` |")
    L.append(f"\n## Dynamic(第一引數為變數)前 15 筆\n")
    L.append("這些 call 的文字來自 runtime 變數(如對話 reply / 角色名),"
             "走 H1 hook 的查表 + fragment 替換,不在硬編表內。\n")
    for d in dynamic[:15]:
        L.append(f"- `{d['func']}` @ {os.path.relpath(d['file'], args.src_dir)}:{d['line']}")
    open(args.out_report, "w", encoding="utf-8").write("\n".join(L))

    print(f"call site(字面): {len(results)}  唯一: {len(entries)}  "
          f"含 format: {fmt_n}  dynamic: {len(dynamic)}")
    print(f"各函式: {by_func}")
    print(f"→ {args.out}\n→ {args.out_report}")


if __name__ == "__main__":
    main()
