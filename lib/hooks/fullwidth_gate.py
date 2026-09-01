#!/usr/bin/env python3
"""PostToolUse gate (matcher: Write|Edit|MultiEdit)
.go 檔註解禁全形標點。剝除 string/rune literal 後殘留的全形標點必在註解內,
故無需解析註解結構。剝除時保留換行數使行號準確。

掃描範圍 (2026-08-07 收斂): 只檢「本次工具呼叫實際寫入的行」, 不檢全檔。
  Edit / MultiEdit -> 以 new_string 在檔內的位置反查行號
  Write            -> 整檔 (該工具語意即為整檔本次產出)
  new_string 全數找不到 (stale) -> fail-open + WARN
動機: 舊版掃全檔, 使檔內既有全形標點卡住任何後續編輯 —— 純刪除的 patch 也會被擋,
而回頭正規化既有註解違反 feedback_no_retroactive_comment_normalization 且會製造
brief 的 diff scope 清單外 hunk。

已知 false-negative: backtick 剝除是全檔任意兩點配對, 落在其間的違規會漏檢 (詳 README)。
內部錯誤一律 fail-open (exit 0) 並記 gate.log。"""
import datetime
import json
import os
import re
import sys

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate.log")
BAD = r"[，。、（）：；「」！？]"  # ，。、（）：；「」！？


def _log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} [fullwidth_gate] {msg}\n")
    except Exception:
        pass


def _blank_keep_newlines(m):
    return '"' + "\n" * m.group(0).count("\n") + '"'


def _written_lines(tool, ti, raw):
    """本次呼叫實際寫入的行號集合。None = 整檔 (Write / 未知 tool, 保守全掃)。
    回傳空 set = new_string 全數找不到, 呼叫端據此 fail-open。"""
    if tool not in ("Edit", "MultiEdit"):
        return None
    news = []
    if tool == "Edit":
        s = ti.get("new_string")
        if s:
            news.append(s)
    else:
        for e in ti.get("edits") or []:
            s = (e or {}).get("new_string")
            if s:
                news.append(s)
    if not news:
        return None  # 取不到 new_string, 退回全掃 (保守)
    lines = set()
    for s in news:
        start = 0
        while True:
            i = raw.find(s, start)
            if i < 0:
                break
            first = raw.count("\n", 0, i) + 1
            lines.update(range(first, first + s.count("\n") + 1))
            start = i + 1
    return lines


def main():
    data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    ti = data.get("tool_input") or {}
    p = (ti.get("file_path") or "").replace("\\", "/")
    if not p.lower().endswith(".go") or "/vendor/" in p.lower():
        return
    if not os.path.isabs(p):
        p = os.path.join(data.get("cwd") or "", p)
    if not os.path.exists(p):
        return
    with open(p, encoding="utf-8-sig", errors="replace") as f:
        raw = f.read()

    targets = _written_lines(data.get("tool_name") or "", ti, raw)
    if targets is not None and not targets:
        _log(f"WARN new_string 未在檔內找到 (stale?), fail-open: {p}")
        return

    src = re.sub(r"`[^`]*`", _blank_keep_newlines, raw)
    src = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', src)
    # rune literal 用精確單字元文法, 避免 don't...don't 假配對吞掉其間內容
    src = re.sub(r"'(?:\\(?:[abfnrtv\\'\"0]|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|[0-7]{3})|[^'\\\n])'", "''", src)

    bad = [f"{p}:{i}" for i, line in enumerate(src.splitlines(), 1)
           if re.search(BAD, line) and (targets is None or i in targets)]
    if bad:
        _log(f"deny {len(bad)} hits in {p} (scope={'file' if targets is None else 'written-lines'})")
        tail = "" if len(bad) <= 10 else f"\n... 共 {len(bad)} 處"
        print("註解含全形標點 (規範: 繁中註解用半形標點), 修正下列位置後再繼續:\n"
              + "\n".join(bad[:10]) + tail
              + "\n(只檢本次寫入的行; 檔內既有全形標點屬存量, 不必回頭修)", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        _log(f"unexpected error: {e}")
    sys.exit(0)
