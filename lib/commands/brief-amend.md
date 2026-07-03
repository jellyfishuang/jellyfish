---
name: brief-amend
description: 對已 done 的 sub-brief 做小範圍修訂（無 reviewer、使用者目視審查）
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task
---

# /brief-amend

對已完成（state=done）的 sub-brief 做輕量修訂。介於「打回 Explore 重 plan」與「重開新 brief」之間的入口。

完整規範見 `.framework/lib/core/amendment.md`。

## 用法

```
/brief-amend <sub_id> "<一句話描述>"
```

範例：
```
/brief-amend a "把 fetchUser 改名 getUserById，並修正 readme 的 callsite"
/brief-amend b "errorMessage 加上 errno 欄位"
```

`<sub_id>` 為 sub-brief 的單字母 id（a, b, c...），不需要前綴 `{root_id}.`。

## 前置條件檢查

依序檢查（任一失敗 → 顯示原因 + 建議替代）：

| # | 檢查 | 失敗時提示 |
|---|---|---|
| 1 | `.framework/.initialized` 存在 | 「Framework 未初始化，先跑 `/framework-init`」 |
| 2 | `.framework/briefs/_active.yaml` 存在 | 「目前無 active brief，無法 amendment。`/brief-new` 開新 brief」 |
| 3 | `.framework/briefs/{root}/sub-briefs/{sub_id}/` 存在 | 「找不到 sub-brief `{sub_id}`。當前 brief 的 sub-brief 列表：[...]」 |
| 4 | `_tree.yaml.nodes.{sub_id}.state == done` | 「sub-brief `{sub_id}` 目前 state={state}，僅 done 的 sub-brief 可 amendment」 |
| 5 | Brief 尚未進入歸檔（`.framework/briefs/{root}/` 仍在原位、控制面未進 Step H） | 「Brief 已歸檔。請用 `/brief-reopen` 重啟（Phase B 才實作）或 `/brief-new` 開新 brief」 |
| 6 | Sub-brief.roster 含至少一個 producer-type role | 「sub-brief `{sub_id}` roster 內無 producer role；amendment 不適用，請 `/brief-cancel` 後改開新 brief」 |
| 7 | Amendment 次數 | 無上限；見下方「次數軟提醒」 |

### 次數軟提醒

amendment **不設次數上限、不強制拒**（信任使用者，amendment.md §1.3）。讀 `_tree.yaml.nodes.{sub_id}.amendments[]` 的非 cancelled 條目數：

```
0-1 次（即將成為第 1-2 次）→ 直接進 Step 1，靜默
≥ 2 次（即將成為第 3 次起）→ 先顯示軟提醒，然後直接進 Step 1（不阻擋、無 y/N 門檻）：

   ℹ️ 此 sub-brief 已進行 {n} 次 amendment。
   連續多次 amendment 有時代表原 plan 規格可再調整；
   若改動已偏大，可考慮 /brief-cancel 重開或於下個 brief 改 plan。
   （此為提醒，不阻擋——繼續進行 amendment。）
```

註：守門改靠「範圍 / 性質」（amendment.md §1.2：架構決策 / 跨模組 / 新依賴 / 新訪談 / 範圍過大 → 仍應中止改走 plan），不靠次數。

## 對話流程

### Step 0. Main 讀 context（無對話）

```
1. Read .framework/briefs/{root}/sub-briefs/{sub_id}/plan.md
2. Read .framework/briefs/{root}/sub-briefs/{sub_id}/final.md
3. ls .framework/briefs/{root}/sub-briefs/{sub_id}/amendments/
4. 計算下一個 amendment id：a1 / a2 / a3...（依現有目錄推算，含 cancelled / rejected 仍佔號）
5. 找主要 producer role：
   - Read sub-brief plan.md 取 pipeline.stages 最末項的 role
   - 確認該 role 仍在 _tree.yaml.nodes.{sub_id}.roster 內
   - 找不到 → 對應前置條件 #6 失敗、拒絕 amendment
```

### Step 1. 短訪談（cap 3 題）

依 `core/clarification.md` 單題制（推薦 + trade-off + options）。題數上限 3，**不反詰**。

訪談重點順序：
1. **範圍是否需擴張 `allowed_paths`？**
   ```
   原 plan.allowed_paths：
     - src/api/user.ts
     - src/api/user.test.ts

   你的描述提到要改 README.md，這超出原範圍。
   要把以下加進 amendment 範圍嗎？
     + README.md

   (y / 列其他要加的檔 / 不擴張、改撤回需求中跨範圍部分)
   ```
2. **是否追加驗收條件？**（可選，使用者自由文字）
3. **不可推導的關鍵決策**（命名 / 行為差異，依需求需要才問）

若使用者觸發指令時描述已充分（main 判斷無不確定點）→ **0 題直接過**。

訪談紀錄寫至 `amendments/{a_id}/clarifications.md`。0 題情況下**不寫**此檔。

### Step 2. 寫 amendment.md + 使用者複誦

