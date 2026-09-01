# Batch Lock — Lock Registry 與並發控制（Multi-Lane）

> 本文件規範 brief 的並發語意：**每 scope 單 active brief**（multi-lane）、`_active/{brief_id}.yaml` lock registry 結構、admission 閘、中斷恢復。
>
> 2026-09-01 改制：原「全域單 active brief」（design-summary 第 11.3 節舊決議）改為 **scope-based lock registry**——多個 brief 可並行，條件是 `affected_repos` 互不相交（repo-disjoint）。「1 main session = 1 control plane = 1 root brief」不變量保留：並行的單位是 **session**（每條 lane 一個 Claude Code session），不是單 session 內多 brief。

---

## 1. 設計原則

1. **每 scope 單 active**：任一 repo 任何時候只屬於一個 active brief（lane）。repo-disjoint 的多個 root brief 可同時跑
2. **1 session = 1 brief**：每條 lane 由自己的 main session 編排；單 session 不同時管多個 root brief（main context 是最稀缺資源，理由同 e2r-tree §1.2 禁 L2）
3. **Sub-brief 不算新 brief**：是當前 brief 的內部展開，不寫 lock
4. **`_active/{brief_id}.yaml` 是 lane 鎖**：admission 閘（§3.1）通過才可建立
5. **PID 僅診斷**，framework 不做活 / 死判斷（empire v3 決議延續）
6. **恢復靠使用者明示**：framework 不自動清 lock
7. **Phase 1 粒度 = repo-disjoint only**：同 repo 兩個 brief 並行不支援（需 per-repo worktree，屬 phase 2）

---

## 2. Lock Registry：`.framework/briefs/_active/`

```
.framework/briefs/_active/
  {brief_id}.yaml      ← 每個 active brief（lane）一份
  _closing.lock        ← brief_close.py 的收尾互斥鎖（短暫存在；非 lane 鎖）
```

### 2.1 單份 lock schema

```yaml
brief_id: 2026-09-01-wallet-rounding
started_at: 2026-09-01T10:00:00
phase: exploring                    # exploring | awaiting_approval | executing | reviewing | local_test | learning | on_hold
                                    # reviewing = L0 holistic review（Step F）+ amendment 期（Step F'）
                                    # local_test = control-plane.md Step F2 進行中（全域互斥，見 §3.4）
                                    # learning = control-plane.md Step G 進行中（learning loop）
                                    # on_hold = 升級使用者後使用者選 hold（escalation-rules.md §4.3）
affected_repos: [SGC_WalletService, SGC_WalletClient]
                                    # 本 lane 的 scope（冗餘欄，admission 不必解析 brief 目錄）
scope_status: provisional           # provisional（brief-new 預估）| confirmed（brief-approve 收斂後）
pid: 12345                          # 啟動本 lane main session 的 pid（僅診斷）
host: liangxuanzhong-laptop         # hostname（僅診斷）
last_heartbeat: 2026-09-01T11:30:00 # 本 lane main 每動一次更新（僅診斷）
clarification_rounds: 3             # grill-me 已用題數（cap 20）
recipe: dev-team
roster: [planner, engineer, code-reviewer]
worktree_enabled: false
trust_mode: standard
autonomous_mandate: _mandate.json   # 選填；離場授權指針（內容在 briefs/{id}/_mandate.json，見 control-plane §5.6）
```

### 2.2 欄位說明

| 欄位 | 必填 | 說明 |
|---|---|---|
| `brief_id` | ✓ | 本 lane 的 root brief id；**檔名必為 `{brief_id}.yaml`**（兩者不符是 bug） |
| `started_at` | ✓ | ISO timestamp，brief 啟動時間 |
| `phase` | ✓ | 本 lane 所處 E²R 階段 |
| `affected_repos` | ✓ | 本 lane 的 repo scope。admission / scope_check 的主要資料源；main 更新 plan scope 時**必同步此欄** |
| `scope_status` | ✓ | `provisional`（預估，brief-new 時）→ `confirmed`（brief-approve 以 plan 權威值收斂後） |
| `pid` | ✓ | 本 lane main session 的 pid（診斷用） |
| `host` | ✓ | hostname（診斷用） |
| `last_heartbeat` | ✓ | 本 lane main 每完成一個動作更新一次 |
| `clarification_rounds` | ✓ | grill-me 計數，避免 brief 重啟後重置 |
| `recipe` | ✓ | 啟用的 recipe 名稱 |
| `roster` | ✓ | 啟用的 role 清單 |
| `worktree_enabled` | ✓ | 此 brief 是否用 worktree |
| `trust_mode` | ✓ | 此 brief 啟動時的 trust mode（中途切 mode 不影響當前 brief）|
| `autonomous_mandate` | 選填 | **僅指針值 `_mandate.json`**，內容一律在 `briefs/{id}/_mandate.json`（結構化 schema + 驗證器見 control-plane §5.6；**禁止散文 mandate 寫在本檔**——2026-07-06 結構化改制）。hooks 對 registry 取**聯集**：任一 lane 的 mandate active 即 deny 生效（gate_mandate.py；本 session 可設 `FRAMEWORK_BRIEF_ID` 精確歸屬） |

