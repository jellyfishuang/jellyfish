# Clarification — Grill-me 訪談規則

> 本文件規範 Explore Step 3 main session 對使用者的訪談行為，及 sub-brief 遇到 ambiguity 的處理。
>
> 對應 design-summary 第 6 題（Explore 階段）+ 第 6b 題（cap 20 題、sub-brief 不訪談）。

---

## 1. 設計原則

1. **單題制**：一次問一題，等使用者答後再問下一題
2. **每題格式固定**：問題 + 推薦 + 理由 + trade-off + options
3. **L0 cap 20 題**：root brief 訪談階段總題數上限
4. **單題上限 2 輪反詰**：使用者答得不清楚時，最多再追問 1 次
5. **使用者可說「你判斷」**：採 main 推薦並註明
6. **Sub-brief 不訪談使用者**：模糊就回 `ambiguity` verdict

---

## 2. 何時訪談

| 階段 | 訪談者 | 對象 |
|---|---|---|
| Explore Step 3（root brief） | main | 使用者 |
| Explore Step 4 plan-draft 後（若 planner 回 ambiguity） | main | 使用者 |
| Plan reviewer fail 第 2 輪後（review-loop §2.2 觸發回 Explore） | main | 使用者 |
| Sub-brief 內 ambiguity verdict | main 自行判斷 → 補資料 / 升級 L0 | 不直接訪談使用者 |

---

## 3. 訪談題目格式

每題顯示給使用者：

```
Q{n}: <問題本體>

我推薦：<main 的推薦答案>

理由：<為什麼推薦這個>

Trade-off：
  - 推薦選項：<優點 / 缺點>
  - 替代選項：<優點 / 缺點>

Options:
  (a) <選項 1>
  (b) <選項 2>
  (c) <選項 3>
  (d) 你判斷（採推薦）
  (其他) 請描述
```

**規範**：
- `<問題本體>` 必為單一決策點，不混多問題
- `<推薦答案>` 必填（使用者最常答「c」或「d」，沒推薦會卡）
- Options 至少 2 個（含 d）；超過 5 個 → 拆題
- 「其他」永遠可用，使用者可自由描述

---

## 4. 反詰邏輯（單題 2 輪上限）

### 4.1 第 1 輪

使用者答完 → main 解析。若答案：
- 明確（選 a/b/c/d 或具體描述）→ 接受 → 進下題
- 模糊（「看情況」「我也不知道」「都可以」）→ 進第 2 輪反詰

### 4.2 第 2 輪反詰

```
Q{n}-2: 我需要更明確的答案才能繼續。

你說「<使用者上輪答案>」。
這對 plan 的影響是：<具體影響說明>

請選：
  (a) <優先 option>
  (b) <次優 option>
  (d) 採我的推薦 <推薦 option>

或請給我具體描述。
```

### 4.3 第 2 輪仍模糊

採 main 推薦並註明於 `clarifications.md`：

```
Q{n}: <問題>
答：<使用者上輪答案>
追問：<反詰>
追問答：<使用者第 2 輪答案>
最終解讀：採 main 推薦 <推薦選項>，因使用者未明確答覆
```

---

## 5. Cap 20 題

### 5.1 計數規則

- 每題（含反詰）算 1 題（反詰不另計）
- L0 Explore Step 3 + Step 4 後再次訪談都算
- 若 Plan reviewer fail 第 2 輪後回 Explore 補訪談 → 累積（不重置）
- 同一個 brief（含其 explore re-do）總和不超過 20 題

### 5.2 接近上限提醒

- 達 15 題時：「已 grill 15 題，還剩 5 題上限。請我直接出 plan 還是繼續釐清？」
- 達 18 題時：強制提示「再 2 題後達上限，超出後 main 將以當下理解開工」
- 達 20 題：強制結束訪談 → main 進 Step 4 plan 草稿

### 5.3 達上限的處置

`clarifications.md` 結尾標：

```
## 未完全釐清項目（達 20 題上限）

- <項目 A>：<main 的當下解讀 + 不確定點>
- <項目 B>：<同上>

Main 將依以上解讀繼續，使用者可在 plan 批准前審視 plan.md 的「已知風險」章節。
```

---

## 6. Sub-brief Ambiguity 處理

Sub-brief 內 producer / reviewer 回 `ambiguity` verdict 時，**不直接訪談使用者**。Main 動作：

