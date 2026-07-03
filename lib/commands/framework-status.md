---
name: framework-status
description: 顯示 framework 啟用狀態、recipe、roles、active brief、trust mode
allowed-tools: Read, Glob
---

# /framework-status

顯示 framework 整體狀態（read-only）。

## 用法

```
/framework-status
```

## 行為

```
1. 偵測啟用狀態：
   - .framework/.initialized 存在？
   - .framework/lib/core/control-plane.md 存在？
   - FRAMEWORK_DISABLED env 設定？
   - .claude/settings.local.json 內 framework_disabled？
2. Read .framework/.initialized 取設定
3. Glob .claude/agents/ 列 role
4. Glob .claude/skills/ 列 skill
5. Glob .framework/codex/ 列 codex
6. Read .framework/briefs/_active.yaml（若存在）
7. 格式化顯示
```

## 顯示範例

```
==========================================
Framework 狀態
==========================================

啟用狀態：✓ 已啟用
框架版本：0.6.0（範例值；實際以 .framework/lib/VERSION 為準）
初始化時間：2026-05-04 14:30
Recipe：dev-team
Trust mode：standard
Worktree：enabled

──────────────────────────────────────────
Roles（4）
──────────────────────────────────────────
  planner             producer  tier=mid   skills=[git-diff-analysis]
  planning-reviewer   reviewer  tier=mid
  engineer            producer  tier=mid   skills=[git-diff-analysis]
  code-reviewer       reviewer  tier=mid   skills=[code-review-checklist, git-diff-analysis]

──────────────────────────────────────────
Skills（2）
──────────────────────────────────────────
  code-review-checklist  global  v1.0.0
  git-diff-analysis      global  v1.0.0

──────────────────────────────────────────
Codex（2）
──────────────────────────────────────────
  planner.md   v0.1.0  last_updated=2026-05-04 (init)
  engineer.md  v0.3.2  last_updated=2026-05-06 (brief-2026-05-06-x)

──────────────────────────────────────────
Active Brief
──────────────────────────────────────────
  brief_id：2026-05-06-slot-revenue-q2
  phase：executing
  啟動：1h 23m ago
  最後活動：2m ago
  訪談：7/20

  詳細進度：/brief-status

──────────────────────────────────────────
Memory
──────────────────────────────────────────
  lessons/  3 categories, 12 條
  patterns/ 3 categories, 8 條
  sessions/ 23 個歷史 brief

──────────────────────────────────────────
Knowledge Base
──────────────────────────────────────────
  connected (<knowledge_base.path>)  promote=on  recall=on

==========================================
```

> Knowledge Base 區：`.initialized` 有 `knowledge_base` → 顯示 `connected (path) promote=.. recall=..`；無 → `not connected (local-only)`。

## 異常顯示

```
若 framework 未啟用：
  Framework 狀態：✗ 未啟用
  原因：{具體原因，如「環境變數 FRAMEWORK_DISABLED=1」/「.framework/.initialized 不存在，請執行 /framework-init」}
```

## 不做的事

- 不修改任何檔
- 不顯示 brief 詳細進度（用 `/brief-status`）

## 相關指令

- `/framework-init`
- `/framework-role-list`
- `/framework-recall`（若已連接外部 KB）
- `/brief-status`
