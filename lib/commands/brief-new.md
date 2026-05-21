---
name: brief-new
description: 開新 brief（短訪談 → 建 brief.md → 進入 Explore 階段）
allowed_tools: Read, Write, Edit, Glob, Grep, Task
---

# /brief-new

開啟新 brief，開始一個正式的批次工作。

## 用法

```
/brief-new                # 互動式（先問需求描述）
/brief-new "需求描述"      # 直接給需求
```

## 前置條件

- Framework 已 init（`.framework/.initialized` 存在）
- 無 active brief（`.framework/briefs/_active.yaml` 不存在）。若有 → 提示使用者選：等待 / 升級為 sub-brief / 取消當前

## 對話流程

### Step 1. 收需求

```
請描述你的需求（一行或多行）：
> ____
```

或從 `/brief-new "..."` 直接取得。

### Step 2. Recipe / Pipeline 推薦

```
偵測到關鍵字：cohort, revenue, Q2 slot game

建議：
  - Pipeline: full_advisory
  - Roster: data-analyst, analysis-reviewer, writer

接受？(y / edit / other)
> ____
```

- `y` → 用建議
- `edit` → 改 roster（增刪 role）
- `other` → 列 pipeline 選單從中選

### Step 3. 建 brief 目錄

```
1. 計算 brief_id：{today}-{slug from 需求標題}
   範例：2026-05-06-slot-revenue-q2
2. 建立目錄：.framework/briefs/{brief_id}/
3. 寫 brief.md（使用者描述 + recipe + roster）
4. 寫 _active.yaml（含 brief_id, started_at, phase: exploring）
5. 寫 _tree.yaml（root node, state: exploring）
6. 寫 _manifest.md（人類可讀進度）
```

### Step 4. 進入 Explore Step 2-6

依 `.framework/lib/core/control-plane.md` 第 4 節 Explore 流程：
- Step 2 情報蒐集（main 自動）
- Step 3 訪談（grill-me，cap 20 題）
- Step 4 plan 草稿
- Step 5 plan 審核
- Step 6 等使用者 `/brief-approve`

## brief.md 模板

```markdown
# Brief: {title}

## 原始需求

{usage 描述原文}

## 元資料

- brief_id: {YYYY-MM-DD-slug}
- created_at: {ISO timestamp}
- pipeline: {pipeline_name}
- roster: [data-analyst, analysis-reviewer, writer]
- recipe: {selected_recipe}

## Directive（追加指令，可空）

（使用者可在此追加單次任務指令，例：「特別注意 SOX 合規」）

```

## 異常

| 狀況 | 處理 |
|---|---|
| 已有 active brief | 提示：(a) 等當前完成 (b) 取消當前再開新 (c) 加為 sub-brief |
| 需求描述 < 10 字 | 提示「太短，請具體描述」，重問 |
| 需求描述純標題（無動作詞） | 提示「請說明你想要什麼產出」，重問 |
| Recipe 不匹配任何已 init 的設定 | 顯示錯誤 + 建議 `/framework-init --reset` 或 `/framework-role-add` |

## 與其他指令搭配

- 開好 brief 後：等 main 跑完 Explore Step 2-5 → 進入 awaiting_approval → 使用者 `/brief-approve`
- 中途取消：`/brief-cancel`
- 查狀態：`/brief-status`
- 想參考其他 repo 的做法：`/framework-recall <主題>`（需已連接外部 KB；main 會把結果折進本 brief 的 intel-pack）

## 相關文件

- `.framework/lib/core/control-plane.md`：Explore 階段細節
- `.framework/lib/core/clarification.md`：grill-me 規則（cap 20 題）
- `.framework/lib/core/e2r-tree.md`：_tree.yaml schema
- `.framework/lib/core/batch-lock.md`：_active.yaml 語意
