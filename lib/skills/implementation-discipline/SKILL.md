---
name: implementation-discipline
description: producer 下筆方法論——把 plan 實作成「reviewer 一次過」的 code（改動清單 / tracer bullet / 交付前自查）
scope: global
applicable_roles: [engineer, planner]
version: 0.1.0
last_updated: 2026-06-01
---

# Implementation Discipline

這份 skill 不教你寫 code（model 本來就會），教你寫出 **reviewer 一次過** 的 code。它是 `code-review-checklist` 的「左移鏡像」：reviewer 事後機械化審的項目，你下筆時就對齊，砍掉 review round trip。

**邊界（避免和其他檔重複）**：

- 「不准做什麼」的紅線 → 看 role 的 §6 鐵律，本檔不重述。
- 審核項目的 single source of truth → `code-review-checklist`，本檔只引用其 § 編號，不複製內容；閾值與規格也一律引用，不在此寫死。
- 讀 diff 的分層方法 → `git-diff-analysis`，本檔 §4 直接接續其「給 engineer 的 self-review 流程」。
- 本檔只回答一件事：**怎麼下筆，才不會被那些檢查擋下來。**

> **給 planner（若本 skill 也掛給你）**：你不下筆，但下面每一項都吃 plan 的輸入品質——`allowed_paths` 要明確、對外命名要定死、wiring 點要點出。讀這份是為了反推「plan 要寫多明確，engineer 才對齊得起來」；缺一項，engineer 就只能回 `ambiguity`。

---

## 1. 下筆前：把 plan 翻成「改動清單」

別打開檔案就改。先把 plan 翻成一份清單，這一步省下整輪 review fail：

1. 讀 plan 的「介面契約 / 範圍 / allowed_paths」。
2. 列出**要碰的每個檔 × 每個檔要做什麼**，逐項對齊 `allowed_paths`。清單外的檔不碰——碰到代表 plan 不足，回 `ambiguity`，別自行擴張範圍。
3. **命名直接抄 plan**：型別 / 函式 / cmd / struct / RPC 名照 plan 寫，不自創、不「優化」。
   → 攔截 `code-review-checklist §11`（doc drift：plan 寫 `LobbyDataSource`、code 寫成 `PGameConfigClient`，未來 engineer 讀 plan 被誤導）。
4. **先列 wiring 清單再動手**：對任何「需在多檔同步出現才生效」的 symbol（config key / env var / registration map / DI 註冊），先 grep 出**所有應出現的點**，列成清單，改的時候逐一勾掉：
   ```bash
   git grep -n "<symbol>"   # 例 PGAME_CONFIG_SERVICE_ADDR / projectConfigMap
   ```
   → 攔截 `code-review-checklist §12`（漏接 wiring：unit test 抓不到，只有 runtime / localTest 會 panic）。

---

## 2. 實作順序：tracer bullet，不要大爆發

打通**一條最小端到端路徑**（哪怕只走 happy path），跑起來確認 wiring 對，再回頭補分支與 edge case。

- 理由：wiring / 介面錯，越早跑越便宜；一次寫完一大段才第一次跑，爆了難定位。
- 隨時對照 plan 的 `estimated_complexity`。**寫的當下感覺規模要超出 plan 預期** → 停手，回 `needs_decomposition`，別硬幹。判定門檻見 `code-review-checklist §10`。

---

## 3. 整合視角：下筆當下維護 caller 一致性

reviewer 的對抗式「整合視角」（§5.x）專抓「改了 A 沒同步 B」。這類問題 checklist §1-13 沒有對應編號，下筆當下就守、別留到最後：

- **改 public API 簽章 → 立刻 grep callers 一起更新**，不累積到最後一次處理。
- **刪函式 / 分支前 → 先 grep callsite**，確認無遺漏 caller。

---

## 4. 交付前自查（emit verdict 前必跑）

本 skill 的核心。丟給 reviewer 前，先跑 reviewer 會跑的機械檢查的 **producer 子集**——只查你自己能驗的「交付物完整性 / 一致性」。

**關鍵界線：self-review ≠ self-verification。** 自查是確認「交付物完整、誠實、對齊 plan」，**不是**寫測試證明自己的 code 對（那是球員兼裁判，違反鐵律；驗證性 unit test 交給獨立 test-writer）。你只「跑既有測試做 regression sanity」，不為自己背書補測試。

接續 `git-diff-analysis §6` 的 self-review 流程，逐項對齊 reviewer：

| 自查項 | 動作 | 對齊 reviewer |
|---|---|---|
| diff 範圍 | `git diff main...HEAD --name-only` → 全在 allowed_paths？ | §1 |
| 規模 | `git diff main...HEAD --stat` → 在 estimated_complexity 預期內？ | §10 |
| 命名對齊 | plan 的對外名逐一 `git grep`，存在且一致？ | §11 |
| 跨檔 wiring | §1 列的 wiring 清單，每個點都接上了？ | §12 |
| 註解紀律 | 新增 / 改動的註解：無 WHAT、無 stale | §13 |
| 自評誠實 | `engineer.output.md` 的變動摘要 == 實際 diff（沒漏報、沒謊報） | §9 |

任一不過 → 改完再 emit verdict，不要把已知問題丟給 reviewer。

**不歸你自查的**（留給 reviewer，別越權）：測試 / lint 的 baseline 對比、對抗式審視（edge / 整合 / 架構 / 未來等視角，見 §5.x）。上表做完即可 emit。

---

## 5. 反例（最常害你被打回的模式）

- **漏接 wiring**：改了 config struct + reader，漏接 `main.go` 的 registration map → §1 沒先列 wiring 清單就動手。
- **自創命名**：plan 寫 `LobbyDataSource`，嫌長改寫成 `Client` → doc drift，reviewer §11 fail。
- **dead-weight 抽象**：為了「讓 test-writer 好測」預先注入 clock interface / wrapper，但 plan 沒要求 → 過度設計，reviewer 架構視角 fail。需要的抽象由 plan 定，不自行加。
- **大爆發**：一次寫完一大段才第一次跑 → 沒打 tracer bullet，wiring 錯難定位，且規模常順勢爆掉 §10。