```
1. 讀 verdict.questions
2. 嘗試從現有資料補：
   a. Read intel-pack.md 找答案
   b. Read codex 找答案
   c. Read .framework/memory/lessons / patterns 找答案
   d. Glob/Grep repo 找答案
3. 若補到 → spawn 同 role 第 2 輪，附補充資訊
4. 若補不到（關鍵問題）→ 升級 L0：
   「Sub-brief X 因 <問題摘要> 無法繼續。
    需要訪談使用者補資訊。
    當前已用 grill 題數：{count}/20，剩 {20-count} 題。
    繼續訪談嗎？(y/n)」
   y → 進第 7 節 L0 補訪談
   n → 整個 sub-brief 標 failed，升級使用者
5. 若累積太多 ambiguity（同 sub-brief 內 ≥ 3 次）→ 強制升級不再嘗試
```

---

## 7. L0 補訪談（從 sub-brief 升級）

```
1. 讀 sub-brief 的 ambiguity verdicts，彙整為 L0 訪談題
2. 進入 Explore Step 3 訪談模式（顯示題目、收答、反詰）
3. 訪談題數計入 L0 cap 20
4. 訪談完 → 把答案寫進 clarifications.md（標「來自 sub-brief X 升級」）
5. spawn 同 sub-brief role 第 N 輪（rounds.producer 不算）
6. 若 sub-brief 仍 ambiguity → 跳到第 6 節步驟 5（強制升級）
```

---

## 8. Plan reviewer fail 後的 Explore 補訪談

review-loop §2.2 觸發回 Explore：

```
1. 顯示給使用者：
   「Stage X 連續 2 輪 review fail。
    失敗原因摘要：<reviewer 累積意見>
    建議：補訪談以修正 plan。
    剩餘 grill 題數：{20-count}
    要進入補訪談嗎？(y/n/cancel)」
2. y → 進入 Step 3 訪談模式（題目從 reviewer 意見生成）
3. n → 直接送回 planner 第 N 輪，不補訪談（風險：可能再 fail）
4. cancel → 整個 brief failed，升級
```

---

## 9. 訪談題目產生邏輯

Main 從以下來源生成題目：

| 來源 | 題目類型範例 |
|---|---|
| `intel-pack.md` 的「不確定點清單」 | 「Cohort 切法用註冊月份還是首儲月份？」 |
| Plan reviewer 的 fail evidence | 「Reviewer 認為 baseline 缺漏，要用上一季同期還是去年同期？」 |
| Sub-brief ambiguity 的 questions | 「Producer 問：要排除測試帳號嗎？」 |
| Codex 的「已知陷阱」對應的本次選項 | 「依 codex 此 repo 區分 win_rate vs payout_rate，本次用哪個？」 |

題目排序：
- BLOCKING severity 在前（不答無法繼續）
- non-blocking 在後（可推遲）

---

## 10. clarifications.md 寫作格式

```markdown
# Clarifications: {brief_id}

## Q1. <問題本體>
- 推薦答案：<...>
- 使用者答：<...>
- 解讀：<最終結論>

## Q2. ...

## 未完全釐清項目（若達 20 題上限）
- <項目>：<解讀 + 不確定點>

## 訪談總計
- L0 Step 3 第 1 次：N 題
- 從 sub-brief X 升級補：M 題
- Plan re-Explore 補：K 題
- 總計：N+M+K / 20
```

---

## 11. 鐵律

### 11.1 不一次問多題
即使連續 5 個關聯問題，main 也要單題提問、單題收答。例外：明確相關的選項組（如 a/b/c options）算同一題。

### 11.2 不省略推薦
即使 main 也不確定 → 推薦欄位填「我也不確定，傾向 X 因為...」。永不留白。

### 11.3 不跳過反詰機會
使用者第 1 輪答模糊 → 必反詰一次。直接套推薦會被使用者抱怨「我又沒明確說 yes」。

### 11.4 不超過 20 題
即使還沒釐清完 → 達上限強制結束。寧可帶風險開工讓 plan 顯示「已知風險」，也不要無限訪談。

### 11.5 Sub-brief 不訪談
Sub-brief 的 producer / reviewer 永遠不直接問使用者。Sub-brief ambiguity → main 處理。

### 11.6 「你判斷」要明確記錄
使用者答 d / 「你判斷」/ 「都可以」→ 在 clarifications.md 標註「採 main 推薦」，可追溯。

---

## 12. 給接手 agent 的提醒

- **訪談是 main 親自做**，不要 spawn 「interviewer role」
- **題目順序 = 影響順序**：blocking 題不答 plan 寫不出來，先問
- **Cap 20 是硬上限**：超過違反 framework 鐵律，使用者會被打斷工作節奏
- **反詰僅 1 次**：第 2 次模糊就採推薦並標註，不要無限糾纏
- **Sub-brief 升級必走 verdict**：不能 spawn 的 sub-brief 直接寫對話視窗（架構鐵律）
- **clarifications.md 是審查素材**：reviewer / 後續 brief 都會 Read，寫工整
