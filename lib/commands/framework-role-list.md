---
name: framework-role-list
description: 列出當前專案所有 role 與職責摘要
allowed_tools: Read, Glob
---

# /framework-role-list

列出 `.claude/agents/` 內所有 role（read-only）。

## 用法

```
/framework-role-list
/framework-role-list --verbose    # 含 path boundaries / 鐵律摘要
```

## 行為

```
1. Glob .claude/agents/*.md
2. 對每 role 解析 frontmatter
3. 格式化顯示
```

## 顯示範例（預設）

```
當前 roles（4）：

╭─────────────────────┬──────────┬──────┬──────────────────────────╮
│ Name                │ Type     │ Tier │ 職責                     │
├─────────────────────┼──────────┼──────┼──────────────────────────┤
│ planner             │ producer │ mid  │ 寫實作規格書              │
│ planning-reviewer   │ reviewer │ mid  │ 審 plan.md                │
│ engineer            │ producer │ mid  │ 在 worktree 內實作 code   │
│ code-reviewer       │ reviewer │ mid  │ 審 code 變動              │
╰─────────────────────┴──────────┴──────┴──────────────────────────╯

要查看某個 role 詳細：cat .claude/agents/{name}.md
要管理：/framework-role-add/edit/remove
```

## --verbose 模式

每個 role 額外顯示：
- skills 列表
- codex 路徑（若存在）
- memory.consume / contribute
- Path Boundaries 摘要
- 鐵律前 3 條

## 不做的事

- 不修改 role
- 不解析 body（除 --verbose 摘要）

## 相關指令

- `/framework-role-add`
- `/framework-role-edit <name>`
- `/framework-role-remove <name>`
- `/framework-status`
