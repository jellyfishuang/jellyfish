#!/usr/bin/env python3
"""Multi-repo scope 機械閘。repo 前綴由 PREFIX 常數定義, 落地時依專案調整。

用法 (在 multi-repo root 跑):
  python .framework/scripts/scope_check.py                      # allowed = _active.yaml 解析的 affected_repos 聯集
  python .framework/scripts/scope_check.py --repos Repo_A,Repo_B  # allowed = 本 sub-brief 的 affected_repos (reviewer/engineer 用)
  python .framework/scripts/scope_check.py --overlap Repo_A      # batch-lock 用: 新 brief repos vs active allowed ∪ dirty repos 交集

行為:
  - 掃所有 PREFIX 前綴目錄 (有 .git 者) 的 working tree vs HEAD (engineer 不 commit, 勿用 main...HEAD 基準)
  - allowed 之外的 repo 有 dirty → VIOLATION, exit 2
  - go.mod/go.sum 有變動的 repo → 列出 require diff 供對照 plan 是否許可 (偷升依賴檢查)
  - 無 allowed 資訊時只報現況 (exit 0)
內部錯誤 exit 1 (顯式 lint 工具, 不 fail-open)。"""
import argparse
import os
import re
import subprocess
import sys

PREFIX = "SGC_"  # 專案 repo 目錄前綴, fork 落地時調整


def sh(args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


def resolve_root(cli_root):
    if cli_root:
        return os.path.abspath(cli_root)
    # 部署位置 .framework/scripts/scope_check.py → 上兩層是專案 root
    guess = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if os.path.isdir(os.path.join(guess, ".framework")):
        return guess
    return os.getcwd()


def active_allowed(root):
    p = os.path.join(root, ".framework", "briefs", "_active.yaml")
    if not os.path.exists(p):
        return None, None
    with open(p, encoding="utf-8") as f:
        m = re.search(r"^brief_id:\s*(\S+)", f.read(), re.M)
    if not m:
        return None, None
    bid = m.group(1)
    bdir = os.path.join(root, ".framework", "briefs", bid)
    # 來源: _tree.yaml + 根 plan.md + 各 sub-brief plan/sub-brief.md
    # 格式容忍: `affected_repos: [...]` 與 markdown 粗體 `**affected_repos**: [...]`
    sources = [os.path.join(bdir, "_tree.yaml"), os.path.join(bdir, "plan.md")]
    sb = os.path.join(bdir, "sub-briefs")
    if os.path.isdir(sb):
        for sub in os.listdir(sb):
            sources += [os.path.join(sb, sub, "plan.md"), os.path.join(sb, sub, "sub-brief.md")]
    repos = set()
    for src in sources:
        if not os.path.exists(src):
            continue
        with open(src, encoding="utf-8", errors="replace") as f:
            for mm in re.finditer(r"affected_repos\*{0,2}:\s*\[([^\]]*)\]", f.read()):
                repos.update(x.strip().strip("'\"") for x in mm.group(1).split(",") if x.strip())
    return bid, repos


def scan_dirty(root):
    dirty = {}
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not name.startswith(PREFIX) or not os.path.exists(os.path.join(d, ".git")):
            continue
        r = sh(["git", "-C", d, "status", "--porcelain"])
        if r.returncode != 0:
            print(f"[warn] git status 失敗: {name}: {r.stderr.strip()[:120]}")
            continue
        files = [ln for ln in r.stdout.splitlines() if ln.strip()]
        if files:
            dirty[name] = files
    return dirty


def gomod_diff(root, repo):
    r = sh(["git", "-C", os.path.join(root, repo), "diff", "HEAD", "--", "go.mod"])
    return [ln for ln in r.stdout.splitlines()
            if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", help="allowed repos, 逗號分隔 (本 sub-brief 的 affected_repos)")
    ap.add_argument("--overlap", help="batch-lock 模式: 檢查這些 repos 與 active brief/dirty 的交集")
    ap.add_argument("--root", help="multi-repo root (預設由 script 位置推導)")
    args = ap.parse_args()
    root = resolve_root(args.root)

    dirty = scan_dirty(root)
    bid, brief_repos = active_allowed(root)

    if args.overlap is not None:
        proposed = {x.strip() for x in args.overlap.split(",") if x.strip()}
        if not proposed:
            print("usage error: --overlap 為空值; 機械閘拒絕 fail-open", file=sys.stderr)
            sys.exit(1)
        busy = (brief_repos or set()) | set(dirty)
        conflicts = sorted(proposed & busy)
        print(f"active brief: {bid or '無'}; its repos: {sorted(brief_repos) if brief_repos else '[]'}")
        print(f"dirty repos: {sorted(dirty)}")
        if conflicts:
            print(f"OVERLAP: {conflicts} — 與 active brief 或未收工作樹重疊, 平行 brief 會互蓋")
            sys.exit(2)
        print("OVERLAP: 無")
        sys.exit(0)

    if args.repos is not None:
        allowed = {x.strip() for x in args.repos.split(",") if x.strip()}
        if not allowed:
            print("usage error: --repos 為空值; 機械閘拒絕 fail-open", file=sys.stderr)
            sys.exit(1)
        src = "--repos"
    elif brief_repos:
        allowed = brief_repos
        src = f"_active.yaml ({bid}) 全 sub-brief 聯集"
    else:
        allowed = None
        src = "無 (僅報現況)"

    print(f"allowed repos [{src}]: {sorted(allowed) if allowed else 'N/A'}")
    for repo in sorted(dirty):
        tag = "OK(in-scope)" if (allowed and repo in allowed) else ("VIOLATION" if allowed else "dirty")
        files = dirty[repo]
        print(f"\n[{tag}] {repo} — {len(files)} 檔:")
        for ln in files[:20]:
            print(f"  {ln}")
        if len(files) > 20:
            print(f"  ... 共 {len(files)} 檔")
        if any(re.search(r"go\.(mod|sum)$", ln) for ln in files):
            req = gomod_diff(root, repo)
            if req:
                print("  go.mod 變動 (對照 plan 是否許可):")
                for ln in req[:15]:
                    print(f"    {ln}")
            else:
                print("  go.sum 變動 (go.mod require 無變動)")

    violations = sorted(r for r in dirty if allowed and r not in allowed)
    not_scanned = sorted(
        r for r in (allowed or set())
        if not (r.startswith(PREFIX) and os.path.exists(os.path.join(root, r, ".git")))
    )
    if not_scanned:
        print(f"\n[note] allowed 內未被掃描的項目 (不存在/非 {PREFIX} 前綴/無 .git): {not_scanned}")
    print(f"\nVERDICT: {'VIOLATION ' + str(violations) if violations else 'clean scope'}"
          f" (dirty repos: {len(dirty)}, allowed: {len(allowed) if allowed else 0})")
    sys.exit(2 if violations else 0)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
