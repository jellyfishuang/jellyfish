#!/usr/bin/env python3
"""PreToolUse gate (matcher: Write|Edit|MultiEdit)
守護路徑 (.framework/memory, .framework/codex, .claude/skills) 的寫入一律 ask:
mid-execution 偷寫會被使用者看見並擋下; learning loop 合法寫入時, 權限提示本身即為批准點。
例外: .framework/memory/sessions/ (brief 結束清單規定強制寫、無批准門檻)。
內部錯誤一律 fail-open (exit 0) 並記 gate.log。"""
import datetime
import json
import os
import sys

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate.log")
GUARDED = (".framework/memory/", ".framework/codex/", ".claude/skills/")
ALLOWED = (".framework/memory/sessions/",)


def _log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} [path_gate] {msg}\n")
    except Exception:
        pass


def main():
    data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    ti = data.get("tool_input") or {}
    raw = ti.get("file_path") or ""
    if not raw:
        return
    if not os.path.isabs(raw):
        raw = os.path.join(data.get("cwd") or "", raw)
    # normpath 解掉 .. 與重複斜線, 防路徑寫法繞過守護比對
    p = os.path.normpath(raw).replace("\\", "/").lower()
    if any(a in p for a in ALLOWED):
        return
    if any(g in p for g in GUARDED):
        _log(f"ask guarded-write: {p}")
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason":
                "寫入受守護路徑 (memory/codex/skills): mid-execution 禁寫; "
                "learning loop 經批准的寫入請放行 (此提示即批准點)",
        }}, ensure_ascii=False))
        sys.exit(0)


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
