#!/usr/bin/env python3
"""Sub-brief 工作成果快照: 把 repo 的 working tree 相對 HEAD 的完整變更 (含 untracked 新檔) 存成可 apply 的 patch。

用法 (Python 3):
  python3 patch_dump.py <repo_dir> <out_patch>

行為:
  用臨時 index (GIT_INDEX_FILE) 做 read-tree HEAD → add -A → diff --binary --cached HEAD,
  不碰真實 index / stage / working tree (使用者的 git 狀態零改變)。
  patch 含: tracked 修改/刪除 + untracked 新檔 (尊重 .gitignore) + binary 內容 (--binary)。
  還原方式: 在乾淨的同 HEAD checkout 上 `git apply <patch>`。
  無變更 → 寫空檔 (仍 exit 0, 供「已 dump」存在性檢查)。
exit: 0 成功 / 1 錯誤 (非 git repo / 無 HEAD / git 失敗)。"""
import os
import subprocess
import sys
import tempfile


def run_git(repo, args, env=None, binary=False):
    r = subprocess.run(["git", "-C", repo] + args, capture_output=True, env=env)
    out = r.stdout if binary else r.stdout.decode("utf-8", errors="replace")
    return r.returncode, out, r.stderr.decode("utf-8", errors="replace")


def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 1
    repo, out_patch = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    if not os.path.isdir(os.path.join(repo, ".git")):
        print(f"非 git repo: {repo}", file=sys.stderr)
        return 1
    rc, head, err = run_git(repo, ["rev-parse", "HEAD"])
    if rc != 0:
        print(f"無 HEAD (空 repo?): {err.strip()}", file=sys.stderr)
        return 1

    fd, tmp_index = tempfile.mkstemp(prefix="patch_dump_idx_")
    os.close(fd)
    os.remove(tmp_index)  # read-tree 自建
    env = dict(os.environ, GIT_INDEX_FILE=tmp_index)
    try:
        rc, _, err = run_git(repo, ["read-tree", "HEAD"], env=env)
        if rc != 0:
            print(f"read-tree 失敗: {err.strip()}", file=sys.stderr)
            return 1
        rc, _, err = run_git(repo, ["add", "-A", "."], env=env)
        if rc != 0:
            print(f"add -A (臨時 index) 失敗: {err.strip()}", file=sys.stderr)
            return 1
        rc, names, _ = run_git(repo, ["diff", "--cached", "--name-only", "HEAD"], env=env)
        rc, patch, err = run_git(repo, ["diff", "--binary", "--cached", "HEAD"], env=env, binary=True)
        if rc not in (0, 1):
            print(f"diff 失敗: {err.strip()}", file=sys.stderr)
            return 1
    finally:
        if os.path.exists(tmp_index):
            os.remove(tmp_index)

    os.makedirs(os.path.dirname(out_patch) or ".", exist_ok=True)
    with open(out_patch, "wb") as f:
        f.write(patch)
    n = len([x for x in names.splitlines() if x.strip()])
    print(f"repo: {repo}")
    print(f"HEAD: {head.strip()[:12]}  變更檔數: {n}  patch bytes: {len(patch)}")
    print(f"寫入: {out_patch}" + ("  (無變更, 空 patch)" if n == 0 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