### 2.3 寫入時機

- 建立 brief（`/brief-new` 完成 brief.md 後）→ **先跑 admission 機械閘**
  `C:/Python312/python.exe .framework/scripts/scope_check.py --overlap <預估 affected_repos 逗號串>`
  （交集對象 = 所有 active lane 的 repos ∪ 無主 dirty 工作樹）→ 無交集才建 `_active/{brief_id}.yaml`
  （`scope_status: provisional`）；有交集 → 顯示歸屬給使用者選（§3.1）
- **`/brief-approve` scope 收斂重驗**：plan 的 affected_repos 聯集為權威值 →
  `scope_check.py --overlap <plan repos> --self {brief_id}` → 通過才更新 lock 的
  `affected_repos` + `scope_status: confirmed`；撞到（預估錯 / 兩鎖之間別的 lane 被 admit）→ 升級使用者
- **Execute 中擴 scope**（needs_decomposition 加 repo）→ 必先 `--overlap <新增 repos> --self {brief_id}`
  通過，才可同步更新 plan 與 lock 的 `affected_repos`
- 階段轉換（exploring → awaiting_approval / executing / reviewing / local_test / learning）→ 更新 `phase`
  （**進 local_test 前先過 §3.4 全域互斥檢查**）
- 任何 main 動作（spawn role / 寫 verdict / 訪談題數變化）→ 更新 `last_heartbeat` + 對應欄位
- 使用者離場授權 → 寫 `briefs/{id}/_mandate.json` + 跑 `C:/Python312/python.exe .framework/scripts/mandate_check.py .framework/briefs/{id}` 通過 → 本檔加 `autonomous_mandate: _mandate.json`；使用者回來確認後 mandate 標 consumed（指針保留供 trail）
- Brief 完成 / 取消 → 刪除 `_active/{brief_id}.yaml`（brief_close.py 收尾時自動；取消由 main 刪）

---

## 3. 並發語意

### 3.1 Admission 閘（`/brief-new` / `/brief-import` / `/brief-reopen`）

```
1. 跑 scope_check.py --overlap <預估 affected_repos>
2. 無交集（exit 0）→ 顯示 active lanes 摘要給使用者確認 → 建 lock → 照常進 Explore
3. 有交集（exit 2）→ 顯示衝突歸屬（哪個 repo ← 哪條 lane / 無主 dirty），選擇：
   (a) 等待該 lane 完成（取消本次嘗試；可先放 inbox/ 排隊）
   (b) 取消衝突 lane，開新的（丟失該 lane 進度，需二次確認；只能取消屬於自己的 lane）
   (c) 升級為該 lane 的 sub-brief（需 manual integrate：修該 brief 的 plan）
   (d) 改 scope 避開衝突 repo（縮 affected_repos 後重跑閘）
4. 無主 dirty（不屬任何 lane 的殘留工作樹）衝突 → 先處置殘留（收工 / stash / 併入某 lane 的 plan）
```

### 3.2 Sub-brief 不開新 lock

`_tree.yaml` 內的 sub-brief 是 root brief 的內部結構。不寫 registry。

### 3.3 Lane 互不侵犯（session 紀律）

- 每個 main session 只操作**自己持有的 brief**（session 對話中正在跑的那個）
- main 每次寫動作（_tree.yaml / spawn / phase 轉換）前，驗自己的 `_active/{brief_id}.yaml` 存在且 brief_id 相符——不符即停，提示使用者 `/framework-recover`
- 對**他 lane** 一律 read-only：可 `/brief-status` 查看，不可寫其 _tree / spawn 其 role / 動其 lock
- Producer/reviewer 的 repo 邊界照舊由 `scope_check.py --repos <本 sub-brief repos>` 把關：
  他 lane 的合法 dirty 顯示為 `INFO(lane:{brief_id})` 不違規；**無主 dirty 仍 VIOLATION**

### 3.4 `local_test` 全域互斥（第二條互斥軸）

Step F2 的 integration-tester 會**真的啟動 service + 臨時 patch outbound URL**（共享機器資源：port、infra、docker）——repo-disjoint 擋不住這種衝突。規則：

