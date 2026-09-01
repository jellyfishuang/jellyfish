> 本文件規範 brief 的 **amendment（修訂）層**——介於 plan-execute 與重開新 brief 之間的輕量入口。
>
> 場景：sub-brief 已通過 stage / L0 holistic review，使用者進入目視 code review 階段，發現小範圍規格調整或 coding style 建議。直接打回 Explore 重跑成本太高、開新 brief 又破壞追蹤性，因此引入 amendment 層。
>
> 與 sub-brief 的差別：**無 reviewer**、**無 review loop**、**單次 producer 動作**（最多續答 1 次共 2 次）。使用者本身就是 reviewer。

---

## 1. 設計原則

### 1.1 信任使用者作為 reviewer

Amendment 層的核心假設：使用者已親自看過 sub-brief 產出，發現的問題範圍小、容易目視辨識。在這個前提下，再 spawn 一個 reviewer 機械審核反而是雜訊。

因此 amendment 流程**不 spawn reviewer**：producer 改完即交付使用者目視審查。Producer 在 amendment 場景不應自報 `fail`（無 reviewer 提供 fail 的 evidence）；若收到失敗類 verdict（`tool_error` / `needs_decomposition` / `needs_dependency` / 二次 `ambiguity`）則 amendment 視為 rejected，詳見 §4。

### 1.2 範圍極小，不重新 Explore

Amendment 適用情境：
- 規格小調整（rename、欄位順序、訊息文案、log level）
- Coding style 建議（命名、注釋、抽函式）
- 小 bug fix（off-by-one、邊界條件）

**不適用**：
- 涉及架構決策、跨模組改動、新依賴
- 需要新訪談才能釐清需求
- 範圍預估超過原 sub-brief plan.allowed_paths 太多（例：擴張 ≥ 5 個檔）

不適用的場景應走 `/brief-cancel` + `/brief-new` 或回 Explore 改 plan。

### 1.3 Amendment 不設次數上限，第 3 次起軟提醒（不阻擋）

amendment 層信任使用者作為 reviewer（§1.1）——小範圍修訂該能連續進行，**不設硬性次數上限、不強制拒**。守門靠「範圍 / 性質」（§1.2 的不適用條件：架構決策、跨模組、新依賴、新訪談、範圍過大），而非「次數」。

但「連續多次 amendment」有時是「原 plan 不貼合需求」的訊號，故保留**軟提醒**：sub-brief 累積非 cancelled amendments 達 **3 次起**，每次 `/brief-amend` 觸發時 main 顯示一行提醒（**不阻擋、預設繼續**，無 y/N 門檻）：

```
ℹ️ 此 sub-brief 已進行 {n} 次 amendment。
連續多次 amendment 有時代表原 plan 規格可再調整；若改動已偏大，可考慮 /brief-cancel 重開或於下個 brief 改 plan。
（此為提醒，不阻擋——繼續進行 amendment。）
```

1-2 次靜默直接進 Step 1。軟提醒只提示、不需確認門檻、不拒絕；使用者自行判斷是否繼續或改走 plan。

---

## 2. 觸發與前置條件

### 2.1 觸發指令

```
/brief-amend <sub_id> "<一句話描述>"
```

範例：
```
/brief-amend a "把 fetchUser 改名 getUserById，並修正 readme 的 callsite"
```

### 2.2 前置條件

| 條件 | 檢查 |
|---|---|
| Framework 已 init | `.framework/.initialized` 存在 |
| 有 active brief | 目標 brief 的 lock `.framework/briefs/_active/{root}.yaml` 存在（多 lane 下 sub_id 以本 session 持有的 brief 解析，或用 `{root}.{sub_id}` 全稱指定） |
| 指定 sub-brief 存在 | `.framework/briefs/{root}/sub-briefs/{sub_id}/` 存在 |
| Sub-brief 已 done | `_tree.yaml.nodes.{sub_id}.state == done` |
| Brief 尚未歸檔 | `.framework/briefs/{root}/` 仍在原位（未移至 `_archive/`）且控制面尚未進入 Step H |
| Sub-brief 有可用 producer role | sub-brief.roster 內存在至少一個 `type: producer` 的 role |
| Amendment 次數 | 無上限；1-2 次靜默，第 3 次起每次顯示軟提醒（不阻擋，§1.3） |

