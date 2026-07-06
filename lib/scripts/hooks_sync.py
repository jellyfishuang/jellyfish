#!/usr/bin/env python3
"""Framework hooks 部署與 settings.json 同步 (確定性機械流程, 不靠 LLM 手動合併 JSON)。

用法 (用 Python 3 執行; Windows 勿用可能是 2.x 的 `python`):
  python3 .framework/lib/scripts/hooks_sync.py [--root <dir>] [--python <exe>] [--dry-run] [--skip-tests]

行為:
  1. lib/hooks/*.py -> .framework/hooks/ ; lib/scripts/*.py -> .framework/scripts/ (byte 相同不重寫)
  2. 渲染 lib/hooks/hooks-config.template.json ({PYTHON} = 實體直譯器, {PROJECT_ROOT} = 專案根)
  3. 合併進 .claude/settings.json:
     - hooks 內 command 含 ".framework/hooks/" 的條目視為 framework-managed, 整組替換 (使用者改過 timeout 也會被重置)
     - 其他條目 (使用者自加 hook) 原樣保留
     - `_framework_managed_hooks` 鏡像更新為本次渲染結果 (供漂移比對)
  4. 跑 .framework/hooks/run_tests.py 回歸 (--skip-tests 跳過)
exit: 0 成功 (含已同步無變更), 1 失敗。"""
import argparse
import json
import os
import shutil
import subprocess
import sys

MANAGED_MARK = ".framework/hooks/"


def resolve_root(cli):
    if cli:
        return os.path.abspath(cli)
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        parent = os.path.dirname(d)
        if os.path.isdir(os.path.join(d, ".framework")) and os.path.basename(d) != ".framework":
            return d
        if parent == d:
            break
        d = parent
    return os.getcwd()


def real_python(cli):
    if cli:
        return os.path.abspath(cli).replace("\\", "/")
    if os.name == "nt":
        cand = os.path.join(sys.base_exec_prefix, "python.exe")  # 避開 WindowsApps shim
        if os.path.exists(cand):
            return os.path.abspath(cand).replace("\\", "/")
    return os.path.abspath(sys.executable).replace("\\", "/")


def sync_dir(src, dst, dry):
    changed = []
    if not os.path.isdir(src):
        return changed
    os.makedirs(dst, exist_ok=True)
    for f in sorted(os.listdir(src)):
        if not f.endswith(".py"):
            continue
        s, d = os.path.join(src, f), os.path.join(dst, f)
        if os.path.exists(d):
            with open(s, "rb") as a, open(d, "rb") as b:
                if a.read() == b.read():
                    continue
        if not dry:
            shutil.copy(s, d)
        changed.append(f)
    return changed


def is_managed(entry):
    return any(MANAGED_MARK in (h.get("command") or "") for h in entry.get("hooks", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--python", dest="py")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()
    root = resolve_root(args.root)
    fw = os.path.join(root, ".framework")
    tpl_path = os.path.join(fw, "lib", "hooks", "hooks-config.template.json")
    if not os.path.exists(tpl_path):
        print(f"error: 找不到 {tpl_path} (lib/hooks 未就位)", file=sys.stderr)
        sys.exit(1)
    py = real_python(args.py)
    root_fs = root.replace("\\", "/")
    print(f"root: {root_fs}\npython: {py}\ndry-run: {args.dry_run}")

    # 1. 部署 scripts
    c1 = sync_dir(os.path.join(fw, "lib", "hooks"), os.path.join(fw, "hooks"), args.dry_run)
    c2 = sync_dir(os.path.join(fw, "lib", "scripts"), os.path.join(fw, "scripts"), args.dry_run)
    print(f"deploy hooks/: {c1 or '無變更'}\ndeploy scripts/: {c2 or '無變更'}")

    # 2. 渲染 template
    with open(tpl_path, encoding="utf-8") as f:
        tpl = json.load(f)
    txt = json.dumps(tpl["hooks"])
    rendered = json.loads(txt.replace("{PYTHON}", py).replace("{PROJECT_ROOT}", root_fs))

    # 3. 合併 settings.json
    sp = os.path.join(root, ".claude", "settings.json")
    settings = {}
    if os.path.exists(sp):
        try:
            with open(sp, encoding="utf-8") as f:
                settings = json.load(f)
        except ValueError as e:
            print(f"error: {sp} 非合法 JSON ({e}); 不覆寫, 請先手動修復", file=sys.stderr)
            sys.exit(1)
    old_hooks = settings.get("hooks") or {}
    new_hooks = {}
    for ev in sorted(set(old_hooks) | set(rendered)):
        kept = [e for e in old_hooks.get(ev, []) if not is_managed(e)]
        merged = kept + rendered.get(ev, [])
        if merged:
            new_hooks[ev] = merged
    changed = old_hooks != new_hooks or settings.get("_framework_managed_hooks") != rendered
    user_kept = sum(len([e for e in v if not is_managed(e)]) for v in old_hooks.values())
    if changed:
        settings["hooks"] = new_hooks
        settings["_framework_managed_hooks"] = rendered
        if not args.dry_run:
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            with open(sp, "w", encoding="utf-8", newline="\n") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                f.write("\n")
        print(f"settings.json: {'(dry-run) 將更新' if args.dry_run else '已更新'}"
              f" (framework-managed 條目已替換; 保留使用者自加 hook {user_kept} 條)")
    else:
        print("settings.json: 已同步, 無變更")

    # 4. 回歸測試
    if args.skip_tests or args.dry_run:
        print("tests: skipped")
    else:
        rt = os.path.join(fw, "hooks", "run_tests.py")
        r = subprocess.run([py, rt], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        tail = (r.stdout or "").strip().splitlines()[-1:] or ["(no output)"]
        print(f"tests: {tail[0]}")
        if r.returncode != 0 or "FAILURES: 0" not in (r.stdout or ""):
            print("error: gate 回歸未通過, 檢視上方輸出", file=sys.stderr)
            sys.exit(1)
    print("SYNC OK" if not args.dry_run else "DRY-RUN OK")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
