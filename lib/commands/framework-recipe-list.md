---
name: framework-recipe-list
description: 列出 framework 內建 recipes（read-only）
allowed_tools: Read, Glob
---

# /framework-recipe-list

列 `.framework/lib/recipes/` 內所有可用 recipe。

## 用法

```
/framework-recipe-list
/framework-recipe-list <name>    # 顯示特定 recipe 詳細
```

## 顯示範例

```
Framework 內建 Recipes（6）：

╭─────────────────────┬───────────────────────────────────────╮
│ Name                │ 描述                                  │
├─────────────────────┼───────────────────────────────────────┤
│ dev-team            │ 開發 / 寫 code / 修 bug               │
│ research-team       │ 研究 / 分析 / 給建議                  │
│ writing-team        │ 寫作 / 編輯                          │
│ finance-advisory    │ 金融顧問（research + analysis + writing） │
│ data-analytics      │ 數據分析                             │
│ general-assistant   │ 通用助理                             │
╰─────────────────────┴───────────────────────────────────────╯

當前專案使用的 recipe：dev-team

要看 recipe 詳細：
  /framework-recipe-list <name>
要改用其他 recipe：
  /framework-init --reset（會重新走 init 流程）
```

## 詳細顯示（特定 recipe）

```
==========================================
Recipe: finance-advisory
==========================================

描述：金融顧問場景套裝
版本：1.0.0

Roles：
  - researcher
  - source-quality-reviewer
  - financial-analyst
  - reasoning-reviewer
  - writer
  - editor

Skills：
  - source-evaluation
  - citation-discipline
  - dcf-valuation
  - scenario-analysis
  - reasoning-bias-checklist
  - technical-writing-style

Pipelines：
  - full_advisory（research → analysis → writing）
  - quick_lookup（main 直接處理）

Trust mode 預設：standard
Worktree 預設：disabled

Init 客製問題（finance-advisory 專屬）：
  Q. 主要分析範圍？（會寫進 financial-analyst 的 codex）
  Q. 來源語言（中文 / 英文）？
  Q. 報告格式偏好（短摘要 / 完整報告）？
```

## 不做的事

- 不切換當前 recipe（要切換用 `/framework-init --reset`）
- 不修改 recipe yaml（recipe 是 framework 內建，不可改；客製化用 `.claude/agents/` fork）

## 相關指令

- `/framework-init --reset`
- `/framework-status`