```
1. 建目錄：.framework/briefs/{root}/sub-briefs/{sub_id}/amendments/{a_id}/
2. 寫 amendments/{a_id}/amendment.md（見 amendment.md §3 Step 3 schema）
3. 更新 _tree.yaml：
   nodes.{sub_id}.amendments[] append:
     - id: {a_id}
       state: amending
       summary: "{一句話}"
       allowed_paths_delta: [...]
       created_at: {now}
       completed_at: null
4. 更新 root.last_updated
5. 寫 _manifest.md append：
   "[{time}] amendment {a_id} 開始：{一句話}"
6. 顯示給使用者複誦：

   請確認以下 amendment 內容：

     變更：{一句話描述}
     擴張路徑：
       + README.md
     追加驗收：
       - grep 'fetchUser' 結果為空

   確認動工？(y / edit / cancel)

7. 使用者選擇：
   - y → 進 Step 3
   - edit → 回 Step 1 補訪談（amendment.md 重寫）
   - cancel → state=cancelled、寫 outcome.md → 中止
```

### Step 3. Spawn 主要 producer

```
1. 取 Step 0 找到的主要 producer role
2. 組 spawn prompt（依 control-plane.md §6.1）：
   - actor.spec_id: {root}.{sub}#{a_id}（amendment 專用 spec_id 格式，見 amendment.md §3.0）
   - mode: amendment
   - round: 1
   - 你的 input：
     - sub-brief plan: ./plan.md
     - sub-brief final: ./final.md
     - amendment 規格: ./amendments/{a_id}/amendment.md
     - allowed_paths: plan.allowed_paths ∪ amendment.allowed_paths_delta
   - 注意：本流程無 reviewer，使用者親自審。請聚焦在 amendment.md 描述的小範圍變更
3. spawn producer
4. 等回 verdict
```

### Step 4. 處理 verdict

依 `core/amendment.md` §4 表格：

| Verdict | 處理 |
|---|---|
| `pass` | append amendment 章節到 sub-brief `final.md` → state=done → 通知使用者 |
| `partial` | 顯示 partial_completed / partial_missing → 問使用者「接受 / 再 amend / cancel」 |
| `ambiguity`（第 1 次） | 顯示問題 → 使用者文字回答 → append 至 amendment.md → 重 spawn 同 producer round 2 |
| `ambiguity`（第 2 次） | 直接 reject、state=rejected |
| `needs_decomposition` / `needs_dependency` / `tool_error` | 直接 reject、state=rejected |
| `fail` | producer 不應自報 fail；視為 tool_error 處理 |

每個終態都寫 `amendments/{a_id}/outcome.md`（schema 見 amendment.md §5.2）。

### Step 4a. Pass 後通知

```
✓ Amendment {a_id} 完成。

變更檔案：
  - src/api/user.ts
  - README.md

詳情：.framework/briefs/{root}/sub-briefs/{sub_id}/amendments/{a_id}/

請目視 review 變更內容。如需再修改：
  - 再 amendment：/brief-amend {sub_id} "..."（已用 {n} 次；無上限，第 3 次起會有軟提醒）
  - 取消整個 brief：/brief-cancel
  - 接受並繼續：（無動作，可繼續 review 其他 sub-brief 或等 brief 歸檔）
```

### Step 4b. Reject 後通知

```
✗ Amendment {a_id} 拒絕。

原因：{verdict 類型 + 一句話}

建議：
  - {對應 verdict 的建議下一步，例「改開新 brief」「修工具後重試」}

詳情：.framework/briefs/{root}/sub-briefs/{sub_id}/amendments/{a_id}/outcome.md
```

## 異常

| 狀況 | 處理 |
|---|---|
| Sub-brief roster 內無 producer-type role | 前置條件 #6 失敗、拒絕 amendment（見上方表格） |
| Producer spawn 失敗（Task 錯誤） | state=rejected、outcome.md 記 tool_error，建議使用者重試 |
| Producer 寫超出 allowed_paths | 視為 tool_error、state=rejected、明示違規路徑清單 |
| Verdict JSON 解析失敗 | 比照 control-plane §6.3 retry 1 次；仍失敗 → tool_error |
| 使用者在 Step 1 訪談中改變需求方向（範圍變大） | 提示「範圍超出 amendment 適用，建議 /brief-cancel 改開新 brief」並中止 |
| 使用者連續多次 ambiguity 答覆模糊 | 第 2 次 ambiguity 強制 reject（依 amendment.md §4.1） |

## 不做的事

- **不 spawn reviewer**：amendment 層的核心設計
- **不重跑 L0 holistic review**：amendment pass 不觸發
- **不寫學習迴圈**（lessons / patterns / sessions）
- **不 merge worktree**（沿用 sub-brief 的 worktree，等 brief Step H 歸檔時統一）
- **不允許在 amendment 中拆 sub-brief**（needs_decomposition 直接 reject）

## 與其他指令搭配

| 場景 | 指令 |
|---|---|
| 看當前 brief 各 sub-brief 的 amendment 狀態 | `/brief-status` |
| Amendment 後決定取消整個 brief | `/brief-cancel` |
| Amendment 範圍超載、想重 plan | `/brief-cancel` + `/brief-new` |
| 想看 amendment 詳情 | 直接 Read `.framework/briefs/{root}/sub-briefs/{sub_id}/amendments/` |

## 相關文件

- `.framework/lib/core/amendment.md`：完整 amendment 規範（**必讀**）
- `.framework/lib/core/control-plane.md`：spawn producer 細節
- `.framework/lib/core/e2r-tree.md`：amendments 欄位於 `_tree.yaml` schema
- `.framework/lib/core/clarification.md`：訪談規則
- `.framework/lib/core/typed-interfaces.md`：verdict schema