任一條件不滿足 → 顯示具體原因並建議替代指令。

> **F2 之後 amend 的補跑義務（2026-07-09）**：若 `_tree.yaml.brief_stages.local_test.state == pass`
> 且 amendment 改動觸及 code → 該 local_test 結果失效，main 必提示並對受影響的 [runtime] 項重跑
> local_test（可縮範圍），重跑 pass 才可進 Step H（control-plane §3 Step F'）。

---

## 3. 流程：四步走完

### 3.0 spec_id 約定

Amendment 的 verdict / suggest_* 彙整需要可辨識的 spec_id。約定格式：

```
{root_id}.{sub_letter}#{a_id}
```

範例：`2026-05-06-feature-x.a#a1`、`2026-05-06-feature-x.b#a2`

`#` 之後的 `{a_id}` 段標示這是 amendment 流程，與 sub-brief 自身的 verdict（spec_id = `{root_id}.{sub_letter}`）區隔。Verdict 寫入時 actor.spec_id 用此格式；`_suggestions.json` 彙整時可依此辨識「來源是 amendment」（雖然 amendment 不寫學習 memory，但 spec_id 仍應正確以供日後追溯）。

### Step 1. Main 讀 context

```
1. Read .framework/briefs/{root}/sub-briefs/{sub_id}/plan.md（取得 allowed_paths、驗收條件）
2. Read .framework/briefs/{root}/sub-briefs/{sub_id}/final.md（取得 sub-brief 已完成內容摘要）
3. Read .framework/briefs/{root}/sub-briefs/{sub_id}/amendments/（檢查歷史 amendment 數量）
4. 計算下一個 amendment id：a1 / a2 / a3...
```

### Step 2. 短訪談（cap 3 題）

訪談規則：依 `core/clarification.md` 的單題制（推薦 + trade-off + options），但題數上限調整：

| 設定 | 值 |
|---|---|
| 題數上限 | 3 題 |
| 反詰輪數 | 0（不反詰；amendment 求快） |
| 跳過條件 | 使用者觸發指令時已附充分描述 → 0 題直接過 |

訪談重點：
1. 範圍是否需擴張 `allowed_paths`？若需，列出擴張的檔 / 目錄
2. 驗收條件是否需追加？（例：「rename 後 grep 不到舊名」）
3. 不可推導的關鍵決策（命名選擇 / 行為差異）

訪談產出寫入 `amendments/{a_id}/clarifications.md`（極簡，可僅 1-2 行）。**0 題情況**：使用者觸發指令時描述已充分、main 判斷無不確定點，跳過訪談並**不寫** `clarifications.md`（保持目錄乾淨）。

### Step 3. 寫 amendment.md + 使用者複誦確認

Main 整理需求成 amendment.md：

```markdown
# Amendment {a_id}: {一句話描述}

## 元資料

- amendment_id: a1
- sub_brief: {root}.{sub}
- created_at: {ISO timestamp}
- requested_by: user

## 變更需求

{使用者描述 + 訪談補充，純文字段落}

## 範圍

- 繼承 sub-brief plan.allowed_paths：[...]
- Allowed paths delta（本次擴張，可空）：
  - + src/utils/y.ts
  - + README.md

## 驗收條件（追加）

- {從訪談得出，例：「grep 'fetchUser' 結果為空」}
- 不破壞原 plan 既有驗收條件

## 不做的事

- {若有，例：「不重構函式內部邏輯」}
```

寫好後**向使用者複誦確認**：

```
請確認以下 amendment 內容：

  變更：{一句話描述}
  擴張路徑：{若有，逐一列}
  追加驗收：{若有}

確認動工？(y / edit / cancel)
```

- `y` → 進 Step 4
- `edit` → 回 Step 2 補訪談
- `cancel` → 中止 amendment（amendment 目錄保留為 `state: cancelled`）

