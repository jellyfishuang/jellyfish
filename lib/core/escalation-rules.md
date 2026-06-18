# Escalation Rules — 升級使用者的觸發條件

> 本文件規範哪些情境必須升級使用者（不論 sub-brief 階段如何）。Main session 偵測到觸發條件即停下並顯示給使用者決定。
>
> 對應 design-summary 第 8.5 節「高風險 sub-brief 強制升級」與多處 verdict 處理流程。

---

## 1. 升級的定義

**升級**（escalate）= main 暫停 brief 流程，把決策權交回使用者。觸發後：

1. Main 不繼續 spawn role
2. 顯示完整情境給使用者
3. 寫 `.framework/briefs/{root_id}/_escalations/{timestamp}-{reason}.md`（brief 進行中的即時紀錄）
4. 等使用者下指令（continue / cancel / 修改 / hold）

升級不等於失敗。失敗（state=failed）是 4 輪上限觸發後的終態，升級是中間狀態（使用者決定後可繼續）。

### Escalation 檔案 lifecycle（兩個位置各司其職）

| 階段 | 路徑 | 內容 | 寫入時機 |
|---|---|---|---|
| Brief 進行中 | `.framework/briefs/{root_id}/_escalations/{timestamp}-{reason}.md` | 即時詳細事件檔（含當下 verdict 累積、main 判斷、使用者決定） | 升級觸發當下 main 寫 |
| Brief 結束（learning loop） | `.framework/memory/lessons/escalations/{root_id}-{sub_id}-{stage}.md` | 經學習迴圈濃縮後的永久紀錄（給未來 brief 的 Explore Step 2 grep 參考） | learning-loop §9（失敗版迴圈）中 main 從 brief 內 `_escalations/` 摘要而成 |

兩者並存：brief 內檔是「事件現場」（隨 brief 歸檔到 `_archive/`），memory 內檔是「跨 brief 經驗」（永久可查）。

---

## 2. 強制升級的觸發條件

### 2.1 Verdict-driven（從 role / reviewer 來）

| Verdict | 觸發 | 升級因為 |
|---|---|---|
| `needs_dependency` | 任何 producer | 安裝依賴需使用者批准 |
| `tool_error` | 任何 reviewer | 工具壞了 framework 修不了 |
| `partial`（高比例 missing） | producer | 完成度 < 50% 通常代表計畫不對 |
| Schema 違規 retry 仍失敗 | main 偵測 | role 寫不出合法 verdict，可能 prompt 有問題 |

### 2.2 Round-driven（review-loop 觸發）

| 觸發 | 來自 |
|---|---|
| 單 stage cumulative reviewer fail ≥ 4 輪 | review-loop §3.2 |
| Plan reviewer fail ≥ 2 輪後使用者拒絕回 Explore | review-loop §2.2 |
| Explore 重做 ≥ 2 次仍 fail | review-loop §3.2 |
| L0 holistic review 連 2 次 fail | review-loop |
| Producer 同 stage retry ≥ 5 次仍非 pass | producer cap（無 pass 過） |

### 2.3 高風險動作（design-summary §8.5）

L1 sub-brief 進入 Execute 前，main 偵測 plan 內含以下動作 → 強制升級使用者批准：

| 高風險類別 | 偵測規則 |
|---|---|
| **動依賴** | plan 提到新增 / 升級 / 移除依賴；diff 預估會動 `pyproject.toml` / `package.json` / `go.mod` 等 |
| **動 schema** | plan 提到 DB migration / API 介面變動（含 breaking change）|
| **跨模組大改** | allowed_paths 跨 ≥3 個模組目錄 |
| **動 production 配置** | plan 提到改 `Dockerfile.production` / `.github/workflows/` / `deploy/` |
| **刪除大量檔案** | plan 預估刪除 ≥ 10 檔，或 ≥ 一整個模組 |
| **Force operation** | plan 明確要求 `git reset --hard` / `git push --force` 等 |
| **Trust mode == strict 下任何寫入** | strict mode 下每 sub-brief 啟動都升級確認 |

升級時顯示：

```
⚠️ 高風險動作確認

Sub-brief {sub_id} 計畫進入 Execute，但偵測到高風險動作：
  - {類別}: {具體說明}

詳情：
  - 計畫變動範圍：{summary}
  - 影響預估：{impact}
  - Trust mode: {mode}

是否同意此 sub-brief 進入 Execute？
  (y) 同意，進入 Execute
  (n) 拒絕，回 Explore 修改 plan
  (cancel) 取消整個 brief
```

### 2.4 Framework 偵測級

