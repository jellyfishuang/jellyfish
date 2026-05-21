# Learning Loop — Brief 完成時的學習迴圈

> 本文件規範 brief 完成時 main session 收集 feedback、產出 memory 條目的流程。
>
> 對應 design-summary 第 12 節（學習迴圈）+ 第 9b 題決議 + 8d 題使用者擴充。

---

## 1. 設計原則

1. **使用者批准制**：所有 memory / codex / skill 寫入需使用者明示批准
2. **品質評分驅動**：依使用者對 brief 結果的滿意度產出對應條目
3. **Producer 不直寫**：透過 verdict suggest_* 欄位提議
4. **Sessions 自動寫**：歷史紀錄無批准門檻
5. **Codex 增修要審慎**：領域知識若寫錯影響大，需 high confidence 才寫

---

## 2. 觸發時機

Brief 完成（L0 holistic review pass）→ main 進入學習迴圈。

不觸發的情境：
- Brief 取消（`/brief-cancel`）→ 不跑學習迴圈，只寫 sessions 簡短紀錄
- Brief 失敗（4 輪上限）→ 跑「失敗版」學習迴圈（強制 lessons + escalations）
- Brief 強制 unlock（`/framework-unlock`）→ 不跑

---

## 3. 五步流程

```
[Brief 完成或失敗]
  ↓
Step 1. Main 自動寫 .framework/memory/sessions/{brief_id}.md（無需批准）
  ↓
Step 2. 詢問使用者品質評分（單題）
  ↓
Step 3. 彙整 verdict suggest_* 欄位 + 評分產出提議
  ↓
Step 4. 使用者批准
  ↓
Step 5. Main 寫 memory / codex / skill（依批准結果）
  ↓
歸檔 + 解鎖 _active.yaml
```

### 3.1 強制執行規則（不可省略）

| 步驟 | 是否可省 | 條件 |
|---|---|---|
| Step 1（寫 sessions） | **絕不可省** | 即使所有 verdict 都 pass、無 suggest_*、無使用者反饋——sessions 仍必寫。是歷史紀錄，不是反饋產物。|
| Step 2（品質評分） | 可省 | 使用者明示跳過；或 brief failed / cancelled 走特殊版（§9-10）|
| Step 3（彙整提議） | 可省 | 若 _suggestions.json 為空 + 評分跳過 → 此步無動作 |
| Step 4-5（批准 + 寫入） | 可省 | 若 Step 3 無提議則跳過；有提議但使用者全拒也跳過 |
| 歸檔 + 解鎖 | **絕不可省** | 是 brief 生命週期的物理結束 |

**核心錯誤模式（必避免）**：
- ❌ 「Verdict 都 pass，沒什麼好寫，跳過 sessions」→ **錯**。Sessions 是歷史紀錄，不是品質評分的產物
- ❌ 「Pipeline 簡單（如 planning_only），跳過 learning loop」→ **錯**。任何 brief 都跑此流程
- ❌ 「使用者沒問就不問品質評分」→ Step 2 main 必主動詢問（即使是「⭐/⚠️/❌/跳過」一行選項）
- ❌ 「歸檔前才發現 sessions 沒寫」→ Step 1 必在歸檔前完成；歸檔是 Step 5 之後

---

## 4. Step 1. 自動寫 sessions

`.framework/memory/sessions/{brief_id}.md`：

```yaml
---
id: 2026-05-06-slot-revenue-q2
created_at: 2026-05-06T12:30:00
brief_started_at: 2026-05-06T10:00:00
brief_completed_at: 2026-05-06T12:30:00
duration: 2h 30m
recipe: data-analytics
roster: [data-analyst, analysis-reviewer, writer]
state: done                            # done | failed | cancelled
sub_briefs: [a, b]
clarification_rounds_used: 7
explore_rounds: 1
total_review_rounds: 5
total_artifacts: 4
archived_to: ./_archive/2026-05/2026-05-06-slot-revenue-q2/
---

# Session: 2026-05-06-slot-revenue-q2

## 摘要

（main 自動產出 1-2 段話：做了什麼、產出在哪、結論是什麼）

## 關鍵時間軸

- 10:00 brief 建立
- 10:08 Explore 完成（7 題訪談）
- 10:12 Plan 批准
- 10:15 開始 Execute（2 sub-briefs 並行）
- 11:30 sub-brief .a done
- 11:50 sub-brief .b done
- 12:10 L0 holistic review pass
- 12:30 完成、歸檔

## 產出

- .framework/briefs/_archive/.../sub-briefs/a/final.md
- .framework/briefs/_archive/.../sub-briefs/b/final.md

## 評分（待 Step 2 填）

- 待使用者評分
```

