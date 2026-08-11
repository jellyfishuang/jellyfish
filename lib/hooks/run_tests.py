#!/usr/bin/env python3
"""Gate scripts 回歸測試 (84 case, 含三輪對抗式驗證回饋案例 + mandate ask 升級 deny)。
測試對象 = 本檔同目錄的 bash_gate.py / path_gate.py / fullwidth_gate.py (+ gate_mandate.py)。
case 以 GATE_BRIEFS_DIR 注入 briefs fixture 與真實 repo 隔離; DEFAULT_PATH/NOMOD 哨兵改跑
fakeroot 副本 (不設環境變數), 驗 __file__ 相對預設路徑與 import 失敗回退。
用法: python run_tests.py  (期望輸出 FAILURES: 0)"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
FIX = tempfile.mkdtemp(prefix="gate_fixtures_")
NL = chr(10)

with open(os.path.join(FIX, "bad.go"), "w", encoding="utf-8") as f:
    f.write("package main" + NL * 2
            + "// 這行註解有全形逗號，應該被攔" + NL
            + 'var s = "字串內全形，不該攔"' + NL * 2
            + "var raw = `raw 多行" + NL + "字串，也不該攔" + NL + "結束`" + NL * 2
            + "// 半形註解 ok, 不攔" + NL
            + "func main() {} // 這行也有全形句號。應該被攔" + NL)
with open(os.path.join(FIX, "clean.go"), "w", encoding="utf-8") as f:
    f.write("package main" + NL * 2 + "// 全部半形標點, 乾淨檔案 (ok)" + NL
            + 'var s = "字串內全形，合法"' + NL * 2 + "func main() {}" + NL)
with open(os.path.join(FIX, "apos.go"), "w", encoding="utf-8") as f:
    f.write("package main" + NL * 2 + "// don't mix，don't do it" + NL + "func main() {}" + NL)

BAD_GO = os.path.join(FIX, "bad.go").replace("\\", "/")
CLEAN_GO = os.path.join(FIX, "clean.go").replace("\\", "/")
APOS_GO = os.path.join(FIX, "apos.go").replace("\\", "/")
NON_GO = os.path.abspath(__file__).replace("\\", "/")


def _briefs(name, active_yaml, mandate_json):
    root = os.path.join(FIX, name)
    os.makedirs(os.path.join(root, "test-brief"))
    if active_yaml is not None:
        with open(os.path.join(root, "_active.yaml"), "w", encoding="utf-8") as f:
            f.write(active_yaml)
    if mandate_json is not None:
        with open(os.path.join(root, "test-brief", "_mandate.json"), "w", encoding="utf-8") as f:
            f.write(mandate_json)
    return root


ACTIVE_YAML = "brief_id: test-brief" + NL + "phase: executing" + NL + "autonomous_mandate: _mandate.json" + NL
BRIEFS_NONE = os.path.join(FIX, "briefs_none")  # 無 _active.yaml -> mandate off (預設 fixture)
os.makedirs(BRIEFS_NONE)
BRIEFS_ACTIVE = _briefs("briefs_active", ACTIVE_YAML, '{"status": "active"}')
BRIEFS_CONSUMED = _briefs("briefs_consumed", ACTIVE_YAML, '{"status": "consumed"}')
BRIEFS_BROKEN = _briefs("briefs_broken", ACTIVE_YAML, '{status: active')
BRIEFS_NOPTR = _briefs("briefs_noptr", "brief_id: test-brief" + NL + "phase: executing" + NL, '{"status": "active"}')
BRIEFS_QUOTED = _briefs("briefs_quoted",
                        "brief_id: 'test-brief'" + NL + 'autonomous_mandate: "_mandate.json"  # 指針' + NL,
                        '{"status": "active"}')
BRIEFS_BOM_YAML = _briefs("briefs_bom_yaml", "\ufeff" + ACTIVE_YAML, '{"status": "active"}')
BRIEFS_BOM_JSON = _briefs("briefs_bom_json", ACTIVE_YAML, "\ufeff" + '{"status": "active"}')

# fakeroot: hooks/ 與 briefs/ 兄弟目錄, 不設 GATE_BRIEFS_DIR, 驗 __file__ 相對預設路徑 (../briefs)
DEFAULT_PATH = "__default__"      # 哨兵: 跑 FAKEHOOKS 副本
DEFAULT_NOMOD = "__default_nomod__"  # 哨兵: 跑無 gate_mandate.py 的副本, 驗 import 失敗回退 ask
FAKEHOOKS = os.path.join(FIX, "fakeroot", "hooks")
FAKEHOOKS_NOMOD = os.path.join(FIX, "fakeroot_nomod", "hooks")
for root, files in ((FAKEHOOKS, ("bash_gate.py", "path_gate.py", "gate_mandate.py")),
                    (FAKEHOOKS_NOMOD, ("bash_gate.py",))):
    os.makedirs(root)
    for fn in files:
        shutil.copy(os.path.join(HERE, fn), root)
    briefs = os.path.join(os.path.dirname(root), "briefs")
    os.makedirs(os.path.join(briefs, "test-brief"))
    with open(os.path.join(briefs, "_active.yaml"), "w", encoding="utf-8") as f:
        f.write(ACTIVE_YAML)
    with open(os.path.join(briefs, "test-brief", "_mandate.json"), "w", encoding="utf-8") as f:
        f.write('{"status": "active"}')

cases = [
    # --- bash_gate 基本 ---
    ("bash_gate", {"tool_input": {"command": 'cd Repo_X && git commit -m "x"'}}, "ask"),
    ("bash_gate", {"tool_input": {"command": "git -C Repo_X push origin main"}}, "ask"),
    ("bash_gate", {"tool_input": {"command": "docker rm sgc-mongo"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker container rm -f x"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker compose down -v"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker compose down"}}, "ask"),
    ("bash_gate", {"tool_input": {"command": "docker-compose down --volumes"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker stop sgc-mongo && docker ps"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "docker run --rm -it alpine sh"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "go build ./..."}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "git status && git log --oneline"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "git add -A; git status"}}, "pass"),
    ("bash_gate", {}, "pass"),
    # --- bash_gate 一輪對抗回饋 ---
    ("bash_gate", {"tool_input": {"command": "docker stop sgc-redis" + NL + "rm -f /tmp/out.log"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "docker compose down" + NL + "ls -lv"}}, "ask"),
    ("bash_gate", {"tool_input": {"command": "docker compose down" + NL + "docker volume ls -v"}}, "ask"),
    ("bash_gate", {"tool_input": {"command": "git status" + NL + "go build commit.go"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": 'grep -rn "docker rm" docs/'}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "cat > notes.md <<EOF" + NL + "cleanup: docker rm old" + NL + "EOF"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "docker stop rm-test"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "docker exec app cat /tmp/rm.log"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "docker container prune -f"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker system prune"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "DOCKER RM x"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "Git Commit -m x"}}, "ask"),
    ("bash_gate", {"tool_input": {"command": "git stash push -m wip"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "docker compose rm -f"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": 'docker rm "my db"'}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker volume rm x"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker compose down -t 5"}}, "ask"),
    # --- bash_gate 二輪對抗回饋 ---
    ("bash_gate", {"tool_input": {"command": "cat <<-EOF" + NL + "\tnote: docker rm old" + NL + "\tEOF"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "docker compose -f local.yml rm -sf"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker-compose rm -f svc"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker --context prod rm x"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker -H tcp://h:2375 rm x"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "echo Don't panic && docker rm x && echo That's it"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": 'echo \\" && git commit -m hi && echo \\"'}}, "ask"),
    ("bash_gate", {"tool_input": {"command": 'echo "escaped \\" prose docker rm x"'}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "git stash  push -m wip"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "git stash push && git push"}}, "ask"),
    ("bash_gate", {"tool_input": {"command": "docker compose exec app ls"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "docker system df"}}, "pass"),
    ("bash_gate", {"tool_input": {"command": "docker \\" + NL + " rm x"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker compose -f local.yml down -v"}}, "deny"),
    ("bash_gate", {"tool_input": {"command": "docker compose -f local.yml up -d"}}, "pass"),
    # --- path_gate ---
    ("path_gate", {"tool_input": {"file_path": "D:\\Proj\\Root\\.framework\\memory\\lessons\\x.md"}}, "ask"),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/.framework/memory/sessions/t.md"}}, "pass"),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/.Framework/Codex/engineer.md"}}, "ask"),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/.claude/skills/foo/SKILL.md"}}, "ask"),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/Repo_X/main.go"}}, "pass"),
    ("path_gate", {"tool_input": {"file_path": "C:/Users/x/.claude/projects/D--Proj-Root/memory/MEMORY.md"}}, "pass"),
    ("path_gate", {}, "pass"),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/.framework/memory/sessions/../lessons/x.md"}}, "ask"),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/.framework//memory/lessons/x.md"}}, "ask"),
    ("path_gate", {"cwd": "D:/Proj/Root/.framework/memory", "tool_input": {"file_path": "lessons/x.md"}}, "ask"),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/x.framework/memory.md"}}, "pass"),
    # --- fullwidth_gate ---
    ("fullwidth_gate", {"tool_input": {"file_path": BAD_GO}}, "deny"),
    ("fullwidth_gate", {"tool_input": {"file_path": CLEAN_GO}}, "pass"),
    ("fullwidth_gate", {"tool_input": {"file_path": APOS_GO}}, "deny"),
    ("fullwidth_gate", {"tool_input": {"file_path": FIX.replace("\\", "/") + "/nonexistent.go"}}, "pass"),
    ("fullwidth_gate", {"tool_input": {"file_path": NON_GO}}, "pass"),
    ("fullwidth_gate", {"tool_input": {"file_path": "D:/Proj/Root/Repo_Y/vendor/a.go"}}, "pass"),
    # --- mandate active: ask 升級 deny (gate_mandate) ---
    ("bash_gate", {"tool_input": {"command": 'git -C SGC_X commit -m "x"'}}, "deny", BRIEFS_ACTIVE),
    ("bash_gate", {"tool_input": {"command": "git push origin main"}}, "deny", BRIEFS_ACTIVE),
    ("bash_gate", {"tool_input": {"command": "docker compose down"}}, "deny", BRIEFS_ACTIVE),
    ("bash_gate", {"tool_input": {"command": "docker compose down -v"}}, "deny", BRIEFS_ACTIVE),
    ("bash_gate", {"tool_input": {"command": "docker stop sgc-mongo"}}, "pass", BRIEFS_ACTIVE),
    ("bash_gate", {"tool_input": {"command": "git status && git log --oneline"}}, "pass", BRIEFS_ACTIVE),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/.framework/memory/lessons/x.md"}}, "deny", BRIEFS_ACTIVE),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/.claude/skills/foo/SKILL.md"}}, "deny", BRIEFS_ACTIVE),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/.framework/memory/sessions/t.md"}}, "pass", BRIEFS_ACTIVE),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/Repo_X/main.go"}}, "pass", BRIEFS_ACTIVE),
    ("bash_gate", {"tool_input": {"command": "git commit -m x"}}, "deny", BRIEFS_QUOTED),
    ("bash_gate", {"tool_input": {"command": "git commit -m x"}}, "deny", BRIEFS_BOM_YAML),
    ("bash_gate", {"tool_input": {"command": "git commit -m x"}}, "deny", BRIEFS_BOM_JSON),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/.framework/codex/engineer.md"}}, "deny", BRIEFS_ACTIVE),
    ("bash_gate", {"tool_input": {"command": "git commit -m x"}}, "deny", DEFAULT_PATH),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/.framework/memory/lessons/x.md"}}, "deny", DEFAULT_PATH),
    ("bash_gate", {"tool_input": {"command": "git commit -m x"}}, "ask", DEFAULT_NOMOD),
    # --- mandate 非 active / 缺損: 回退 ask ---
    ("bash_gate", {"tool_input": {"command": "git commit -m x"}}, "ask", BRIEFS_CONSUMED),
    ("path_gate", {"tool_input": {"file_path": "D:/Proj/Root/.framework/memory/lessons/x.md"}}, "ask", BRIEFS_CONSUMED),
    ("bash_gate", {"tool_input": {"command": "git commit -m x"}}, "ask", BRIEFS_BROKEN),
    ("bash_gate", {"tool_input": {"command": "git commit -m x"}}, "ask", BRIEFS_NOPTR),
    ("bash_gate", {"tool_input": {"command": "git commit -m x"}}, "ask", os.path.join(FIX, "briefs_missing")),
]


def classify(rc, out):
    if rc == 2:
        return "deny"
    if rc == 0 and '"permissionDecision": "ask"' in out:
        return "ask"
    if rc == 0:
        return "pass"
    return f"rc={rc}"


fails = 0
for case in cases:
    script, payload, want = case[0], case[1], case[2]
    briefs = case[3] if len(case) > 3 else BRIEFS_NONE
    env = dict(os.environ)
    env.pop("GATE_BRIEFS_DIR", None)
    if briefs == DEFAULT_PATH:
        script_path = os.path.join(FAKEHOOKS, script + ".py")
    elif briefs == DEFAULT_NOMOD:
        script_path = os.path.join(FAKEHOOKS_NOMOD, script + ".py")
    else:
        script_path = os.path.join(HERE, script + ".py")
        env["GATE_BRIEFS_DIR"] = briefs
    r = subprocess.run([PY, script_path],
                       input=json.dumps(payload).encode("utf-8"), capture_output=True, env=env)
    got = classify(r.returncode, r.stdout.decode("utf-8", "replace"))
    ok = got == want
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} {script:15s} want={want:5s} got={got:5s} :: {json.dumps(payload)[:88]}")
    if not ok:
        print("     stderr:", r.stderr.decode("utf-8", "replace").replace(NL, " | ")[:200])
print(f"TOTAL {len(cases)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
