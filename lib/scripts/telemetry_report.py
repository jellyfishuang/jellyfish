#!/usr/bin/env python3
"""Gate 遙測報表: 讀 gate_runs.jsonl 出 per-gate 有效性統計 (markdown 到 stdout)。

用法 (Python 3):
  python3 telemetry_report.py [--jsonl <path>] [--md <out_path>]

--jsonl 預設: 由本檔位置向上找 .framework → memory/telemetry/gate_runs.jsonl
統計軸: 每 gate 的 runs / 覆蓋 brief 數 / fail 率 / findings 總數與 per-run 密度
        / severity 分佈 / disposition 分佈 (user_code_review) / zero-finding 率 / live vs retro。
判讀提示: findings 密度低 + zero-finding 率高 + severity 輕 → 候選改條件式閘;
          user_code_review 攔到而機器閘沒攔到的類型 → 機器閘的盲區清單。"""
import argparse
import json
import os
import sys
from collections import defaultdict


def default_jsonl():
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        cand = os.path.join(d, ".framework", "memory", "telemetry", "gate_runs.jsonl")
        if os.path.isfile(cand):
            return cand
        if os.path.basename(d) == ".framework":
            return os.path.join(d, "memory", "telemetry", "gate_runs.jsonl")
        parent = os.path.dirname(d)
        if parent == d:
            return cand
        d = parent


def load(path):
    rows = []
    for i, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            print(f"WARN 略過壞列 {path}:{i}", file=sys.stderr)
    return rows


def pct(n, d):
    return f"{100.0 * n / d:.0f}%" if d else "-"


def build(rows):
    gates = defaultdict(lambda: {"runs": 0, "briefs": set(), "fails": 0, "findings": 0,
                                 "zero": 0, "sev": defaultdict(int), "disp": defaultdict(int),
                                 "src": defaultdict(int)})
    for r in rows:
        g = gates[r.get("gate") or "?"]
        g["runs"] += 1
        g["briefs"].add(r.get("brief_id"))
        g["src"][r.get("source") or "?"] += 1
        if r.get("verdict") in ("fail", "partial"):
            g["fails"] += 1
        n = r.get("findings_count")
        if n is None:
            n = len(r.get("findings") or [])
        g["findings"] += n
        if n == 0:
            g["zero"] += 1
        for f in r.get("findings") or []:
            g["sev"][(f.get("severity") or "未標")] += 1
            if f.get("disposition"):
                g["disp"][f["disposition"]] += 1

    lines = ["# Gate 遙測報表", "",
             f"資料列: {len(rows)}  brief 數: {len({r.get('brief_id') for r in rows})}", "",
             "| gate | runs | briefs | fail率 | findings | 密度/run | zero率 | severity | disposition | 來源 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    order = sorted(gates.items(), key=lambda kv: -kv[1]["findings"])
    for name, g in order:
        sev = " ".join(f"{k}:{v}" for k, v in sorted(g["sev"].items(), key=lambda kv: -kv[1])) or "-"
        disp = " ".join(f"{k}:{v}" for k, v in sorted(g["disp"].items(), key=lambda kv: -kv[1])) or "-"
        src = " ".join(f"{k}:{v}" for k, v in sorted(g["src"].items())) or "-"
        dens = f"{g['findings'] / g['runs']:.1f}" if g["runs"] else "-"
        lines.append(f"| {name} | {g['runs']} | {len(g['briefs'])} | {pct(g['fails'], g['runs'])} "
                     f"| {g['findings']} | {dens} | {pct(g['zero'], g['runs'])} | {sev} | {disp} | {src} |")
    lines += ["",
              "判讀: 密度低 + zero 率高 + severity 輕 → 候選改條件式閘; ",
              "user_code_review 有 findings 的 brief, 對照同 brief 機器閘 rows = 機器閘盲區線索。"]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl")
    ap.add_argument("--md")
    a = ap.parse_args()
    path = a.jsonl or default_jsonl()
    if not os.path.isfile(path):
        print(f"找不到 gate_runs.jsonl: {path}", file=sys.stderr)
        return 1
    report = build(load(path))
    print(report)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\n已寫: {a.md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