### Step 4. Spawn 主要 producer → 結束

「主要 producer」= sub-brief 的 pipeline 最後一個 stage 對應的 producer role（dev-team 通常是 `engineer`、finance-advisory 通常是 `writer`、data-analytics 通常是 `data-analyst`）。

```
1. 找 producer role：
   - Read sub-brief plan.md 取 pipeline.stages 最末項的 role
   - 確認該 role 仍在 _tree.yaml.nodes.{sub_id}.roster 內
   - 找不到 → 拒絕 amendment（前置條件 §2.2 已預檢，此處為防禦性檢查）
2. 組 spawn prompt：
   - role: <主要 producer role>
   - actor.spec_id: {root}.{sub}#{a_id}（amendment 專用 spec_id 格式，見 §3.0）
   - input：
     - 原 plan.md
     - 原 final.md
     - amendment.md
     - 原 sub-brief 的 worktree（dev recipe）或對應 source 路徑
   - 模式旗標：mode: amendment（role md 可選擇是否依此調整行為，預設不調整）
   - allowed_paths = plan.allowed_paths ∪ amendment.allowed_paths_delta
3. 等 producer 回 verdict
4. 處理 verdict（見 §4）
```

---

## 4. Producer Verdict 處理

Amendment 層僅接受以下 verdict 走向：

| Verdict | 處理 |
|---|---|
| `pass` | Append amendment 章節到 sub-brief `final.md` → state=done → 通知使用者接手目視 review |
| `partial` | 保留 patch，state=`done_with_notes`，列 `partial_completed` / `partial_missing` 給使用者，由使用者決定接受 / 再 amend / cancel |
| `ambiguity` | **允許 1 次續答**（使用者直接回覆）→ main 把答覆 append 到 amendment.md → 重 spawn 同 producer round 2。第 2 次 ambiguity 直接 reject amendment |
| `needs_decomposition` | 直接拒絕：amendment 不允許拆分。state=rejected，建議使用者改開新 brief |
| `needs_dependency` | 直接拒絕：amendment 不允許新依賴。state=rejected，建議使用者改開新 brief |
| `tool_error` | state=rejected，記錄錯誤，建議使用者修工具後重試 |
| `fail` | **不適用**：amendment 層無 reviewer 提供 fail 的 evidence、producer 不應自報 fail。若收到 → 視為 tool_error 處理 |

### 4.1 「允許 1 次續答」流程

```
1. Main 顯示 producer 的 ambiguity 問題給使用者
2. 使用者回答（自由文字）
3. Main append 至 amendment.md 的「補充答覆」章節
4. Main 重 spawn 同 producer，prompt 包含原 amendment.md（含補充）+ 標註 round=2
5. Producer 回新 verdict：
   - pass / partial → 同 §4 表格處理
   - ambiguity 再次 → 直接 reject amendment，建議改 plan
```

**鐵律**：續答只允許 1 次。第 2 次 ambiguity 視為「需求本身不清楚」，amendment 層解決不了。

---

## 5. 檔案結構

```
.framework/briefs/{root_id}/sub-briefs/{sub_id}/
├── plan.md                       ← 不動
├── final.md                      ← amendment pass 後 append 章節
├── stages/...                    ← 不動
└── amendments/
    ├── a1/
    │   ├── amendment.md          ← spec + path delta（Step 3 產出）
    │   ├── clarifications.md     ← 訪談紀錄（Step 2 產出；0 題時不寫此檔）
    │   ├── {producer-role}.patch.md   ← producer verdict + 變更摘要（檔名隨 role，例 engineer.patch.md / writer.patch.md）
    │   └── outcome.md            ← 一句話結論：done / done_with_notes / rejected / cancelled
    ├── a2/
    │   └── ...
    └── a3/
        └── ...
```

### 5.1 `amendment.md` schema

