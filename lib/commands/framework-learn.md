---
name: framework-learn
description: 補處理已歸檔 brief 的 _suggestions / ad-hoc 加 lesson / pattern（無需開新 brief）
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /framework-learn

補學習迴圈缺口的 lightweight 入口——不依附 brief 流程，無 brief overhead，直接走 user approval → main 寫 memory。

對應 `core/learning-loop.md` 第 7 節 Step 4-5（user approval + main 寫入）。

## 設計理由

Framework 的鐵律「main 不直寫 memory」常被誤讀為「需要 planner agent 評估才能寫」→ 引導使用者開新 brief。**這是錯的**。鐵律的意思是 main 必走 user approval gate，**不是禁止 main 寫**。

當 brief 結束時 learning loop 應該自動跑 Step 2-5（顯示 suggest_* → 使用者答 y/n/edit → main 寫）。但實務上常見 main 漏跑或誤讀。`/framework-learn` 提供補救路徑：

- 補處理歸檔 brief 的 _suggestions
- Ad-hoc 加 lesson / pattern（無需依附任何 brief）
- 不需要開新 brief（避免 brief 數量爆炸）

## 用法

```
/framework-learn                          # 列所有歸檔 brief 含未處理 _suggestions
/framework-learn <brief_id>               # 補處理指定 brief 的 _suggestions（走 learning loop Step 2-5）
/framework-learn add-lesson <text>        # ad-hoc 加 lesson（不依附 brief）
/framework-learn add-pattern <text>       # ad-hoc 加 pattern（不依附 brief）
/framework-learn add-lesson --interactive # 對話式收集 lesson 內容
```

## 行為

### 模式 A：列未處理 brief（無參數）

```
1. Glob .framework/briefs/_archive/**/_tree.yaml
2. 對每個 tree.yaml 解析 suggestions 區塊（或 _suggestions.json 若有）
3. 對比 .framework/memory/lessons/ + patterns/，判斷哪些 suggest_* 已落地（用 source_brief 比對）
4. 列出含未落地 suggest_* 的 brief：

   未處理的 suggest_* 來源：
   ╭───────────────────────────────┬──────┬──────────╮
   │ brief_id                      │ 類別 │ 條目數   │
   ├───────────────────────────────┼──────┼──────────┤
   │ 2026-05-06-common-unittest    │ ⏳   │ 2 條     │
   │ 2026-04-22-cohort-analysis    │ ⏳   │ 1 條     │
   ╰───────────────────────────────┴──────┴──────────╯

   要補處理哪一個？或 all 處理全部？
```

### 模式 B：補處理指定 brief

```
1. Read .framework/briefs/_archive/{year-month}/{brief_id}/_suggestions.json 取彙整的 suggest_*
   （若 _suggestions.json 不存在，fallback Read _tree.yaml 看是否有 suggestions 區塊——
    某些早期 brief 把 suggestions 寫進 tree.yaml，相容處理）
2. 走 learning-loop §6-7：
   a. 顯示每條 suggest_* 給使用者
   b. 使用者答 y / n / edit / yes-all / quit
3. 對 y / edit 的條目，main 寫至：
   - lesson → .framework/memory/lessons/{category}.md（依 §8.1）
   - pattern → .framework/memory/patterns/{category}.md（依 §8.2）
   - codex → .framework/codex/{role}.md（依 §8.3）
   - skill → .claude/skills/{name}/SKILL.md（依 §8.4）
4. 寫完顯示摘要：「✓ 寫入 N 條，略過 M 條」
5. 在 _suggestions.json 內標記每條 processed_at: <ISO timestamp>（避免下次重 process）
```

### 模式 C：Ad-hoc add-lesson / add-pattern

```
/framework-learn add-lesson "Pytest 在 monorepo 子模組需 cd 後跑" --category code-review
```

行為：

```
1. 取 args：text, --category（必填）, --reference-brief（可選）
2. 顯示提議：
   「提議寫入 .framework/memory/lessons/code-review.md：
    'Pytest 在 monorepo 子模組需 cd 後跑'
    類別：code-review
    來源：使用者 ad-hoc（無關聯 brief）

    (y) 寫入  (edit) 修改文字  (n) 取消」
3. 使用者答 y → main append（依 learning-loop §8.1 schema）
4. Source 欄位：寫 'ad-hoc' 或使用者指定的 brief_id
```

`--interactive` 模式：對話式收集 text / category / 引用 brief（若有）等資訊。

## ad-hoc 條目格式（依 learning-loop.md §8.1 schema）

寫入時 append 至 `lessons/{cat}.md` 檔尾為 `## L{N}:` section（L 編號 = 檔內既有最大 L + 1，永不重編）：

```markdown
## L{N}: {一句標題}

**Source**: ad-hoc（{date}） 或 brief `{brief_id}`
**Status**: confirmed by user（{date}）
**Reference count**: 0
**Added via**: framework-learn-add-lesson

### 教訓

{body}
```

`Added via` 欄位（擴展，不在 §8.1 必備欄位）讓後續審視 memory 時可區分「brief learning loop 提議」vs「ad-hoc 直接加」。

## 異常處理

| 狀況 | 處理 |
|---|---|
| 找不到 brief_id | 顯示錯誤、列近期歸檔 brief |
| _tree.yaml 內無 suggestions 區塊 | 顯示「此 brief 無未處理 suggest_*，無需補」 |
| .framework/memory/lessons/{category}.md 達 30 條上限 | 同 learning-loop §8.1：提議淘汰最舊，使用者批准後執行 |
| Add-lesson text 過短 / 缺 category | 提示重輸入 |
| 使用者執行 add-lesson 但沒有 --category | 提示 + 列當前已有的 categories（從 ls .framework/memory/lessons/ 取） |

## 不做的事

- **不開新 brief**：本指令的存在意義就是避免開 brief
- **不繞過 user approval**：仍走 y/n/edit 流程
- **不修改 brief 歷史檔**（除了標記 suggestions[i].processed）
- **不影響 active brief**：可在 active brief 進行中執行（讀歸檔 brief 不影響當前）

## 與其他指令對比

| 指令 | 觸發時機 | 用途 |
|---|---|---|
| `/brief-new` | 想做正式工作 | 開 brief、走 Explore + Execute |
| Brief 結束時的 inline learning loop | brief 完成的最後 phase | 自動處理本 brief 的 _suggestions |
| `/framework-learn <brief_id>` | inline learning loop 漏跑 / 過去歸檔 brief 想補處理 | 補處理 |
| `/framework-learn add-lesson` | 想記一條跨 brief 的觀察 | Ad-hoc 加 memory，不開 brief |

## 相關文件

- `core/learning-loop.md`：完整學習迴圈（inline 版）
- `core/control-plane.md § 1.2`：「不直寫 memory」的精確意涵
- `commands/brief-new.md`：開新 brief（不是 learning 的入口）

## 相關指令

- `/framework-status` — 看 active brief 與 framework 狀態
- `/brief-status all` — 看歸檔 brief 列表
