---
name: framework-pipeline-edit
description: 改 .framework/pipeline.yaml（加 stage / 改依賴 / 改 reviewer 配對）
allowed-tools: Read, Edit, Glob
---

# /framework-pipeline-edit

對話式修改 `.framework/pipeline.yaml`。也可直接用編輯器改 yaml（兩條路徑都合法）。

## 用法

```
/framework-pipeline-edit
/framework-pipeline-edit --pipeline <name>   # 直接編特定 pipeline
```

## 對話流程

```
1. Read .framework/pipeline.yaml
2. 顯示當前 pipelines（list 出每條 pipeline 的 stages DAG）
3. 顯示選單：
   (1) 改既有 pipeline 的 stage 配置
   (2) 加 stage 到 pipeline
   (3) 移除 stage
   (4) 改 stage 的 role / reviewer / depends_on
   (5) 加新 pipeline
   (6) 移除 pipeline
   (7) 改 default pipeline
   (8) 改 review_rounds_override
   (9) 直接開檔自己改（顯示路徑後退出）
   (10) 取消
```

### 加 stage

```
要加到哪條 pipeline？
> new_feature

Stage 名稱？
> documentation

Producer role？（必為 .claude/agents/ 已存在的 role）
> documentation-writer

Reviewer role？（可為 null）
> editor

Depends on？（其他 stage 名稱，逗號分隔；可空）
> [planning, engineering]
```

### 改 stage

```
選 pipeline / stage：
  new_feature.engineering

當前配置：
  role: engineer
  reviewer: code-reviewer
  depends_on: [planning]
  skills_extra: []
  worktree: inherit
  review_rounds: null

要改哪個欄位？(role/reviewer/depends_on/skills_extra/worktree/review_rounds/done)
> ____
```

## 驗證

每修改後 main 驗證：
- role / reviewer 存在於 .claude/agents/
- depends_on 引用的 stage 存在於同 pipeline
- 無循環依賴（topological sort）
- review_rounds 數值合法（same_role_max ≤ total_max）

驗證失敗 → 拒寫 + 顯示具體錯誤。

## 衝擊偵測

修改後若：
- 移除 stage 但其他 stage depends_on 仍引用 → 拒絕，提示先改 depends_on
- 改 default pipeline → 提示「下次 brief 用此條」
- 改了 stage 數 → 影響 worktree 數（dev-team），提示

## 不做的事

- 不改其他檔（codex / agents / etc.）
- 不取消當前 active brief（即使 active brief 用了此 pipeline）—— 只影響下次 brief

## 相關指令

- `/framework-status`
- `/framework-role-list`