```
main 進 Step F2 前：掃 _active/*.yaml 的 phase 欄
  無他 lane 處於 local_test → 更新自己 phase: local_test → 開跑
  有 → 等待該 lane 離開 local_test（或問使用者是否先跑其他步驟 / 稍後重試）
```

全域同時**只允許一條 lane 處於 `phase: local_test`**。

### 3.5 收尾互斥（`_closing.lock`）

`brief_close.py` 收尾時對 registry 取 `_closing.lock`（O_EXCL）——多 lane 同時收尾會交錯寫共用 `memory/telemetry/*.jsonl`。他 lane 收尾中 → exit 1 稍候重跑；stale（>10min，crash 殘留）自動搶佔。main 不需手動管理此鎖。

---

## 4. 中斷恢復（per-lane）

### 4.1 中斷情境

| 情境 | 偵測 | 狀態 |
|---|---|---|
| 使用者 Ctrl-C 殺某 lane 的 main | 該 lane lock 還在、其 session 不存在 | 該 lane 殭屍（他 lane 不受影響） |
| 系統重啟 | 所有 lock 還在、所有 session 不存在 | 全部 lane 殭屍 |
| Network / API 失敗 | lock 還在、main 還活著 | 暫時失敗，main 自重試 |
| Bug crash 某 lane 的 main | 該 lane lock 還在、main 不存在 | 該 lane 殭屍 |

### 4.2 偵測殭屍

下次 main session 啟動 / 使用者執行 `/framework-status`：

```
1. 掃 _active/*.yaml（每份獨立判斷）
2. 逐 lane 比對 last_heartbeat：
   - < 10 分鐘：可能仍在跑（該 lane main 在思考 / 大 task）
   - 10 分鐘 - 1 小時：可疑
   - > 1 小時：高機率殭屍
3. 顯示（僅列可疑 / 殭屍 lane）：
   「偵測到 lane 無活動：
    brief_id: {...}
    last_heartbeat: 1 hour 23 min 前
    可能該 lane 的 main session 已中斷（Ctrl-C / crash / 系統重啟）

    要 /framework-recover {brief_id} 嗎？(y/n)」
```

### 4.3 `/framework-recover [brief_id]` 流程

```
0. 無參數：registry 只有一個 lock → 用它；多個 → 列 lane 清單要求指定
1. Read _active/{brief_id}.yaml + 對應 _tree.yaml + _manifest.md
2. 顯示當前狀態：
   - brief_id / phase / affected_repos
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
5. 更新該 lock 的 last_heartbeat = now、pid = current pid
6. 進入 Execute 主迴圈接續（本 session 自此持有該 lane）
```

### 4.4 `/framework-unlock <brief_id>` 強制清

```
0. 必帶 brief_id（多 lane 下無「the lock」可默認；registry 僅一份時可省）
1. 顯示警告：
   「即將強制刪除 _active/{brief_id}.yaml。
    該 lane 進度將無法繼續（除非手動重建狀態）。
    建議：先 /framework-recover {brief_id} 嘗試恢復，無法恢復才用 unlock。
    確定？(yes/N)」
2. yes → 刪該 lock（僅該份；他 lane 不動）
3. brief 目錄不刪（使用者後續可參考）
```

---

## 5. 為什麼不自動偵測 PID

empire v3 決議延續：

- PID 偵測在不同 OS 行為不同（Windows ps vs Linux ps），跨平台麻煩
- PID 可能被 reuse（殺 main 後同 PID 可能被別 process 用）
- main 的 cleanup 不保證乾淨（崩潰時 lock 留下是常態）
- 信任使用者判斷比 framework 自動猜對

**例外**：last_heartbeat 是「軟 PID」——若 ≥ 1 小時無更新，提示但不自動清。

---

## 6. 多 session 並行的正式模型

### 6.1 正常型態（2026-09-01 起支援）

- 每條產線（repo-disjoint 的 scope）開一個 Claude Code session，各跑一個 brief
- Admission 閘（§3.1）機械保證 scope 不相交；lane 紀律（§3.3）保證互不侵犯
- 建議搭配：非焦點 lane 走 mandate（control-plane §5.6）自主推進，使用者注意力集中在一條 lane 的人審關卡；`/brief-status` 無參數顯示跨 lane dashboard
- 多 lane 並行 + 有 lane 掛 mandate 時，建議各 session 設 `FRAMEWORK_BRIEF_ID`（gate 精確歸屬，避免他 lane 的 mandate deny 誤傷本 lane 的 ask 語意）

### 6.2 兩個 session 搶同一條 lane

