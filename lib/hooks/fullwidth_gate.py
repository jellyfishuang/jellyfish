#!/usr/bin/env python3
"""PostToolUse gate (matcher: Write|Edit|MultiEdit)
.go 檔註解禁全形標點。剝除 string/rune literal 後殘留的全形標點必在註解內,
故無需解析註解結構。剝除時保留換行數使行號準確。
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
        src = f.read()
    src = re.sub(r"`[^`]*`", _blank_keep_newlines, src)
    src = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', src)
    # rune literal 用精確單字元文法, 避免 don't...don't 假配對吞掉其間內容
    src = re.sub(r"'(?:\\(?:[abfnrtv\\'\"0]|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|[0-7]{3})|[^'\\\n])'", "''", src)
    bad = [f"{p}:{i}" for i, line in enumerate(src.splitlines(), 1) if re.search(BAD, line)]
    if bad:
        _log(f"deny {len(bad)} hits in {p}")
        tail = "" if len(bad) <= 10 else f"\n... 共 {len(bad)} 處"
        print("註解含全形標點 (規範: 繁中註解用半形標點), 修正下列位置後再繼續:\n"
              + "\n".join(bad[:10]) + tail, file=sys.stderr)
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