見 §3 Step 3 範本。必備欄位：
- 元資料：`amendment_id`, `sub_brief`, `created_at`, `requested_by`
- 變更需求（自由文字段落）
- 範圍（allowed_paths_delta，可空陣列）
- 驗收條件追加（可空陣列）
- 不做的事（可空）

### 5.2 `outcome.md` schema

```markdown
# Outcome: {a_id}

- state: done | done_with_notes | rejected | cancelled
- completed_at: {ISO timestamp}
- summary: {一句話}

## 變更摘要（pass / done_with_notes 才有）

{producer patch.md 摘要、檔案清單、git diff stats}

## 拒絕理由（rejected 才有）

{verdict 類型 + 一句話原因 + 建議下一步}
```

### 5.3 `final.md` 的 amendment 章節

Amendment pass 後，main append 以下章節到 sub-brief `final.md` 末尾：

```markdown
---

## Amendments

### a1 — {一句話描述}（{完成時間}）

**變更檔案**：
- src/foo.ts（rename fetchUser → getUserById）
- README.md（更新 callsite 範例）

**驗收**：grep 'fetchUser' 結果為空 ✓

詳見 `./amendments/a1/`。
```

每次 amendment pass 都 append 一個 `### a{n}` 區塊。

---

## 6. `_tree.yaml` 變動

Sub-brief 節點下新增 `amendments` 陣列（可空，初始 sub-brief 無此欄位）：

```yaml
nodes:
  2026-05-06-feature-x.a:
    state: done
    parent: 2026-05-06-feature-x
    children: []
    # ... 既有欄位 ...
    amendments:
      - id: a1
        state: done                    # amending | done | done_with_notes | rejected | cancelled
        summary: "rename fetchUser → getUserById"
        allowed_paths_delta:
          - src/utils/y.ts
          - README.md
        created_at: 2026-05-06T13:00:00
        completed_at: 2026-05-06T13:08:00
      - id: a2
        state: amending
        summary: "..."
        allowed_paths_delta: []
        created_at: 2026-05-06T14:00:00
        completed_at: null
```

### 6.1 Amendment state enum

| State | 描述 | 可進入的下一狀態 |
|---|---|---|
| `amending` | 訪談中 / 確認中 / producer 跑中 | done, done_with_notes, rejected, cancelled |
| `done` | producer pass、final.md 已 append | （終態） |
| `done_with_notes` | producer partial，使用者接受 | （終態。使用者若想再修，開新 a{n+1}） |
| `rejected` | producer 二次 ambiguity / needs_decomposition / needs_dependency / tool_error | （終態） |
| `cancelled` | 使用者於 Step 3 確認時選 cancel | （終態） |

### 6.2 寫入時機

| 時機 | 寫入內容 |
|---|---|
| `/brief-amend` 開始 Step 3 | append amendments[] 新項，state=amending |
| Engineer pass | state=done, completed_at |
| Engineer partial 且使用者接受 | state=done_with_notes, completed_at |
| Engineer 拒絕類 verdict | state=rejected, completed_at |
| Step 3 使用者選 cancel | state=cancelled, completed_at |

每次寫入後同步更新 root 的 `last_updated`。

---

## 7. 與其他流程的互動

### 7.1 與 L0 holistic review

Amendment **發生在 L0 holistic review pass 之後、brief 歸檔（Step H）之前**。

Amendment pass 不重跑 L0 holistic review（amendment 範圍小、信任使用者目視審）。若使用者擔心 amendment 影響跨 sub-brief 一致性 → 應走 `/brief-cancel` 後重開新 brief。

### 7.2 與學習迴圈

Amendment **不參與學習迴圈**：
- 不寫 `.framework/memory/sessions/`（sessions 仍綁原 brief 完成時觸發）
- 不寫 `.framework/memory/lessons/` / `patterns/`
- Amendment 紀錄留在 `amendments/{a_id}/outcome.md`，brief 歸檔時隨 brief 一起進 `_archive/`

理由：amendment 是「使用者親手把關」的微調，與「reviewer 機械發現」不同層次，混進 lessons 會稀釋訊號。

### 7.3 與 worktree（dev recipe）