| 條件 | 觸發 |
|---|---|
| `_active.yaml` last_heartbeat > 1 hour 後 main 重啟 | batch-lock.md：殭屍恢復提示 |
| 同 sub-brief 累積 ≥ 3 次 ambiguity 升級 L0 | clarification.md §6 step 5 |
| Plan reviewer 寫的 plan 與舊 plan diff < 5% | review-loop：plan 重做沒實質變化警告 |
| Tree 結構與 _tree.yaml 不一致（手動改） | e2r-tree §6.5 |
| Brief 總執行時間 > 24 小時 | 提示「brief 拖太久，要不要 hold？」 |
| Sub-brief 試圖切 L2（違反 2 層限制） | e2r-tree §4.2：拒絕 + 升級 |
| Schema 違規 retry 仍違規 | typed-interfaces 範例 |
| Producer 連續 retry 仍 ambiguity / partial / decomposition | review-loop |
| **Adversarial-deadlock**：`rounds.adversarial >= 3` 且仍 fail | review-loop §3.2；觸發 escalation tag `adversarial-deadlock`，建議使用者改該 stage `second_review: false` 後 `/framework-recover` 接續 |

---

## 3. 升級顯示格式

統一格式 `_escalations/{timestamp}-{reason}.md`：

```markdown
# Escalation: {reason}

- brief_id: {...}
- sub_id: {...}（若 L1）
- stage: {...}（若 stage 內）
- timestamp: {ISO}
- trigger: {從第 2 節哪條觸發的}

## 情境

（1-2 段話描述發生什麼）

## 累積證據

- Verdict 1: {...}
- Verdict 2: {...}
- ...

## Main 的判斷

（為什麼這需要使用者決策；main 自己不能決定的理由）

## 選項

- (a) {option 1}
- (b) {option 2}
- (c) {option 3}

## 使用者決定（待填）

```

升級時 main 同時：
1. 寫此檔案
2. 顯示完整內容給使用者
3. 等使用者回覆

---

## 4. 使用者回覆格式

### 4.1 直接答字母

```
使用者：a
```

→ Main 執行 option (a)，更新 _escalations 檔加「使用者決定」段。

### 4.2 自由描述

```
使用者：我已經手動修了 X，請接續
```

→ Main 詢問需要什麼 follow-up 動作（例：是否要 re-spawn / 跳過 stage / 標完成）。

### 4.3 Hold

```
使用者：先 hold，我晚點看
```

→ _active.yaml.phase = on_hold；不繼續，但 lock 保持。使用者可隨時用 `/framework-recover` 接續。

---

## 5. 不升級的情境（main 自處理）

以下情境 main 自己處理，不顯示升級：

| 情境 | Main 動作 |
|---|---|
| Producer round 1 fail | spawn round 2（review-loop §2.1） |
| Sub-brief ambiguity 且能從 intel 補 | 自行補資料、re-spawn |
| Stage 完成、進下個 stage | 直接 spawn 下個 |
| L0 holistic review pass | 直接歸檔 |
| Verdict 寫入 / _tree 更新 | 直接寫 |

升級是 escape hatch，不是日常路徑。

---

## 6. 升級的優先級

若同時觸發多個升級條件（例：tool_error + 高風險動作）：

```
1. 致命級（不解決就無法繼續）：tool_error / Schema 違規 / dependency
2. 流程級（4 輪上限 / Explore 上限）
3. 風險級（高風險動作 plan 預檢）
4. 啟發級（拖太久 / heartbeat 異常）
```

依此順序顯示給使用者。多個同時觸發 → 一次顯示一個（依優先級）。

---

## 7. 鐵律

### 7.1 升級必寫 _escalations 檔
口頭通知不夠，必有人類可讀紀錄供追溯。

### 7.2 升級不自動繼續
使用者明示繼續才繼續。即使 30 分鐘後使用者沒回，也不自動 timeout。

### 7.3 不在 sub-brief 層升級
Sub-brief 內的 ambiguity / decomposition 等回 main，由 main 決定是否升級。Sub-brief 不直接顯示升級對話。

### 7.4 升級前累積證據
不要單一 verdict 就升級。給 framework 自處理機會（同 role retry / 補資料 / re-Explore）。確認自處理失敗才升級。

### 7.5 高風險動作必升級
即使 trust=sandbox，動依賴 / schema / production 配置仍升級（trust 不繞過風險判斷）。

---

## 8. 給接手 agent 的提醒

- **升級 ≠ 失敗**：使用者可決定後繼續，brief state 不一定變 failed
- **致命級升級不能拖**：tool_error 不解決後續任何 spawn 都會壞，立即升級
- **高風險偵測在 Execute 前做**：plan 寫完後、進 Execute 前檢查
- **`/framework-recover` 是升級的反向操作**：使用者離開後回來，用 recover 接續
- **不要設 timeout 自動 cancel**：升級無時限，brief 可以 hold 數天（合理工作節奏）

---

## 9. 相關文件

- `core/control-plane.md`：何時偵測升級條件
- `core/review-loop.md`：round-driven 升級
- `core/clarification.md`：累積 ambiguity 升級
- `core/batch-lock.md`：heartbeat 殭屍升級
- `core/e2r-tree.md`：tree 違規升級
- `commands/framework-recover.md`：使用者接續流程
