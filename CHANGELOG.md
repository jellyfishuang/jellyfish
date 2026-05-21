# Framework CHANGELOG

記錄 framework lib（`lib/`）的版本演變。版號採 SemVer，對應日後的 git tag。
版號真實來源＝`lib/VERSION`；各 repo 複製時以該檔為準。

## 0.2.0 — 2026-05-21

反饋輪 + 外部 KB sink。6 大主題，核心目標：避免小改動被重流程過度工程化 + 攔截 unit test 抓不到的整合 bug + 讓 learning loop 可選地把蒸餾知識升流外部 KB。
動到 lib 共 11 檔；外部 KB sink 另新增 `framework-recall.md` 並改 control-plane / learning-loop / generator / claude-md-template / design-summary / 9 個 role。

- **micro-change size gating（避免過度工程化）**
  - `core/review-loop.md`：新增 §3.4 對抗式 review 豁免（diff 淨改 < N 行自動跳過 adversarial second pass）
  - `core/control-plane.md`：新增 Step 0 規模 triage（micro-change 建議走 bug_fix、跳過 planning）
  - `init/pipeline-yaml-template.md`：`second_review` 支援物件寫法（`enabled` / `skip_below_lines` / `skip_single_file`），`true` 向後相容
- **靜態 vs runtime 驗收分離**
  - `core/control-plane.md`：holistic review 標明僅靜態驗證；[runtime] 項列「需使用者端 localTest」
  - `roles/planner.md`：驗收條件分 [靜態] / [runtime]
  - `roles/planning-reviewer.md`：新增「驗收分靜態 / runtime」檢查
- **跨檔 wiring 完整性**
  - `skills/code-review-checklist/SKILL.md`：新增 §12（grep 所有 wiring 點，漏接即 fail）
  - `roles/code-reviewer.md`：checklist + 整合視角補 wiring 檢查
- **plan↔code 命名對齊 + plan 分層**
  - `skills/code-review-checklist/SKILL.md`：新增 §11（plan↔code 命名 / 契約對齊）
  - `roles/planner.md`：`範圍` 改為「架構決策（穩定層）」+「範圍（實作細節層）」；禁 round 1 釘死低層細節；plan 為當前狀態規格非 changelog
  - `roles/planning-reviewer.md`：新增「Plan 分層」「Plan 未肥大」「architecture.md 引用已驗證」檢查
- **註解紀律 + 架構視角**
  - `skills/code-review-checklist/SKILL.md`：新增 §13（禁 WHAT 註解 / 無 drift / WHY 正確）
  - `roles/code-reviewer.md`：對抗式三視角→四視角（加架構視角，抓 dead-weight 過度設計 / architecture drift）
  - `roles/engineer.md`：新增註解紀律（少寫、寫對，禁 WHAT）；格式化只跑單檔，禁全域 reformat
  - `roles/test-writer.md`：case 數自評必用機器算；整合 / wire 行為標明 unit test 不涵蓋
- **可插拔外部 KB sink（opt-in，預設解耦）**
  - `core/learning-loop.md`：新增 §8.5 升流機制 + §7 Step 4 `(m)` 選項 + §11.5 改寫（解耦→條件式升流）
  - `core/control-plane.md`：§8.5 解耦→KB sink + §4 Step 2 跨 repo 參考
  - 新增 `commands/framework-recall.md`：唯讀查外部 KB 參考其他 repo（純命令驅動、唯讀工具集）
  - `init/generator.md`：§2.8 `.initialized` 加 `knowledge_base{path,promote,recall}` opt-in 段
  - `init/claude-md-template.md` + 9 個 role：boundary 措辭改為通用「不直寫外部 KB」
  - 設計見 `design-summary.md` §12.3 / `core/learning-loop.md` §8.5
- 其他：`design-summary.md` 同步更新、`VERSION` bump

## 0.1.0 — baseline（反饋前）

framework dev-team recipe 的反饋前狀態，事後追認為起點基準。
無完整快照（僅保留部分 before 備份），故不回補 git tag，僅以本條目記錄。
