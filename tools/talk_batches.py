#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
talk_bilingual.json 分批(供平行翻譯)/ 合併(回填 zh)。

split: 依城(tlk_file)分成 N 批 → dumps/batches/batch_NN.json
merge: 讀 dumps/batches/batch_NN.zh.json 的 zh → 回填 talk_bilingual.json

用法:
  python3 tools/talk_batches.py split --in dumps/talk_bilingual.json --batches 8
  python3 tools/talk_batches.py merge --in dumps/talk_bilingual.json
"""
import argparse
import glob
import json
import os

BATCH_DIR = "dumps/batches"


def split(infile, nbatches):
    data = json.load(open(infile, encoding="utf-8"))
    npcs = data["npcs"]
    # 依城分組,城再平均分配到 nbatches 批(保持同城在同批)
    towns = {}
    for n in npcs:
        towns.setdefault(n["tlk_file"], []).append(n)
    town_names = sorted(towns)
    buckets = [[] for _ in range(nbatches)]
    for i, t in enumerate(town_names):
        buckets[i % nbatches].extend(towns[t])

    os.makedirs(BATCH_DIR, exist_ok=True)
    for old in glob.glob(f"{BATCH_DIR}/batch_*.json"):
        os.remove(old)
    for bi, bucket in enumerate(buckets):
        items = []
        for n in bucket:
            items.append({
                "key": f"{n['tlk_file']}:{n['conv_index']}",
                "name": n["name"],
                "fields": {f: {"en": v["en"], "zh": v["zh"]}
                           for f, v in n["fields"].items()},
            })
        out = f"{BATCH_DIR}/batch_{bi:02d}.json"
        json.dump({"batch": bi, "towns": sorted({i["key"].split(":")[0] for i in items}),
                   "count": len(items), "npcs": items},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"batch_{bi:02d}: {len(items)} NPC  towns={sorted({i['key'].split(':')[0] for i in items})}")


def merge(infile):
    data = json.load(open(infile, encoding="utf-8"))
    index = {f"{n['tlk_file']}:{n['conv_index']}": n for n in data["npcs"]}
    filled = 0
    files = sorted(glob.glob(f"{BATCH_DIR}/batch_*.zh.json"))
    if not files:
        print("找不到 batch_*.zh.json"); return
    for f in files:
        bd = json.load(open(f, encoding="utf-8"))
        for item in bd["npcs"]:
            tgt = index.get(item["key"])
            if not tgt:
                continue
            for field, v in item["fields"].items():
                zh = v.get("zh", "")
                if field in tgt["fields"]:
                    tgt["fields"][field]["zh"] = zh
                    if zh:
                        filled += 1
    json.dump(data, open(infile, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # 覆蓋率
    total = sum(1 for n in data["npcs"] for fld in n["fields"]
                if fld not in ("keyword_1", "keyword_2"))
    done = sum(1 for n in data["npcs"] for fld, v in n["fields"].items()
               if fld not in ("keyword_1", "keyword_2") and v["zh"])
    print(f"合併 {len(files)} 批,填入 {filled} 個 zh 欄位")
    print(f"翻譯覆蓋(不含 keyword): {done}/{total} = {done*100//max(total,1)}%")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split"); s.add_argument("--in", dest="infile", required=True)
    s.add_argument("--batches", type=int, default=8)
    m = sub.add_parser("merge"); m.add_argument("--in", dest="infile", required=True)
    a = ap.parse_args()
    if a.cmd == "split":
        split(a.infile, a.batches)
    else:
        merge(a.infile)


if __name__ == "__main__":
    main()
