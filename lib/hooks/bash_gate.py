#!/usr/bin/env python3
"""PreToolUse gate (matcher: Bash)
docker rm/rmi/prune (子指令位置, 容許 flag+value)、compose down -v -> deny;
compose down -> ask; git commit/push -> ask。
比對前剝除 heredoc body/跳脫序列/引號內容, 換行視同指令分隔, docker-compose 正規化, 空白摺疊。
內部錯誤一律 fail-open (exit 0) 並記 gate.log。"""
import datetime
import json
import os
import re
import sys

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate.log")

SEG = r"[^|;&\n]*"  # 同一指令段 (|;& 與換行視同分隔)
FLAGS = r"(?:--?\S+(?:[ \t]+[^\s|;&-]\S*)?[ \t]+)*"  # dashed flag, 可帶一個 value token
RE_DOCKER_RM = re.compile(
    rf"\bdocker\b[ \t]+{FLAGS}(?:(?:container|image|volume|compose)[ \t]+{FLAGS})?(?:rm|rmi)\b", re.I)
RE_DOCKER_PRUNE = re.compile(
    rf"\bdocker\b[ \t]+{FLAGS}(?:(?:system|container|image|volume|network|builder)[ \t]+{FLAGS})?prune\b", re.I)
RE_COMPOSE_DOWN = re.compile(rf"\b(?:docker[ \t]+compose|compose)\b{SEG}\bdown\b", re.I)
RE_DOWN_VOLUMES = re.compile(rf"\bdown\b{SEG}(?:[ \t]-\w*v\b|[ \t]--volumes\b)", re.I)
RE_GIT_COMMIT_PUSH = re.compile(rf"\bgit\b{SEG}\b(?:commit|(?<!stash )push)\b", re.I)


def _san(s):
    return s.replace("\n", "\\n")[:200]


def _log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} [bash_gate] {msg}\n")
    except Exception:
        pass


def _ask(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": reason,
    }}, ensure_ascii=False))
    sys.exit(0)


def _deny(reason):
    print(reason, file=sys.stderr)
    sys.exit(2)


def _scrub(cmd):
    cmd = re.sub(r"<<-?[ \t]*(['\"]?)(\w+)\1[\s\S]*?\n\t*\2(?=[ \t]*(?:\n|$))", " <<HEREDOC", cmd)
    cmd = re.sub(r"\\\n", " ", cmd)            # line continuation 視同接續同段
    cmd = re.sub(r"\\.", "", cmd)              # 跳脫序列是字面字元, 先移除防引號假配對
    cmd = re.sub(r"(?<=\w)'(?=\w)", "", cmd)   # 字中撇號 (don't) 不參與引號配對
    cmd = re.sub(r"'[^']*'", "''", cmd)
    cmd = re.sub(r'"[^"]*"', '""', cmd)
    cmd = re.sub(r"\bdocker-compose\b", "docker compose", cmd, flags=re.I)
    cmd = re.sub(r"[ \t]+", " ", cmd)          # 摺空白, lookbehind 對多空白也成立
    return cmd


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception as e:
        _log(f"payload parse error: {e}")
        return
    cmd = (data.get("tool_input") or {}).get("command") or ""
    scrubbed = _scrub(cmd)

    if RE_DOCKER_RM.search(scrubbed):
        _log(f"deny docker-rm: {_san(cmd)}")
        _deny("禁用 docker rm/rmi: 測試收尾只允許 docker stop, 容器保留供使用者重用")

    if RE_DOCKER_PRUNE.search(scrubbed):
        _log(f"deny docker-prune: {_san(cmd)}")
        _deny("禁用 docker prune: 會批量刪除容器/映像/volume, 清理由使用者親自執行")

    if RE_COMPOSE_DOWN.search(scrubbed):
        if RE_DOWN_VOLUMES.search(scrubbed):
            _log(f"deny compose-down-v: {_san(cmd)}")
            _deny("禁用 docker compose down -v: 會刪除 volume; 收尾用 docker compose stop")
        _log(f"ask compose-down: {_san(cmd)}")
        _ask("docker compose down 會刪除容器, 收尾慣例是 stop; 確定要 down 才放行")

    if RE_GIT_COMMIT_PUSH.search(scrubbed):
        _log(f"ask git-commit-push: {_san(cmd)}")
        _ask("git commit/push 由使用者親自執行 (CLAUDE.md multi-repo 鐵律); 使用者已明確要求才放行")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        _log(f"unexpected error: {e}")
    sys.exit(0)
