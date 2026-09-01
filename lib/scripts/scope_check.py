#!/usr/bin/env python3
"""Multi-repo scope 機械閘。repo 前綴由 PREFIX 常數定義, 落地時依專案調整。

Lock registry (multi-lane, 2026-09-01): active brief 的鎖在 .framework/briefs/_active/{brief_id}.yaml
(每 lane 一份, 內含 affected_repos 冗餘欄); legacy 單檔 .framework/briefs/_active.yaml 兼容讀取 (視為一個 lane)。

用法 (在 multi-repo root 跑):
  python .framework/scripts/scope_check.py                        # 單 lane: allowed = 該 lock repos; 多 lane: 僅報現況+歸屬
  python .framework/scripts/scope_check.py --self <brief_id>      # allowed = 本 lane lock 的 repos
  python .framework/scripts/scope_check.py --repos Repo_A,Repo_B  # allowed = 本 sub-brief 的 affected_repos (reviewer/engineer 用)
  python .framework/scripts/scope_check.py --overlap Repo_A       # admission 閘: 新 brief repos vs (各 lane repos ∪ 無主 dirty) 交集
  python .framework/scripts/scope_check.py --overlap Repo_A --self <brief_id>
                                                                  # 排除自己的 lock (brief-approve 收斂重驗 / execute 擴 scope 用)

行為:
  - 掃所有 PREFIX 前綴目錄 (有 .git 者) 的 working tree vs HEAD (engineer 不 commit, 勿用 main...HEAD 基準)
  - dirty 三分類: 屬 allowed → OK(in-scope); 屬某 lane 的 lock → INFO (該 lane 合法工作區, 不違規);
    不屬任何 lock → VIOLATION (無主殘留), exit 2
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


def _brief_repos_from_dir(root, bid):
    """從 brief 目錄解析 affected_repos 聯集 (lock 缺冗餘欄時的 fallback)。
    來源: _tree.yaml + 根 plan.md + 各 sub-brief plan/sub-brief.md
    格式容忍: `affected_repos: [...]` 與 markdown 粗體 `**affected_repos**: [...]`"""
    bdir = os.path.join(root, ".framework", "briefs", bid)
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
    return repos


def active_locks(root):
    """讀 lock registry → {brief_id: set(repos)}。
    lock 內 affected_repos 為主、brief 目錄解析為 fallback; legacy 單檔 _active.yaml 視為一個 lane。"""
    briefs = os.path.join(root, ".framework", "briefs")
    reg = os.path.join(briefs, "_active")
    candidates = []
    if os.path.isdir(reg):
        candidates += [os.path.join(reg, f) for f in sorted(os.listdir(reg))
                       if f.endswith(".yaml") and not f.startswith("_")]
    legacy = os.path.join(briefs, "_active.yaml")
    if os.path.exists(legacy):
        candidates.append(legacy)  # 遷移期兼容; 讀到時上層應提示搬遷至 _active/
    locks = {}
    for p in candidates:
        try:
            with open(p, encoding="utf-8-sig", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        m = re.search(r"^brief_id:\s*(\S+)", text, re.M)
        bid = m.group(1).strip("'\"") if m else os.path.splitext(os.path.basename(p))[0]
        mm = re.search(r"^affected_repos:\s*\[([^\]]*)\]", text, re.M)
        if mm:
            repos = {x.strip().strip("'\"") for x in mm.group(1).split(",") if x.strip()}
        else:
            repos = _brief_repos_from_dir(root, bid)
        locks[bid] = repos
    return locks


def owner_of(repo, locks):
    for bid, repos in locks.items():
        if repo in repos:
            return bid
    return None


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
    ap.add_argument("--overlap", help="admission 模式: 檢查這些 repos 與各 lane / 無主 dirty 的交集")
    ap.add_argument("--self", dest="self_id",
                    help="本 lane 的 brief_id: --overlap 時排除自己的 lock; 單獨用時 allowed = 該 lock repos")
    ap.add_argument("--root", help="multi-repo root (預設由 script 位置推導)")
    args = ap.parse_args()
    root = resolve_root(args.root)

    dirty = scan_dirty(root)
    locks = active_locks(root)
    owned = set().union(*locks.values()) if locks else set()
    unowned_dirty = sorted(set(dirty) - owned)

    if args.overlap is not None:
        proposed = {x.strip() for x in args.overlap.split(",") if x.strip()}
        if not proposed:
            print("usage error: --overlap 為空值; 機械閘拒絕 fail-open", file=sys.stderr)
            sys.exit(1)
        others = {b: r for b, r in locks.items() if b != args.self_id}
        if args.self_id and args.self_id not in locks:
            print(f"[warn] --self {args.self_id} 在 registry 內無 lock (視同無自鎖繼續)")
        busy = set().union(*others.values()) if others else set()
        busy |= set(unowned_dirty)
        conflicts = sorted(proposed & busy)
        print(f"active lanes: {len(locks)}" + (f" (排除自己: {args.self_id})" if args.self_id else ""))
        for bid in sorted(locks):
            print(f"  {bid}: {sorted(locks[bid])}")
        print(f"dirty repos: {sorted(dirty)} (無主: {unowned_dirty})")
        if conflicts:
            attributed = [f"{r} ← {owner_of(r, others) or '無主 dirty'}" for r in conflicts]
            print(f"OVERLAP: {attributed} — 與他 lane 範圍或無主工作樹重疊, 平行 brief 會互蓋")
            sys.exit(2)
        print("OVERLAP: 無")
        sys.exit(0)

    if args.repos is not None:
        allowed = {x.strip() for x in args.repos.split(",") if x.strip()}
        if not allowed:
            print("usage error: --repos 為空值; 機械閘拒絕 fail-open", file=sys.stderr)
            sys.exit(1)
        src = "--repos"
    elif args.self_id:
        if args.self_id not in locks:
            print(f"usage error: --self {args.self_id} 在 registry 內無 lock", file=sys.stderr)
            sys.exit(1)
        allowed = locks[args.self_id]
        src = f"_active/{args.self_id}.yaml"
    elif len(locks) == 1:
        bid, allowed = next(iter(locks.items()))
        src = f"_active/{bid}.yaml 全 sub-brief 聯集"
    elif locks:
        allowed = None
        src = f"多 lane ({len(locks)}) 未指定 --self (僅報現況+歸屬)"
    else:
        allowed = None
        src = "無 (僅報現況)"

    print(f"allowed repos [{src}]: {sorted(allowed) if allowed else 'N/A'}")
    if locks:
        print(f"active lanes: " + ", ".join(f"{b}={sorted(r)}" for b, r in sorted(locks.items())))
    violations = []
    for repo in sorted(dirty):
        owner = owner_of(repo, locks)
        if allowed is not None and repo in allowed:
            tag = "OK(in-scope)"
        elif owner:
            tag = f"INFO(lane:{owner})"  # 他 lane 合法工作區; 若非該 lane 所為, 查其 diff
        elif allowed is not None:
            tag = "VIOLATION"
            violations.append(repo)
        else:
            tag = "dirty"
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

    not_scanned = sorted(
        r for r in (allowed or set())
        if not (r.startswith(PREFIX) and os.path.exists(os.path.join(root, r, ".git")))
    )
    if not_scanned:
        print(f"\n[note] allowed 內未被掃描的項目 (不存在/非 {PREFIX} 前綴/無 .git): {not_scanned}")
    print(f"\nVERDICT: {'VIOLATION ' + str(sorted(violations)) if violations else 'clean scope'}"
          f" (dirty repos: {len(dirty)}, allowed: {len(allowed) if allowed else 0}, lanes: {len(locks)})")
    sys.exit(2 if violations else 0)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
