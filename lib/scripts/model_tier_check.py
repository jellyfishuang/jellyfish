# -*- coding: utf-8 -*-
"""model_tier_check.py — 驗證 subagent 實際跑的模型符合 model tier 配置（八點 #8，v0.13.0）

原理：Claude Code 把每個 subagent 的 transcript 落在
  ~/.claude/projects/<project-slug>/<session-id>/subagents/agent-*.jsonl
（<project-slug> = 專案絕對路徑非英數字元全換 '-'，例 D:\\CodeSpace\\SGC → D--CodeSpace-SGC）。
assistant 條目帶 message.model。role 權威來源 = agent-*.meta.json 的 agentType
（harness 落盤，不依賴 spawn prompt 措辭），fallback 抓 spawn prompt 開頭「你是 {role}」。

期望值讀 .claude/agents/{role}.md frontmatter `model:` 欄（v0.13.0 起唯一生效來源），
別名 haiku/sonnet/opus/fable → 模型 ID 前綴比對（避免 dated suffix 差異）。
無 model: 欄的 role 繼承 main session 模型、無固定期望，不驗（僅列出）。

用法（在專案根執行）：
  python .framework/scripts/model_tier_check.py            # 近 48h 的 session
  python .framework/scripts/model_tier_check.py --hours 168
  python .framework/scripts/model_tier_check.py --session <session-id>
  python .framework/scripts/model_tier_check.py --all

exit 0 = 全符合；exit 2 = 有 mismatch（或掃描範圍內無任何 framework role spawn，避免假綠）。
已知坑：agent 定義在 session 啟動時載入快取——改 model: 欄後須以新 session spawn 才反映。
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ALIAS_PREFIX = {
    "haiku": "claude-haiku",
    "sonnet": "claude-sonnet",
    "opus": "claude-opus",
    "fable": "claude-fable",
}

ROLE_RE = re.compile(r"你是\s*([a-z][a-z-]+)")


def transcript_dir(project_root):
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(Path(project_root).resolve()))
    return Path.home() / ".claude" / "projects" / slug


def load_expected(agents_dir):
    """role → 模型 ID 前綴。來源 = .claude/agents/{role}.md frontmatter model: 欄。"""
    expected = {}
    for p in glob.glob(os.path.join(agents_dir, "*.md")):
        fm = {}
        with open(p, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        if not lines or lines[0].strip() != "---":
            continue
        for raw in lines[1:]:
            if raw.strip() == "---":
                break
            m = re.match(r"^([\w\-]+):\s*(.*)$", raw)
            if m:
                fm[m.group(1)] = m.group(2).split("#", 1)[0].strip()
        model = fm.get("model")
        if not model:
            continue
        role = fm.get("name") or os.path.splitext(os.path.basename(p))[0]
        prefix = ALIAS_PREFIX.get(model) or (model if model.startswith("claude-") else None)
        if prefix:
            expected[role] = prefix
    return expected


def role_from_meta(path):
    """權威 role 來源: agent-*.meta.json 的 agentType (harness 落盤, 不依賴 spawn prompt 措辭)。"""
    meta_path = path[: -len(".jsonl")] + ".meta.json"
    try:
        with open(meta_path, encoding="utf-8") as fh:
            return (json.load(fh).get("agentType") or "").strip() or None
    except (OSError, ValueError):
        return None


def first_user_text(path):
    for line in open(path, encoding="utf-8"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "user":
            continue
        content = (d.get("message") or {}).get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    return block["text"]
    return ""


def first_model(path):
    for line in open(path, encoding="utf-8"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "assistant":
            return (d.get("message") or {}).get("model")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", help="只掃指定 session id")
    ap.add_argument("--hours", type=float, default=48, help="掃 mtime 在 N 小時內的 subagent transcript（預設 48）")
    ap.add_argument("--all", action="store_true", help="掃全部歷史")
    ap.add_argument("--project", default=".", help="專案根（預設 cwd；用於推 transcript dir 與 .claude/agents）")
    args = ap.parse_args()

    expected = load_expected(os.path.join(args.project, ".claude", "agents"))
    if not expected:
        print("`.claude/agents/*.md` 沒有任何 role 設 frontmatter model: 欄——無期望可驗。")
        sys.exit(2)

    tdir = transcript_dir(args.project)
    if args.session:
        pattern = str(tdir / args.session / "subagents" / "agent-*.jsonl")
    else:
        pattern = str(tdir / "*" / "subagents" / "agent-*.jsonl")
    files = glob.glob(pattern)
    if not args.all and not args.session:
        import time
        cutoff = time.time() - args.hours * 3600
        files = [f for f in files if os.path.getmtime(f) >= cutoff]

    per_role = {}   # role -> Counter(model)
    unmapped = Counter()
    for f in files:
        model = first_model(f)
        if model is None:
            continue
        role = role_from_meta(f)
        if role is None:
            role_match = ROLE_RE.search(first_user_text(f)[:300])
            role = role_match.group(1) if role_match else None
        if role in expected:
            per_role.setdefault(role, Counter())[model] += 1
        else:
            unmapped[model] += 1

    if not per_role:
        print(f"掃描範圍內（{len(files)} 檔）沒有任何 framework role 的 subagent transcript——無法驗證。")
        print("先跑一個 brief（或至少 spawn 一個 role subagent）再驗。")
        sys.exit(2)

    mismatch = 0
    print(f"{'role':<24}{'期望前綴':<16}實際 model（次數）")
    for role in expected:
        if role not in per_role:
            continue
        for model, n in sorted(per_role[role].items()):
            ok = model.startswith(expected[role])
            flag = "" if ok else "  <-- MISMATCH"
            if not ok:
                mismatch += n
            print(f"{role:<24}{expected[role]:<16}{model} ({n}){flag}")
    if unmapped:
        print(f"\n無 model: 欄 / 非 framework role（不驗，僅列）：{dict(unmapped)}")

    if mismatch:
        print(f"\nFAIL：{mismatch} 個 subagent 跑錯模型。檢查 .claude/agents/*.md 的 model: 欄是否存在且值正確（改欄後需新 session 生效）。")
        sys.exit(2)
    print("\nPASS：所有 framework role subagent 模型符合 tier 配置。")


if __name__ == "__main__":
    main()
