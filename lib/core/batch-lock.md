# Batch Lock — `_active.yaml` 與並發控制

> 本文件規範 brief 的並發語意：單 active brief、`_active.yaml` 結構、中斷恢復。
>
> 對應 design-summary 第 11.3 節決議：multi-agent = 同 main session 內 spawn subagent，**不**允許多 process / 多 session 跑同份 brief。

---

## 1. 設計原則

1. **單 active brief**：任何時候 framework 只有一個 root brief 在跑
2. **Sub-brief 不算新 brief**：是當前 brief 的內部展開
3. **`_active.yaml` 是鎖**：存在即拒新 brief
4. **PID 僅診斷**，framework 不做活 / 死判斷（empire v3 決議延續）
5. **恢復靠使用者明示**：framework 不自動清 lock

---

## 2. `.framework/briefs/_active.yaml` Schema

```yaml
brief_id: 2026-05-06-slot-revenue-q2
started_at: 2026-05-06T10:00:00
phase: exploring                    # exploring | awaiting_approval | executing | reviewing | learning | on_hold
                                    # learning = control-plane.md Step G 進行中（learning loop）
                                    # on_hold = 升級使用者後使用者選 hold（escalation-rules.md §4.3）
pid: 12345                          # 啟動 main session 的 pid（僅診斷）
host: liangxuanzhong-laptop         # hostname（僅診斷）
last_heartbeat: 2026-05-06T11:30:00 # main 每動一次更新（僅診斷）
clarification_rounds: 3             # grill-me 已用題數（cap 20）
recipe: data-analytics
roster: [data-analyst, analysis-reviewer, writer]
worktree_enabled: false
trust_mode: standard
```

### 2.1 欄位說明

| 欄位 | 必填 | 說明 |
|---|---|---|
| `brief_id` | ✓ | 當前 active root brief id |
| `started_at` | ✓ | ISO timestamp，brief 啟動時間 |
| `phase` | ✓ | 當前 brief 所處 E²R 階段 |
| `pid` | ✓ | main session 的 pid（診斷用） |
| `host` | ✓ | hostname（診斷用） |
| `last_heartbeat` | ✓ | main 每完成一個動作更新一次 |
| `clarification_rounds` | ✓ | grill-me 計數，避免 brief 重啟後重置 |
| `recipe` | ✓ | 啟用的 recipe 名稱 |
| `roster` | ✓ | 啟用的 role 清單 |
| `worktree_enabled` | ✓ | 此 brief 是否用 worktree |
| `trust_mode` | ✓ | 此 brief 啟動時的 trust mode（中途切 mode 不影響當前 brief）|

### 2.2 寫入時機

- 建立 brief（`/brief-new` 完成 brief.md 後）→ **先跑重疊機械閘** `python .framework/scripts/scope_check.py --overlap <預估 affected_repos 逗號串>`：非空交集（與 active brief 範圍或殘留 dirty 工作樹重疊；無 active brief 時只驗 dirty 殘留）→ 顯示給使用者確認後才建 _active.yaml（防平行/殘留互蓋）→ 建立 _active.yaml
- 階段轉換（exploring → awaiting_approval / executing / reviewing / learning）→ 更新 `phase`
- 任何 main 動作（spawn role / 寫 verdict / 訪談題數變化）→ 更新 `last_heartbeat` + 對應欄位
- Brief 完成 / 取消 → 刪除 _active.yaml

---

## 3. 並發語意

### 3.1 試開新 brief（_active.yaml 已存在）

`/brief-new` 偵測：

```
1. 讀 _active.yaml
2. 顯示：
   「目前已有 active brief：
      brief_id: {existing.brief_id}
      phase: {existing.phase}
      已執行：{started_at - now}
      最後活動：{last_heartbeat - now} 前

    選擇：
      (a) 等待當前完成（取消新 brief 嘗試）
      (b) 取消當前 brief，開新的（會丟失當前 brief 進度，需確認）
      (c) 升級為當前 brief 的 sub-brief（需 manual integrate）」
3. (a) → 退出
4. (b) → 提示二次確認 → 寫 .framework/briefs/{existing}/CANCELLED → 刪 _active → 開新 brief
5. (c) → 提示：使用者必修當前 brief 的 plan 加 sub-brief（不自動執行）
```

### 3.2 Sub-brief 不開新 lock

`_tree.yaml` 內的 sub-brief 是 root brief 的內部結構。不寫 `_active.yaml`。

---

## 4. 中斷恢復

### 4.1 中斷情境

| 情境 | 偵測 | 狀態 |
|---|---|---|
| 使用者 Ctrl-C 殺 main | _active.yaml 還在、main session 不存在 | 殭屍 |
| 系統重啟 | 同上 | 殭屍 |
| Network / API 失敗 | _active.yaml 還在、main 還活著 | 暫時失敗，main 自重試 |
| Bug crash main | _active.yaml 還在、main 不存在 | 殭屍 |

### 4.2 偵測殭屍

下次 main session 啟動 / 使用者執行 `/framework-status`：

