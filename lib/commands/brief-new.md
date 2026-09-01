---
name: brief-new
description: 開新 brief（短訪談 → 建 brief.md → 進入 Explore 階段）
allowed-tools: Read, Write, Edit, Glob, Grep, Task
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
- **Admission 閘通過**（multi-lane，batch-lock.md §3.1）：本 brief 的預估 `affected_repos` 與
  所有 active lane 的 scope、無主 dirty 工作樹皆無交集。**不再是「無 active brief」**——
  repo-disjoint 的 brief 可與現有 lane 並行（各自獨立 session 跑）
- 偵測到 legacy 單檔 `.framework/briefs/_active.yaml` → 先提示搬遷至 registry（batch-lock.md §8）

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

### Step 2.5. Admission 閘（multi-lane）

```
1. 從需求描述預估 affected_repos（不確定時問使用者一句；寧可估寬——approve 時會收斂）
2. 跑 C:/Python312/python.exe .framework/scripts/scope_check.py --overlap <預估 repos 逗號串>
3. 無交集（exit 0）→ 顯示 active lanes 摘要供確認 → 進 Step 3
4. 有交集（exit 2）→ 顯示衝突歸屬（repo ← lane / 無主 dirty），使用者選：
   (a) 等待該 lane 完成（可先把需求寫進 briefs/inbox/ 排隊，檔內宣告 affected_repos）
   (b) 取消衝突 lane，開新的（丟該 lane 進度，二次確認；只能取消本人 lane）
   (c) 升級為該 lane 的 sub-brief（manual integrate：修該 brief 的 plan）
   (d) 改 scope 避開衝突 repo → 重跑閘
```

### Step 3. 建 brief 目錄

```
1. 計算 brief_id：{today}-{slug from 需求標題}
   範例：2026-05-06-slot-revenue-q2
2. 建立目錄：.framework/briefs/{brief_id}/
3. 寫 brief.md（使用者描述 + recipe + roster）
4. 寫 _active/{brief_id}.yaml（含 brief_id, started_at, phase: exploring,
   affected_repos: [預估值], scope_status: provisional；檔名必等於 brief_id）
5. 寫 _tree.yaml（root node, state: exploring）
6. 寫 _manifest.md（人類可讀進度）
7. 自驗：絕對路徑 ls 確認 lock 落在 .framework/briefs/_active/（control-plane §8.8）
```

### Step 4. 進入 Explore Step 2-6

依 `.framework/lib/core/control-plane.md` 第 4 節 Explore 流程：
- Step 2 情報蒐集（main 自動）
- Step 3 理解草稿 + 紅筆（draft+redline 預設；真分岔題 cap 20，逐題 grill-me 為 fallback）
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
| Admission 閘撞鎖（scope 交集） | Step 2.5 四選項：(a) 等待/排 inbox (b) 取消衝突 lane (c) 加為其 sub-brief (d) 改 scope |
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
- `.framework/lib/core/clarification.md`：釐清規則（§2.5 draft+redline 預設 + 逐題 fallback，cap 20 題）
- `.framework/lib/core/e2r-tree.md`：_tree.yaml schema
- `.framework/lib/core/batch-lock.md`：lock registry 語意、admission 閘、multi-lane 並發規則