寫完後 Step 2 立即跑。

---

## 5. Step 2. 品質評分

```
Brief 已完成。請評分本次結果：

  ⭐ 滿意（流程順暢、產出符合預期、值得記為 pattern）
  ⚠️ 還行（有缺點但可接受，sessions 記錄即可）
  ❌ 不行（有錯需糾正，記為 lesson）
  📝 不評分跳過（仍歸檔但不產 memory 條目）

可選追加：自由評論（會記入 sessions.md）
```

收答案後寫 sessions.md 的「評分」段。

---

## 6. Step 3. 彙整提議

### 6.1 從 brief 內 `_suggestions.json` 收集

Brief 進行中各 verdict 的 `suggest_*` 欄位都已彙整在 `.framework/briefs/{brief_id}/_suggestions.json`：

```json
{
  "suggest_lesson": [
    {
      "from_verdict": "code-reviewer.verdict-1.json",
      "category": "code-review",
      "body": "Pytest 在 monorepo 子模組需 cd 後才能跑",
      "rationale": "..."
    }
  ],
  "suggest_pattern": [...],
  "suggest_codex": [...],
  "suggest_skill": [...]
}
```

### 6.2 依評分過濾

| 評分 | 處理 |
|---|---|
| ⭐ 滿意 | 顯示所有 suggest_pattern 候選 + suggest_codex 候選；suggest_lesson 不主動顯示但若有 escalations 則顯示 |
| ⚠️ 還行 | 不顯示 suggest_pattern；顯示 suggest_codex、suggest_lesson |
| ❌ 不行 | 強制顯示 suggest_lesson + 寫 escalation；不顯示 suggest_pattern |
| 📝 跳過 | 不顯示任何提議，直接歸檔 |

### 6.3 Main 的補充提議

除了 verdict 的 suggest_*，main 自己也可補：

- 若 escalations 目錄非空 → 強制提 lesson（從 escalation 內容生成）
- 若 brief 訪談題數 ≥ 15 但結果好 → 提 pattern「此類 brief 需高訪談量但可成功」
- 若 sub-brief 切分模式重複出現 → 提 pattern

---

## 7. Step 4. 使用者批准

對每個提議顯示：

```
🆕 提議寫入 lessons/code-review/{filename}.md：

「Pytest 在 monorepo 子模組需 cd 後才能跑，否則 collect error」

來源：本次 code-reviewer Round 1 因從 root 跑 pytest 誤判
類別：code-review

(y) 寫入 local
(n) 略過
(edit) 我先改一下文字再寫入
(m) 寫 local + 升流外部 KB    ← 僅當 .initialized knowledge_base.promote=true 時顯示
```

使用者可：
- y / n 對每項
- edit 改文字後寫入
- 一次 yes-all（接受所有提議）
- **m（升流外部 KB，僅 knowledge_base.promote=true）**：lessons / patterns / preferences 適用。main 依「跨 repo 可攜」準則預推薦——不綁本 repo 檔名/service/函式、換 repo/語言仍成立、是會重現的坑或方法論 → 標建議升流；綁死本 repo 具體程式碼的只給 y。`preferences` 預設推 m。選 m → main 蒸餾改寫後寫入 KB（見 §8.5），預覽可 edit

對 codex 提議特別嚴格：

```
🆕 提議更新 codex/data-analyst.md，新增知識點：

  Section: 1. 領域知識點
  Title: win_rate vs payout_rate 區分

  Body:
  win_rate = 勝場 / 總場；payout_rate = 派彩金額 / 投注金額。
  分析 revenue 時用 payout_rate。

  Source: 本次 brief 透過比對歷史報告確認
  Confidence: high

(y) 寫入（confidence: high）
(n) 略過
(edit) 我改 confidence 或 body
(low) 寫入但降為 confidence: low（後續驗證再升級）
```

