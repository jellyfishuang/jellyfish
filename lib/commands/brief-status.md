---
name: brief-status
description: 顯示當前 active brief 進度與近期完成 brief
allowed-tools: Read, Glob, Grep
---

# /brief-status

顯示 brief 進度（不修改任何檔）。

## 用法

```
/brief-status              # 顯示當前 active brief + 近 5 個歸檔 brief 摘要
/brief-status all          # 列所有歷史 brief（含歸檔）
/brief-status {brief_id}   # 單一 brief 詳細
```

## 行為（無參數）

```
1. 讀 .framework/briefs/_active.yaml
2. 若無 active：
   顯示「目前無 active brief」+ 近 5 個歸檔（從 .framework/memory/sessions/ 排序取最近）
3. 若有 active：
   讀 .framework/briefs/{brief_id}/_tree.yaml + _manifest.md
   格式化顯示
```

## 顯示格式（active brief）

```
==========================================
當前 active brief: 2026-05-06-slot-revenue-q2
==========================================

階段：Execute
Recipe: data-analytics
Pipeline: full_advisory
啟動時間：2026-05-06 10:00 (1h 23m ago)

────────────────────────────────────────
L0: 2026-05-06-slot-revenue-q2
   State: executing
   Roster: data-analyst, analysis-reviewer, writer
   Plan: ./plan.md (批准於 10:30)

   Sub-briefs:
   ├─ .a   state=done    (research+analysis 完成 11:15)
   │       amendments: a1 done (13:08) | a2 amending
   ├─ .b   state=executing  stage=writing  round 1
   └─ .c   state=pending  depends_on=[a]
────────────────────────────────────────

最新 verdict（讀 _manifest.md 末段）：
  [11:42] writer Round 1 → producer pass
  [11:43] editor Round 1 → reviewer fail (cohort 描述不一致)

下一步：
  - sub-brief .b stage writing 進入 round 2
  - sub-brief .c 等 .a done（已 done，等 main 排程）
  - sub-brief .a amendment a2 在訪談中（/brief-amend 流程未完）

============================
近期歸檔 brief（最近 5 個）：
============================
- 2026-05-04-tax-policy-summary    [done] (.framework/memory/sessions/...)
- 2026-05-02-feature-x-rollout     [done]
- 2026-04-30-bug-login-flow        [done]
- 2026-04-28-q1-report             [cancelled]
- 2026-04-25-cache-redesign        [done]
```

## Amendment 顯示規則

讀 `_tree.yaml.nodes.{sub_id}.amendments[]`：

- 若陣列為空或欄位缺失 → **不顯示** amendment 行（保持輸出乾淨）
- 若有任一非終態（`amending`） → 列在「下一步」區塊
- 列條目格式：`a{n} {state}{若終態 + 完成時間}`，多項用 `|` 分隔
- 終態（`done` / `done_with_notes` / `rejected` / `cancelled`）只在 sub-brief 行下方顯示，不重複進「下一步」

範例：
```
amendments: a1 done (13:08) | a2 done_with_notes (13:30) | a3 amending
```

## 顯示格式（無 active）

```
目前無 active brief。

============================
近期歸檔 brief（最近 5 個）：
============================
（同上）

開新 brief: /brief-new
```

## 顯示格式（特定 brief_id）

```
==========================================
Brief: 2026-05-04-tax-policy-summary
==========================================

State: done
Recipe: research-team
Pipeline: full_research
持續時間：2h 15m

關鍵時間軸（從 _manifest.md）：
[10:00] 建立 brief
[10:08] Explore 完成（5 題訪談）
[10:12] Plan 批准
[10:15] 開始 Execute（2 sub-briefs 並行）
[11:30] sub-brief .a done
[11:50] sub-brief .b done
[12:10] L0 holistic review pass
[12:15] 完成、歸檔

歸檔位置：.framework/briefs/_archive/2026-05/2026-05-04-tax-policy-summary/
Session 摘要：.framework/memory/sessions/2026-05-04-tax-policy-summary.md
```

## 行為（all）

```
列所有歷史 brief（從 .framework/memory/sessions/ + .framework/briefs/_archive/ 掃）：
- 按時間倒序
- 顯示：id / state / recipe / 完成時間
- 上限顯示 30 個（更多請直接看 .framework/memory/sessions/）
```

## 異常

| 狀況 | 處理 |
|---|---|
| _active.yaml 存在但 _tree.yaml 缺失 | 顯示警告：「狀態檔不一致，建議 /framework-recover」 |
| brief_id 不存在（特定查詢） | 顯示錯誤：「找不到 {brief_id}」+ 列近期 brief |
| _manifest.md 解析失敗 | 顯示原始內容，警告解析失敗 |

## 不做的事

- **不修改任何檔**（純讀取）
- **不取消 / 不接續**（要這些用 `/brief-cancel` / `/framework-recover`）
- **不展開 stage 內細節到逐 verdict**（要看細節直接 Read `.framework/briefs/{id}/sub-briefs/{sub_id}/stages/`）

## 相關指令

- `/brief-amend <sub_id> "..."` — 對 done 的 sub-brief 做輕量修訂
- `/brief-cancel` — 取消當前
- `/brief-reopen <id>` — 重啟歸檔（Phase B 才實作）
- `/framework-recover` — 從中斷恢復
- `/framework-status` — framework 整體狀態（roles / settings）

## 相關文件

- `.framework/lib/core/e2r-tree.md`：_tree.yaml schema（含 amendments 欄位）
- `.framework/lib/core/batch-lock.md`：_active.yaml schema
- `.framework/lib/core/amendment.md`：amendment 流程規範