同一個 brief 只能有一個 main session 持有：

- 持有者 = 對話中正在跑該 brief、持續更新其 last_heartbeat 的 session
- 第二個 session 偵測到「該 lock 的 pid != 自己 + last_heartbeat 還新」→ 拒絕進入該 brief，read-only
- 顯示：「另一個 session 正在處理 brief X，本 session 對它 read-only。可 /brief-new 開別條產線，或 /brief-status 查進度」
- 真正接手（原 session 已死）走 `/framework-recover {brief_id}`（§4.3，更新 pid + heartbeat）

### 6.3 同 repo 的兩個 task 怎麼辦（phase 1 不支援並行）

- 序列化：一個 done 才開下一個（可先放 `briefs/inbox/` 排隊，inbox 檔宣告 `affected_repos` 供 dashboard 判斷可開案時機）
- 或合併成一個 brief 的兩個 sub-brief
- Phase 2 才考慮 per-repo worktree 隔離的同 repo 並行

---

## 7. brief 目錄與 lock 關係

| 場景 | `_active/{id}.yaml` | `.framework/briefs/{id}/` |
|---|---|---|
| Brief 進行中 | 存在 | 存在 |
| Brief 完成 | 已刪（brief_close.py） | 已歸檔到 _archive/{year-month}/ |
| Brief 取消 | 已刪 | 留 CANCELLED 標記，仍在 .framework/briefs/ |
| 殭屍中斷 | 存在 | 存在（in-flight 狀態） |
| Recover 後 | 存在（更新 pid / heartbeat） | 同前 |
| Unlock 後 | 已刪 | 留下，需使用者手動處理 |

---

## 8. Legacy 遷移（單檔 `_active.yaml` → registry）

- 舊制單檔 `.framework/briefs/_active.yaml` 已廢止。scripts（scope_check / brief_close）與 hooks（gate_mandate）保留兼容讀取：legacy 單檔視為一條 lane
- main / 指令偵測到 legacy 單檔 → 提示使用者：讀出內容 → 寫 `_active/{brief_id}.yaml`（補 `affected_repos`（從 plan 解析）與 `scope_status: confirmed`）→ 刪 legacy 單檔（一次性）
- 手工 park 慣例 `_active.snapshot.yaml`（插隊時把 lock 搬進 brief 目錄暫存）**正式退役**：插隊 = repo-disjoint 直接開第二條 lane；同 repo 插隊照舊 cancel / 等待

---

## 9. 鐵律

- **每 scope 單 active**：任一 repo 同時只屬一條 lane；admission 閘不可跳過
- **1 session = 1 brief**：單 main session 不併行管多個 root brief
- **檔名 = brief_id**：`_active/{brief_id}.yaml` 檔名與內文 brief_id 必一致
- **affected_repos 同步**：plan scope 變動必同步 lock 冗餘欄（否則 admission 閘資料失真）
- **PID 僅診斷**：framework 不做 PID 活 / 死自動判斷
- **Recovery 走顯式對話**：使用者明示要 recover，main 不自動接續
- **Unlock 警告嚴格**：強制清 lock 是逃生口，不該成為日常操作；只清指定的那份
- **last_heartbeat 必更新**：每動一次都更新（避免假殭屍）
- **local_test 全域互斥**：同時只有一條 lane 可處於 local_test phase

---

## 10. 給接手 agent 的提醒

- **Heartbeat 是輕度信號**：不要靠它做 critical decision，只用於使用者顯示與 recover 判斷
- **Sub-brief 不寫 registry**：若 `_active/` 內出現 sub-brief id 格式的檔 → 是 bug
- **Ctrl-C 後 lock 留下是常態**：不要一看到留下就警告，應檢查該份的 last_heartbeat
- **Recover 後 pid / heartbeat 必更新**：避免下次再被誤判殭屍
- **`_closing.lock` 不是 lane 鎖**：它是 brief_close.py 的收尾互斥，短暫存在；掃 lane 時跳過 `_` 開頭的檔
- **他 lane 的 dirty 是常態**：scope_check 標 `INFO(lane:x)` 的 dirty 不是違規，不要拿去煩使用者

---

## 11. 相關文件

- `core/control-plane.md`：main 何時讀 / 寫 lock（Step A / D / F2 / H / I）
- `core/e2r-tree.md`：lock 與 _tree.yaml 的關係
- `commands/framework-recover.md`：recover 流程具體
- `commands/framework-unlock.md`：unlock 流程具體
- `commands/brief-cancel.md`：使用者主動取消
- `commands/brief-status.md`：跨 lane dashboard
- `scripts/scope_check.py`：admission / scope 機械閘實作