若 sub-brief 使用 worktree，amendment 共用同一 worktree（不另開）：
- producer spawn 時 cwd = sub-brief 的 worktree
- amendment 完成後不立即 merge / remove worktree（等原 brief Step H 歸檔時統一處理）

### 7.4 與 `/brief-cancel`

`/brief-cancel` 取消整個 brief：所有 amendment（含 amending 中的）一併進歸檔。amending 中的 amendment 視為 cancelled。

### 7.5 與 `/brief-reopen`（Phase B）

歸檔 brief 重啟後，可繼續 `/brief-amend`。次數計算延續歸檔前的紀錄（即歸檔前已 N 次，重啟後仍從 N 起算軟提醒門檻，§1.3）。

---

## 8. 鐵律

### 8.1 無 reviewer
Amendment 層不 spawn 任何 reviewer。使用者本身就是 reviewer。任何試圖 spawn reviewer-type role 的行為都是設計錯誤。

### 8.2 單 producer 動作
Amendment 流程內最多 spawn 主要 producer 2 次（初始 + 1 次 ambiguity 續答）。超過 → 強制 reject、要求改開新 brief 或回 Explore。

### 8.3 不允許拆分
`needs_decomposition` 在 amendment 層直接 reject。amendment 預設範圍小，要拆代表不該走 amendment。

### 8.4 不允許新依賴
`needs_dependency` 在 amendment 層直接 reject。新依賴影響面廣，須走完整 plan 流程。

### 8.5 不設次數上限，第 3 次起軟提醒
amendment 不設硬性次數上限、不強制拒（信任使用者，§1.1）。累積 3 次起每次顯示軟提醒（不阻擋、無確認門檻）。守門改靠範圍 / 性質（§1.2），非次數。理由見 §1.3。

### 8.6 不參與學習迴圈
Amendment 不寫 lessons / patterns / sessions。原 brief 的學習迴圈仍正常跑（綁原 brief 完成時觸發）。

### 8.7 範圍邊界硬擋
Producer 寫超出 `plan.allowed_paths ∪ amendment.allowed_paths_delta` 的檔 → 視為 path boundary 違反、verdict 強制改 tool_error、amendment 拒絕。

### 8.8 不建立新 sub-brief
Amendment 不算 sub-brief，不進 `_tree.yaml.nodes` 作為獨立節點，只掛在所屬 sub-brief 節點的 `amendments[]` 陣列。

---

## 9. 給接手 agent 的提醒

- **Amendment 是「review 後的微調入口」，不是「快速通道」**：別讓使用者習慣把所有小改都丟 amendment 而跳過 plan
- **第 3 次起的軟提醒是必須的**：提醒（不阻擋）讓使用者意識到原 plan 可能有問題，但尊重使用者繼續小修的決定——不要把它變回硬性確認門檻或拒絕
- **producer mode flag 預設無作用**：role md 不需特別處理 `mode: amendment`，除非該 role 的設計者明確要區分
- **path boundary 在 amendment 層仍是硬限**：擴張要明示寫進 `allowed_paths_delta`、不可隱式
- **使用者目視 review 失敗的處置**：使用者讀完 patch 不滿意 → 沒有「打回」流程，使用者自行決定（再 amend / cancel / 改 plan）
- **不要試圖把 reviewer 加回來**：「加個 lint 機械審吧」的衝動很常見，但會破壞 amendment 層的核心定位（信任使用者）

---

## 10. 相關文件

- `core/control-plane.md`：main session 行為規範（amendment 入口在 §6）
- `core/e2r-tree.md`：`_tree.yaml` schema（amendments 欄位定義在 §2.2）
- `core/clarification.md`：訪談規則（amendment 用單題制 cap 3）
- `core/typed-interfaces.md`：producer verdict schema（amendment 用 spec_id `{root}.{sub}#{a_id}` 格式）
- `core/escalation-rules.md`：何時拒絕 amendment 強制走 plan
- `commands/brief-amend.md`：slash command 對話腳本
- `commands/brief-status.md`：amendment 狀態顯示
