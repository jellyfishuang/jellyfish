#!/usr/bin/env python3
"""sessions/{brief_id}.md 格式機械 lint (learning-loop.md §4 Step 1 模板)。格式漂移的機械化解 (2026-07-07)。

用法 (Python 3):
  python3 session_check.py <brief_dir | sessions/*.md>

檢查:
  檔案存在: .framework/memory/sessions/{brief_id}.md (brief_dir 模式由目錄名推 brief_id)
  YAML frontmatter: 首行 `---` + 收尾 `---`
  必填鍵: id / created_at / brief_started_at / brief_completed_at / duration / recipe / roster / state / sub_briefs / archived_to / draft_cycles / fork_count
  draft_cycles / fork_count 值限 null 或非負整數 (draft+redline 遙測, learning-loop.md §4; 逐題模式填 null; 2026-07-06 前歷史檔不回溯)
  id 必等於 brief_id (檔名 stem)
  state ∈ {done, failed, cancelled}
  必要 section (state=cancelled 免): ## 摘要 / ## 關鍵時間軸 / ## 產出
exit: 0 過 / 1 檔案或用法錯 / 2 違規 (列明細)。"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REQUIRED_KEYS = ("id", "created_at", "brief_started_at", "brief_completed_at",
                 "duration", "recipe", "roster", "state", "sub_briefs", "archived_to",
                 "draft_cycles", "fork_count")
NULL_OR_INT_KEYS = ("draft_cycles", "fork_count")  # draft+redline 遙測; 漏記=樣本作廢, 故鍵必在
STATES = {"done", "failed", "cancelled"}
REQUIRED_SECTIONS = ("## 摘要", "## 關鍵時間軸", "## 產出")


def resolve(target):
    """回 (sessions_md_path, expected_brief_id)。"""
    target = os.path.abspath(target)
    if os.path.isdir(target):
        brief_id = os.path.basename(target.rstrip("\\/"))
        # brief_dir = <root>/.framework/briefs[/_archive/YYYY-MM]/{id} → sessions 同 .framework 下
        d = target
        while d and os.path.basename(d) != ".framework":
            parent = os.path.dirname(d)
            if parent == d:
                return None, brief_id
            d = parent
        return os.path.join(d, "memory", "sessions", brief_id + ".md"), brief_id
    return target, os.path.splitext(os.path.basename(target))[0]


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    path, brief_id = resolve(sys.argv[1])
    if not path or not os.path.isfile(path):
        print(f"sessions 檔不存在: {path or '(無法定位 .framework 根)'} (brief_id={brief_id})", file=sys.stderr)
        return 2  # 缺 sessions 檔屬收尾違規 (learning-loop §11.1 永遠寫), 非內部錯

    lines = open(path, encoding="utf-8").read().splitlines()
    errs = []

    if not lines or lines[0].strip() != "---":
        errs.append("首行非 '---'——缺 YAML frontmatter (learning-loop.md §4 模板)")
        fm, body_start = {}, 0
    else:
        fm, body_start = {}, None
        for i, raw in enumerate(lines[1:], 2):
            if raw.strip() == "---":
                body_start = i
                break
            m = re.match(r"^([\w\-]+):\s*(.*)$", raw)
            if m:
                fm[m.group(1)] = m.group(2).split("#", 1)[0].strip()
        if body_start is None:
            errs.append("frontmatter 未以 '---' 收尾")
            body_start = len(lines)

    for k in REQUIRED_KEYS:
        if k not in fm:
            errs.append(f"frontmatter 缺必填鍵: {k}")

    for k in NULL_OR_INT_KEYS:
        v = fm.get(k)
        if v is not None and v != "null" and not v.isdigit():
            errs.append(f"{k} 值非法 '{v}' (允許 null 或非負整數)")

    state = fm.get("state", "")
    if state and state not in STATES:
        errs.append(f"state 非法 '{state}' (允許 {sorted(STATES)})")
    fid = fm.get("id", "")
    if fid and fid != brief_id:
        errs.append(f"frontmatter id '{fid}' 與檔名 brief_id '{brief_id}' 不符")

    if state != "cancelled":
        body = "\n".join(lines[body_start:])
        for sec in REQUIRED_SECTIONS:
            if not re.search(rf"^{re.escape(sec)}\s*$", body, re.M):
                errs.append(f"缺必要 section: {sec}")

    if errs:
        print(f"sessions 格式違規 ({os.path.basename(path)}):", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 2
    print(f"SESSION OK  {brief_id} state={state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