---

## 8. Step 5. 寫入

依使用者批准結果：

### 8.1 寫 lessons

**檔案結構**：每 category 一檔（`lessons/{category}.md`）。**整檔一個 frontmatter**（追蹤檔級 metadata），body 為 bullet list（每條 lesson 一個 bullet，附 inline metadata）。

```
1. 開啟 .framework/memory/lessons/{category}.md
2. 若檔不存在 → 建檔，寫初始 frontmatter：
   ```yaml
   ---
   category: {cat}
   created_at: {ISO}
   last_updated: {ISO}
   entry_count: 0
   ---
   # Lessons: {cat}
   ```
3. 檢查現有條目數，若 ≥ 30：
   - 提示使用者：「lessons/{category}.md 已 30 條（上限）。要淘汰最久未引用的嗎？」
   - 同意 → 找 reference_count 最低 + last_referenced 最早 → 移至 lessons/escalations/（封存）
4. Append 新 bullet 至檔尾（不重寫 frontmatter，僅更新 last_updated / entry_count）：
   ```
   - [{date}] [id:lesson-{date}-{seq}] {body}
     - source_brief: {brief_id}
     - last_referenced: {date}
     - reference_count: 0
     - 詳見：escalations/{file}.md（若有）
   ```
5. 同 lesson 重複觸發 ≥ 3 次 → main 提議升級為 preferences.md 硬規則
```

**為何不用「每條 frontmatter」**：yaml + markdown 慣例下單檔多 frontmatter 不合法；inline bullet metadata 既可被 grep 也可被 SLIDERS 後期 import 工具掃進 SQLite（每行一個 entry）。

### 8.2 寫 patterns

```
1. .framework/memory/patterns/{category}.md
2. 上限 30 條（同 lessons 規則）
3. 條目 ≤ 3 行
4. Frontmatter 同 lessons
```

### 8.3 寫 codex

```
1. .framework/codex/{role}.md
2. 找對應 section（依 suggest_codex.section）
3. Append knowledge point + provenance blockquote：
   ```
   ### {title}
   - 含義：{body}

   > Source: {brief_id} / Confirmed: yes / Confidence: {high|low}
   ```
4. 更新 frontmatter：
   - version: bump（patch level）
   - last_updated: today
   - last_updated_by: {brief_id}
5. 變更紀錄章節 append 一行
```

### 8.4 寫 skill

```
1. 建立 .claude/skills/{skill_name}/SKILL.md
2. 從 suggest_skill.draft_body 寫
3. Frontmatter 必填：name / description / scope / version (1.0.0)
4. 顯示給使用者最終路徑，提醒可後續編輯
```

### 8.5 升流外部知識庫（promote，僅 knowledge_base.promote=true）

對 Step 4 選 `(m)` 的 `lessons / patterns / preferences`，main 寫完 local 後額外升流至 `.framework/.initialized` 的 `knowledge_base.path` 指向的外部 KB：

```
1. 讀 .initialized 取 knowledge_base；不存在或 promote != true → 跳過整個升流
2. 蒸餾改寫：剝掉 repo-specific 識別碼（檔名 / service / 函式 / 行號），
   留「通則 + backstory」。backstory 保留出處（source_brief + repo）
3. 去重（沿用該 KB 自身的寫入 / ingest 慣例）：
   - 已有等義條目 → 不重複寫，必要時補 backstory / 連結
   - 與既有矛盾 → callout 標記，不靜默覆蓋
4. 落點依**該 KB 自身的 schema 與寫入慣例**（讀 `knowledge_base.path` 下的 schema 說明，如其 CLAUDE.md / 模板）：
   分類標籤、聚合方式、frontmatter 欄位都由該 KB 定義，框架不假設特定結構
5. 更新 KB 對應索引 + append KB log（沿用該 KB 自身的寫入後慣例）
```

