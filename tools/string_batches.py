#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用字串雙語表分批 / 合併(供平行翻譯)。支援三種檔:
  stringtable : {sections:{sec:{entries:[{idx,en,zh}]}}}   key = "sec#idx"
  hardcoded   : {strings:[{en,zh,...}]}                     key = en(唯一)
  vendor      : {strings:[{en,zh,...}]}                     key = en(唯一)

純 format / 控制字串(去掉 %s %d %c \n 空白標點後為空)自動標 zh=en,不送翻譯。

用法:
  python3 tools/string_batches.py split --file dumps/hardcoded_strings.json --kind hardcoded --batches 3
  python3 tools/string_batches.py merge --file dumps/hardcoded_strings.json --kind hardcoded
"""
import argparse
import glob
import json
import os
import re

BATCH_DIR = "dumps/batches2"


def iter_items(data, kind):
    """yield (key, item_dict);item_dict 有 'en'/'zh'。"""
    if kind == "stringtable":
        for sec, sd in data["sections"].items():
            for e in sd["entries"]:
                yield f"{sec}#{e['idx']}", e
    else:  # hardcoded / vendor
        for e in data["strings"]:
            yield e["en"], e


def is_control(en):
    """純 format/控制字串(無實際可譯文字)。"""
    stripped = re.sub(r"%[-0-9.]*[sdcuxX%]|\\n|\s|[\n\t]", "", en)
    return not re.search(r"[A-Za-z]", stripped)


def split(path, kind, nbatches):
    data = json.load(open(path, encoding="utf-8"))
    base = os.path.splitext(os.path.basename(path))[0]
    items = list(iter_items(data, kind))

    transl = [(k, it) for k, it in items if not is_control(it["en"])]
    control = [(k, it) for k, it in items if is_control(it["en"])]

    os.makedirs(BATCH_DIR, exist_ok=True)
    for old in glob.glob(f"{BATCH_DIR}/{base}_*.json"):
        os.remove(old)

    buckets = [[] for _ in range(nbatches)]
    for i, (k, it) in enumerate(transl):
        buckets[i % nbatches].append({"key": k, "en": it["en"], "zh": ""})
    for bi, b in enumerate(buckets):
        out = f"{BATCH_DIR}/{base}_{bi:02d}.json"
        json.dump({"file": base, "kind": kind, "count": len(b), "items": b},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"{base}_{bi:02d}: {len(b)} 待譯")
    print(f"  控制字串自動 zh=en(不送翻譯): {len(control)}")


def merge(path, kind):
    data = json.load(open(path, encoding="utf-8"))
    base = os.path.splitext(os.path.basename(path))[0]
    index = {k: it for k, it in iter_items(data, kind)}

    # 控制字串先 zh=en
    ctrl = 0
    for k, it in index.items():
        if is_control(it["en"]) and not it["zh"]:
            it["zh"] = it["en"]; ctrl += 1

    files = sorted(glob.glob(f"{BATCH_DIR}/{base}_*.zh.json"))
    filled = 0
    for f in files:
        bd = json.load(open(f, encoding="utf-8"))
        for item in bd["items"]:
            tgt = index.get(item["key"])
            if tgt is not None and item.get("zh"):
                tgt["zh"] = item["zh"]; filled += 1

    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    total = len(index)
    done = sum(1 for it in index.values() if it["zh"])
    print(f"{base}: 合併 {len(files)} 批,翻譯填入 {filled},控制 zh=en {ctrl}")
    print(f"  覆蓋: {done}/{total} = {done*100//max(total,1)}%")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("split", "merge"):
        p = sub.add_parser(c)
        p.add_argument("--file", required=True)
        p.add_argument("--kind", required=True, choices=["stringtable", "hardcoded", "vendor"])
        if c == "split":
            p.add_argument("--batches", type=int, default=3)
    a = ap.parse_args()
    if a.cmd == "split":
        split(a.file, a.kind, a.batches)
    else:
        merge(a.file, a.kind)


if __name__ == "__main__":
    main()
