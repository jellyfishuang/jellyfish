#!/usr/bin/env python3
"""Gate scripts 回歸測試 (62 case, 含三輪對抗式驗證回饋案例)。
測試對象 = 本檔同目錄的 bash_gate.py / path_gate.py / fullwidth_gate.py。
用法: python run_tests.py  (期望輸出 FAILURES: 0)"""
import json
import os
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
for script, payload, want in cases:
    r = subprocess.run([PY, os.path.join(HERE, script + ".py")],
                       input=json.dumps(payload).encode("utf-8"), capture_output=True)
    got = classify(r.returncode, r.stdout.decode("utf-8", "replace"))
    ok = got == want
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} {script:15s} want={want:5s} got={got:5s} :: {json.dumps(payload)[:88]}")
    if not ok:
        print("     stderr:", r.stderr.decode("utf-8", "replace").replace(NL, " | ")[:200])
print(f"TOTAL {len(cases)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
