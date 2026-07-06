#!/usr/bin/env python3
"""_tree.yaml canonical schema 機械 lint (e2r-tree.md §1.4 / §2.2 / §3.1)。「禁止自由發揮」的機械化。

用法 (Python 3):
  python3 tree_check.py <brief_dir | _tree.yaml>

檢查:
  頂層鍵: root(字串) / created_at / last_updated / nodes 必在; root id 必在 nodes 下
  禁攤平: nodes.{id}.* 欄位 (state/children/pipeline_stages/...) 不得出現在頂層 (§1.4)
  node state ∈ {pending, exploring, awaiting_approval, executing, reviewing, paused, done, failed, cancelled}
  stage state ∈ {pending, running, done, failed, paused, skipped}
  brief_stages.{x}.state ∈ {pending, running, pass, fail, skipped}
  stage verdict ∈ 7 verdict 枚舉 + skipped + null
  holistic_review ∈ {null, pass, fail}
exit: 0 過 / 1 檔案錯 / 2 違規 (列明細)。"""
import os
import re
import sys

NODE_STATES = {"pending", "exploring", "awaiting_approval", "executing", "reviewing", "paused", "done", "failed", "cancelled"}
STAGE_STATES = {"pending", "running", "done", "failed", "paused", "skipped"}
BRIEF_STAGE_STATES = {"pending", "running", "pass", "fail", "skipped"}
VERDICTS = {"pass", "fail", "ambiguity", "needs_decomposition", "needs_dependency", "tool_error", "partial", "skipped", "null"}
FLAT_FORBIDDEN = {"state", "children", "parent", "roster", "pipeline_stages", "depends_on", "artifact",
                  "started_at", "completed_at", "rounds", "worktree", "amendments", "decomposition_origin"}
HOLISTIC = {"null", "pass", "fail"}


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    target = os.path.abspath(sys.argv[1])
    path = os.path.join(target, "_tree.yaml") if os.path.isdir(target) else target
    if not os.path.isfile(path):
        print(f"_tree.yaml 不存在: {path}", file=sys.stderr)
        return 1
    lines = open(path, encoding="utf-8").read().splitlines()

    errs = []
    top = {}          # 頂層 key -> value
    node_ids = set()
    in_nodes = False
    ctx = None        # None | "node" | "pipeline_stages" | "brief_stages"

    for i, raw in enumerate(lines, 1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        m = re.match(r"^(\s*)(- )?([\w.\-]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(3), m.group(4).strip()

        if indent == 0:
            top[key] = val
            in_nodes = key == "nodes"
            ctx = None
            if key in FLAT_FORBIDDEN:
                errs.append(f"L{i}: 頂層出現 nodes 欄位 '{key}'——禁止把 nodes.{{id}}.* 攤平 (e2r-tree §1.4)")
            continue
        if not in_nodes:
            continue
        if indent == 2 and not m.group(2):
            node_ids.add(key)
            ctx = "node"
            continue
        if key == "pipeline_stages":
            ctx = "pipeline_stages"
        elif key == "brief_stages":
            ctx = "brief_stages"
        elif indent == 4 and key not in ("state",):
            if ctx in ("pipeline_stages", "brief_stages") and key not in ("name", "rounds", "verdict",
                                                                          "started_at", "completed_at",
                                                                          "result_summary", "on_fail_choice",
                                                                          "report_path", "comment"):
                ctx = "node"

        if key == "state":
            v = val or "null"
            if ctx == "pipeline_stages":
                if v not in STAGE_STATES:
                    errs.append(f"L{i}: stage state 非法 '{v}' (允許 {sorted(STAGE_STATES)})")
            elif ctx == "brief_stages":
                if v not in BRIEF_STAGE_STATES:
                    errs.append(f"L{i}: brief_stages state 非法 '{v}' (允許 {sorted(BRIEF_STAGE_STATES)})")
            else:
                if v not in NODE_STATES:
                    errs.append(f"L{i}: node state 非法 '{v}' (允許 {sorted(NODE_STATES)}；"
                                f"常見錯: completed/passed/l0_review_passed → 用 done)")
        elif key == "verdict" and ctx == "pipeline_stages":
            if (val or "null") not in VERDICTS:
                errs.append(f"L{i}: stage verdict 非法 '{val}'")
        elif key == "holistic_review":
            if (val or "null") not in HOLISTIC:
                errs.append(f"L{i}: holistic_review 非法 '{val}' (允許 null|pass|fail)")

    for k in ("root", "created_at", "last_updated", "nodes"):
        if k not in top:
            errs.append(f"缺頂層鍵: {k}")
    root = top.get("root", "")
    if root and (root.startswith("{") or not root):
        errs.append(f"root 須為 brief id 字串: '{root}'")
    if root and node_ids and root not in node_ids:
        errs.append(f"root id '{root}' 不在 nodes 之下")

    if errs:
        print("_tree.yaml schema 違規:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 2
    print(f"TREE OK  root={root} nodes={len(node_ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
