#!/usr/bin/env python3
"""gate 共用: 判定 user-away mandate 是否生效 (control-plane §5.6)。

Multi-lane (2026-09-01): 鎖在 briefs/_active/{brief_id}.yaml (registry, 每 lane 一份);
legacy 單檔 briefs/_active.yaml 兼容讀取。每份 lock 的 autonomous_mandate 指針 ->
briefs/{id}/_mandate.json -> status == "active"。

**任一** lane 有 active mandate 即回報 (聯集語意, 保守 over-deny——gate 守的是永不可
預授權動作, 絕不 under-deny)。多 lane 並行時本 session 可設 FRAMEWORK_BRIEF_ID 環境變數
精確歸屬: 設定後只看該 lane 的 lock, 他 lane 的 mandate 不再誤傷本 session 的 ask 語意。

呼叫契約: mandate_active() 任何情況不得 raise——raise 會冒泡到 gate 的 fail-open 包裝,
連原本的 ask 防線一起跳過。任何讀取/解析失敗回 falsy (gate 回退互動語意 ask)。
回傳值: 生效中的 brief_id 字串 (truthy) / "" (falsy)——truthiness 與舊布林契約相容,
呼叫端 deny 訊息可點名肇事 lane。
GATE_BRIEFS_DIR 環境變數覆寫 briefs 目錄 (測試注入 fixture 用)。"""
import json
import os
import re


def _lock_mandate(briefs, text):
    """單份 lock 內容 → 有 active mandate 時回 brief_id, 否則 ""。可 raise, 由呼叫端兜。"""
    m_id = re.search(r"^brief_id:[ \t]*(\S+)", text, re.M)
    m_ptr = re.search(r"^autonomous_mandate:[ \t]*(\S+)", text, re.M)
    if not m_id or not m_ptr:
        return ""
    brief_id = m_id.group(1).strip("'\"")
    ptr = m_ptr.group(1).strip("'\"")
    with open(os.path.join(briefs, brief_id, ptr), encoding="utf-8-sig") as f:
        mandate = json.load(f)
    return brief_id if mandate.get("status") == "active" else ""


def mandate_active():
    try:
        briefs = os.environ.get("GATE_BRIEFS_DIR") or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "briefs")
        only = (os.environ.get("FRAMEWORK_BRIEF_ID") or "").strip()
        reg = os.path.join(briefs, "_active")
        paths = []
        if os.path.isdir(reg):
            paths += [os.path.join(reg, f) for f in sorted(os.listdir(reg))
                      if f.endswith(".yaml") and not f.startswith("_")]
        legacy = os.path.join(briefs, "_active.yaml")
        if os.path.exists(legacy):
            paths.append(legacy)  # 遷移期兼容
        for p in paths:
            try:
                with open(p, encoding="utf-8-sig") as f:
                    text = f.read()
                bid = _lock_mandate(briefs, text)
            except Exception:
                continue  # 單份 lock 壞檔不拖垮其他 lane 的判定
            if not bid:
                continue
            if only and bid != only:
                continue  # 本 session 已精確歸屬, 他 lane 的 mandate 不干涉
            return bid
        return ""
    except Exception:
        return ""