鐵律：
- **只升流 `lessons / patterns / preferences`**；`sessions` / `codex` / `skill` 不升流
- **local 永遠保留**：升流是 promotion 不是搬移——role 跑 brief 讀的仍是 local

---

## 9. 失敗版學習迴圈（brief failed）

```
1. Step 1 一樣寫 sessions（標 state: failed）
2. Step 2 跳過評分（已是失敗）
3. Step 3 強制顯示 escalations 對應的 lesson 提議
4. Step 4 強烈鼓勵批准（避免下次重蹈）
5. Step 5 寫入
6. Mirror brief 內 `_escalations/*.md` 摘要至 `.framework/memory/lessons/escalations/{root_id}-{sub_id}-{stage}.md`（永久紀錄；見 escalation-rules.md §1 lifecycle）
```

---

## 10. 取消版（brief cancelled）

```
1. 寫簡短 sessions（state: cancelled, 標取消原因）
2. 不跑 Step 2-5
```

---

## 11. 鐵律

### 11.1 Sessions 永遠寫
即使取消、失敗、跳過評分，sessions 都寫（歷史紀錄不省略）。

### 11.2 lessons / patterns / codex / skill 必批准
不批准就不寫。即使 main 強烈推薦，使用者拒絕就不寫。

### 11.3 不刪不修既有條目（除非顯式淘汰）
Append-only。淘汰是顯式 review，不能 main 自決悄悄改。

### 11.4 Provenance 必填
每個寫入的條目都有 source_brief / created_at（frontmatter）+ 對 codex 還有 Confirmed / Confidence。

### 11.5 外部知識庫（KB sink）：預設解耦、可 opt-in 升流
學習迴圈**預設只寫 local `.framework/memory`**，不依賴任何外部 KB——沒接 KB 的 repo 行為不變。

若 repo 在 `.framework/.initialized` 宣告 `knowledge_base` block：
- `promote: true` → brief 收尾經 Step 4 `(m)` 批准的 `lessons / patterns / preferences` 蒸餾升流至 KB（見 §8.5）
- `recall: true` → 使用者可 `/framework-recall` 唯讀查 KB 參考其他 repo（見 commands/framework-recall.md）

解耦不變式仍在：① 不自動倒（升流必經 Step 4 `(m)` 批准）② 不硬依賴（沒 KB 也自給自足）。KB 的手動寫入由該 KB 自己的入口處理（與框架無關）。

---

## 12. 給接手 agent 的提醒

- **學習迴圈是 brief 結束的最後一步**：寫完才解 _active.yaml lock
- **使用者疲勞時可全 yes-all**：但不要替使用者自決
- **Codex 寫入要慎重**：confidence 影響後續 brief；low 是好的預設
- **Patterns 30 條上限是經驗值**：超過後查找成本與益處不成比例
- **Lessons 升級為 preferences 是高槓桿**：減少未來 brief 重複糾正同事
- **Skill 寫入頻率應低**：skill 是穩定方法論，每 brief 都寫 skill 代表方法論不穩
- **❌ 永遠不需另開 brief 寫 memory**：常見誤讀是「main 不直寫 memory → 需要 planner agent 評估 → 開新 brief」。**這是錯的**。鐵律意思是「main 必走 user approval flow」，不是「main 不能寫」。User approval 在 inline learning loop（Step 4）內進行，main 直接寫；錯過了用 `/framework-learn` 補。**禁止建議使用者開新 brief 寫 memory**，會讓 brief 數量爆炸
- **「主 agent 把這條規則套到 mid-execution 的觀察」是常見偏離**：mid-execution 偵測到該記 lesson → 不要當下寫，**也不要主動建議開新 brief**。把它放進 verdict 的 `suggest_lesson` 欄位（聚合到 `_suggestions.json`），brief 結束時 inline learning loop 統一處理

---

## 13. 相關文件

- `core/control-plane.md`：Step G 學習迴圈在主流程位置
- `core/typed-interfaces.md`：suggest_* 欄位 schema
- `core/escalation-rules.md`：失敗版迴圈與 escalations 寫入
- `commands/brief-cancel.md`：取消的學習迴圈差異
