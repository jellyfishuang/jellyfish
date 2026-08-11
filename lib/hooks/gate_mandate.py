#!/usr/bin/env python3
"""gate 共用: 判定 user-away mandate 是否生效 (control-plane §5.6)。
briefs/_active.yaml 的 brief_id + autonomous_mandate 指針 -> briefs/{id}/_mandate.json -> status == "active"。
呼叫契約: 本函式任何情況不得 raise——raise 會冒泡到 gate 的 fail-open 包裝, 連原本的 ask 防線一起跳過。
任何讀取/解析失敗回 False (gate 回退互動語意 ask, 與 fail-open 原則一致)。
GATE_BRIEFS_DIR 環境變數覆寫 briefs 目錄 (測試注入 fixture 用)。"""
import json
import os
import re


def mandate_active():
    try:
        briefs = os.environ.get("GATE_BRIEFS_DIR") or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "briefs")
        with open(os.path.join(briefs, "_active.yaml"), encoding="utf-8-sig") as f:
            active = f.read()
        m_id = re.search(r"^brief_id:[ \t]*(\S+)", active, re.M)
        m_ptr = re.search(r"^autonomous_mandate:[ \t]*(\S+)", active, re.M)
        if not m_id or not m_ptr:
            return False
        brief_id = m_id.group(1).strip("'\"")
        ptr = m_ptr.group(1).strip("'\"")
        with open(os.path.join(briefs, brief_id, ptr), encoding="utf-8-sig") as f:
            mandate = json.load(f)
        return mandate.get("status") == "active"
    except Exception:
        return False
