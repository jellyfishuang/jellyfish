"""hooks_sync.py 生命週期測試 (fake root): fresh create / idempotent / user hook 保留 / 壞 JSON 拒寫 / dry-run。

用法: 以 Python 3 執行本檔 (路徑由檔案位置自推)。改 hooks_sync.py 後必跑, 期望 TOTAL FAILURES: 0。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
SYNC = os.path.join(HERE, "hooks_sync.py")


def find_lib():
    """雙位置可跑 (2026-07-09): 從 lib/scripts 跑 → dirname(HERE)=lib; 從部署 .framework/scripts
    跑 → dirname(HERE)=.framework, 退而找同層 lib/。以 hooks-config.template.json 存在為判準。"""
    for cand in (os.path.dirname(HERE), os.path.join(os.path.dirname(HERE), "lib")):
        if os.path.isfile(os.path.join(cand, "hooks", "hooks-config.template.json")):
            return cand
    sys.exit(f"找不到 lib/hooks/hooks-config.template.json (自 {HERE} 推導)")


SRC = find_lib()

fake = tempfile.mkdtemp(prefix="hooks_sync_fake_")
os.makedirs(f"{fake}/.framework/lib/hooks")
os.makedirs(f"{fake}/.framework/lib/scripts")
for f in os.listdir(f"{SRC}/hooks"):
    shutil.copy(f"{SRC}/hooks/{f}", f"{fake}/.framework/lib/hooks/{f}")
shutil.copy(f"{SRC}/scripts/scope_check.py", f"{fake}/.framework/lib/scripts/scope_check.py")

fails = 0


def run(*extra):
    return subprocess.run([PY, SYNC, "--root", fake, "--skip-tests", *extra],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def check(name, cond, detail=""):
    global fails
    print(("OK  " if cond else "FAIL") + f" {name} {detail if not cond else ''}")
    fails += 0 if cond else 1


# T1: fresh create
r = run()
sp = f"{fake}/.claude/settings.json"
check("T1 fresh exit 0", r.returncode == 0, r.stderr[:200])
s = json.load(open(sp, encoding="utf-8"))
check("T1 hooks 3 events", set(s["hooks"]) == {"PreToolUse", "PostToolUse"} and len(s["hooks"]["PreToolUse"]) == 2)
check("T1 mirror equal", s["hooks"] == s["_framework_managed_hooks"])
check("T1 placeholders rendered", "{PYTHON}" not in json.dumps(s) and "{PROJECT_ROOT}" not in json.dumps(s))
check("T1 deployed", os.path.exists(f"{fake}/.framework/hooks/bash_gate.py")
      and os.path.exists(f"{fake}/.framework/scripts/scope_check.py"))

# T2: idempotent
r2 = run()
check("T2 idempotent", r2.returncode == 0 and "無變更" in r2.stdout and "已同步" in r2.stdout, r2.stdout[-200:])

# T3: user hook 保留 + managed 替換 (user 亂改 managed timeout 也會被重置)
s = json.load(open(sp, encoding="utf-8"))
s["hooks"]["PreToolUse"].append({"matcher": "WebFetch", "hooks": [{"type": "command", "command": "python /my/own_hook.py"}]})
s["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"] = 99  # 使用者亂改 managed
s["permissions"] = {"allow": ["Bash(ls:*)"]}  # 其他 key 保留驗證
json.dump(s, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
r3 = run()
s3 = json.load(open(sp, encoding="utf-8"))
pre = s3["hooks"]["PreToolUse"]
check("T3 exit 0 + updated", r3.returncode == 0 and "已更新" in r3.stdout)
check("T3 user hook 保留", any("own_hook.py" in h["command"] for e in pre for h in e["hooks"]))
check("T3 managed timeout 重置", all(h.get("timeout") != 99 for e in pre for h in e["hooks"]))
check("T3 其他 key 保留", s3.get("permissions") == {"allow": ["Bash(ls:*)"]})
check("T3 條目數正確 (2 managed + 1 user)", len(pre) == 3)

# T4: 再跑 idempotent (帶 user hook)
r4 = run()
check("T4 idempotent with user hook", r4.returncode == 0 and "已同步, 無變更" in r4.stdout, r4.stdout[-200:])

# T5: 壞 JSON 拒寫
open(sp, "w", encoding="utf-8").write("{broken json")
r5 = run()
check("T5 壞 JSON exit 1", r5.returncode == 1 and "非合法 JSON" in r5.stderr)
check("T5 未覆寫", open(sp, encoding="utf-8").read() == "{broken json")

# T6: dry-run 不寫
os.remove(sp)
r6 = run("--dry-run")
check("T6 dry-run exit 0 不建檔", r6.returncode == 0 and not os.path.exists(sp) and "DRY-RUN OK" in r6.stdout)

print(f"TOTAL FAILURES: {fails}")
shutil.rmtree(fake, ignore_errors=True)
sys.exit(1 if fails else 0)