```
1. 偵測 _active.yaml 存在
2. 比對 last_heartbeat：
   - < 10 分鐘：可能仍在跑（main 在思考 / 大 task）
   - 10 分鐘 - 1 小時：可疑
   - > 1 小時：高機率殭屍
3. 顯示：
   「偵測到 active brief 但 main session 未感應到活動。
    brief_id: {...}
    last_heartbeat: 1 hour 23 min 前
    可能 main session 已中斷（Ctrl-C / crash / 系統重啟）

    要 /framework-recover 嗎？(y/n)」
```

### 4.3 `/framework-recover` 流程

```
1. Read _active.yaml + 對應 _tree.yaml + _manifest.md
2. 顯示當前狀態：
   - brief_id / phase
   - 各 sub-brief 進度
   - 最後一個 verdict 是什麼
3. 對每個 in-flight 節點（state=executing / reviewing / paused）詢問：
   「Sub-brief X (stage Y) 中斷時 state={state}, round={round}
    選擇：
      (a) 繼續跑（重新 spawn 該 stage role）
      (b) 標記完成（人工介入後接續）
      (c) 標記失敗（不再跑此 sub-brief）
      (d) 取消整個 brief」
4. 依答案更新 _tree.yaml
5. 更新 _active.yaml.last_heartbeat = now、_active.yaml.pid = current pid
6. 進入 Execute 主迴圈接續
```

### 4.4 `/framework-unlock` 強制清

```
1. 顯示警告：
   「即將強制刪除 _active.yaml。
    當前 brief 進度將無法繼續（除非手動重建狀態）。
    建議：先 /framework-recover 嘗試恢復，無法恢復才用 unlock。
    確定？(yes/N)」
2. yes → 刪 _active.yaml
3. brief 目錄不刪（使用者後續可參考）
```

---

## 5. 為什麼不自動偵測 PID

empire v3 決議延續：

- PID 偵測在不同 OS 行為不同（Windows ps vs Linux ps），跨平台麻煩
- PID 可能被 reuse（殺 main 後同 PID 可能被別 process 用）
- main 的 cleanup 不保證乾淨（崩潰時 _active.yaml 留下是常態）
- 信任使用者判斷比 framework 自動猜對

**例外**：last_heartbeat 是「軟 PID」——若 ≥ 1 小時無更新，提示但不自動清。

---

## 6. 多開 Claude Code session 怎辦

### 6.1 使用者意圖：跨機器 / 跨 session

**Framework 不支援**：multi-agent ≠ multi-session。

若使用者真的需要平行：
- 開兩個獨立 repo（每 repo 自己的 framework + _active.yaml）
- 或在同一 repo 開兩個 brief 必序列化（一個 done 才開下一個）

### 6.2 真的兩個 session 同時開了

兩個 main 都看到 _active.yaml：
- 第一個 session 是「主」（持續更新 last_heartbeat）
- 第二個 session 偵測到「pid != 自己 + last_heartbeat 還新」→ 拒絕進入 brief 模式
- 第二個 session 顯示：「另一個 session 正在處理 brief X，本 session 將 read-only。要繼續嗎？」
- 使用者可以 `/brief-status` 查進度，但不能改

**機制**：每次 main 動作前 check `pid` 與 `last_heartbeat`，若 pid != self → 拒寫 _tree.yaml / 不 spawn role。

---

## 7. brief 目錄與 _active.yaml 關係

| 場景 | _active.yaml | .framework/briefs/{id}/ |
|---|---|---|
| Brief 進行中 | 存在 | 存在 |
| Brief 完成 | 已刪 | 已歸檔到 _archive/ |
| Brief 取消 | 已刪 | 留 CANCELLED 標記，仍在 .framework/briefs/ |
| 殭屍中斷 | 存在 | 存在（in-flight 狀態） |
| Recover 後 | 存在（更新 pid / heartbeat） | 同前 |
| Unlock 後 | 已刪 | 留下，需使用者手動處理 |

---

## 8. 鐵律

- **Single active brief**：rule of one，不允許多個 root brief 同時跑
- **PID 僅診斷**：framework 不做 PID 活 / 死自動判斷
- **Recovery 走顯式對話**：使用者明示要 recover，main 不自動接續
- **Unlock 警告嚴格**：強制清 lock 是逃生口，不該成為日常操作
- **last_heartbeat 必更新**：每動一次都更新（避免假殭屍）

---

## 9. 給接手 agent 的提醒

- **Heartbeat 是輕度信號**：不要靠它做 critical decision，只用於使用者顯示與 recover 判斷
- **Sub-brief 不寫 _active.yaml**：若你看到 _active 內 brief_id 是 sub-brief id 格式 → 是 bug
- **Ctrl-C 後 _active 留下是常態**：不要一看到留下就警告，應檢查 last_heartbeat
- **Recover 後 pid / heartbeat 必更新**：避免下次再被誤判殭屍
- **多 session 偵測非優先**：實務上使用者通常不會這樣搞，但 framework 設計時要考慮過

---

## 10. 相關文件

- `core/control-plane.md`：main 何時讀 / 寫 _active.yaml
- `core/e2r-tree.md`：_active.yaml 與 _tree.yaml 的關係
- `commands/framework-recover.md`：recover 流程具體
- `commands/framework-unlock.md`：unlock 流程具體
- `commands/brief-cancel.md`：使用者主動取消
