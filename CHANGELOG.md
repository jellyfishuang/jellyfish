# Framework CHANGELOG

記錄 framework lib（`D:\Claude\.framework\lib`）的版本演變。版號採 SemVer，對應日後的 git tag。
版號真實來源＝`lib/VERSION`；各 repo 複製時以該檔為準。

## 0.6.0 — 2026-06-17

架構速覽（design sketch）+ 條件式 ack 閘。動因：SGC 部署實例（brief `2026-06-11-hot-lobby-api`）出現一個架構洩漏——gateway 建兩個下游 client、未復用既有連線——**通過 code-review 與 adversarial arch-review（被歸 advisory 默默記錄），使用者目視 user_code_review 才發現、回頭走 amendment 收斂**。根因：advisory finding 清單會埋掉「形狀」問題，形狀問題（如新增與既有功能重疊的元件而未復用）不主動浮給使用者。新增 1 個 verdict schema 欄 + 新的 arch-review 輪末投遞機制（條件式 ack 閘），跨 2 檔，屬新機制主題，故 minor bump。

- **架構速覽（design sketch）：arch-review 輪末把「形狀」頂給使用者**（去專案化回流）
  - `roles/architecture-reviewer.md`：§6 verdict schema 新增 `design_sketch` 物件（`change` / `shape` / `reuse_vs_new` / `overlaps_existing` Y/N / `pattern_divergence` Y/N / `key_tradeoffs` / `ack_required` derived）；新增 §6.1「架構速覽」規範（每次 verdict 必附、≤30 行、兩 focus 皆出、arch-review 被 skip 則無此輪；誠實規則禁為少打擾瞞報 overlaps/divergence）；§8 鐵律補對應條
  - `core/control-plane.md`：§5.3 新增 §5.3.1「Architecture-reviewer 議案處理」——main 在每輪**非 skip** 的 arch-review 結束時原樣貼 `design_sketch`；`ack_required==false`（重疊=N 且 偏離=N）純 FYI 不等待、`==true`（重疊=Y 或 偏離=是）走輕量 ack 閘（等使用者一句確認才推進，非 blocker 仲裁、不卡輪數）；blocker 仲裁與速覽 ack 獨立並行
  - 去專案化：lib 內以通用「既有元件 / pattern」描述，剔除實例的 client 名 / brief id；SGC 觸發案例僅記於本 CHANGELOG 動因
- 設計來源：SGC 部署實例 brief `2026-06-11-hot-lobby-api` 收尾 retro，使用者拍板「時機：兩點都出、skip 不出；強度：重疊或偏離才 ack」
- 未採納（記錄）：「修正 B」severity 校準（把『新增與既有功能重疊元件而未復用』預設升 ≥MAJOR）——本版只做投遞管道 + ack 閘，分類維持原樣，待實戰驗證速覽是否確實擋得住後再議

## 0.5.0 — 2026-06-16

規格感知審查 + 量化註解紀律回流。動因：SGC 部署實例（0.4.0 base）在實戰中於 `.claude/agents` 既有角色上演化出兩個通用紀律主題，去專案化後回流母體。收斂兩主題、新增 1 個 verdict schema 欄，跨 5 檔純新增規則（無新角色、無機制變更，但屬新規則主題），故 minor bump。SGC 端其餘差異（`worktree=false` / §7 SGC Multi-Repo Override / `SGC_*`·`go test`·provider·port / integration-tester 全檔實例化 / planning-reviewer·test-writer 精簡重寫 / tier·skill 調整）判定為落地實例化或退化，**不回流**。

- **規格感知審查（reviewer 報對稱性 / special-case finding 前必對照 brief 規格）**（去專案化回流）
  - `core/control-plane.md`：reviewer spawn input 區段新增「通用約定」——main spawn 任何 reviewer 時 input 必含 brief.md；涉規格決定的 special case / 不對稱設計時，main 在 spawn prompt 主動摘要相關規格條款（cold reviewer 即使有 brief，rubric 仍可能誤判規格要求的不對稱為 smell）
  - `roles/architecture-reviewer.md`：§5 rubric 後新增「對稱性 / special-case finding 的規格豁免」區塊（報 finding 前對照 brief，規格明文要求的不對稱不報為 smell）；verdict schema 新增 `spec_checked` 欄（對稱性 / special-case 維度必填）；§8 鐵律補對應條
  - `roles/code-reviewer.md`：§4 執行流程 Read 清單加 `brief.md`（規格意圖，辨認 special case）；§5.x 對抗式架構視角補「同類走不同路 / special case 先查 brief 規格是否要求」
  - 與 `lessons/architecture.md` L1 呼應；去專案化：保留 brief.md / lessons 通用路徑，無 SGC 字眼
- **量化註解紀律（少寫、寫對的可機械化上限）**（去專案化回流）
  - `roles/engineer.md`：既有「註解紀律」鐵律補三條子規則——禁決策敘述 / 歷史（移 commit / brief）、量化上限（單區塊 ≤ 3 行、exported symbol doc ≤ 1 行、新增註解佔比 > 15% 自審）、emit 前 self-check 必跑
  - `roles/code-reviewer.md`：§5「註解紀律」rubric 升級為「註解紀律（量化）」，新增 (d) 無 > 3 行區塊、(e) exported symbol doc ≤ 1 行、(f) code 註解用半形標點
  - 去專案化：`*.go` → 通用「原始碼」、`godoc` → 「exported symbol 的 doc 註解」，剔除 SGC session 名稱與 vault `[[...]]` 連結
- **brief_stages 模板微修**
  - `init/claude-md-template.md`：Brief 結束清單 Step 4 sessions schema 註補「若 step 4 在 step 2/3 之前寫過（main 提前寫），需在此補完」
- 設計來源：`D:\CodeSpace\SGC\.claude\agents` ↔ 母體 `lib/roles` 雙向同步盤點（通用強化往上併、實例化往下留）
- 註：未併回的 SGC 退化（template verdict `partial→fail` 與 control-plane `case partial` 脫鉤、xref `2.e→2.d` 指錯子步）一併記錄為「不採信」

## 0.4.0 — 2026-06-05

SGC 部署實例回流。動因：SGC fork（0.2.0 base）在實戰中演化出母體沒有的機制與兩個新角色，與母體做雙向同步——母體 0.3.x 機制 forward-port 進 SGC，SGC 的下列產物去專案化後回流母體。新增 2 role + brief_stages 框架 + amendment 政策轉向，故 minor bump。

- **amendment 政策轉向：硬上限 → 無上限軟提醒**（SGC 版為準，回流）
  - `core/amendment.md`：§1.3 從「上限 2 次、第 3 次強制走 plan」改為「不設次數上限、第 3 次起每次顯示軟提醒（不阻擋、無確認門檻）」。守門改靠「範圍 / 性質」（§1.2：架構決策 / 跨模組 / 新依賴 / 新訪談 / 範圍過大）而非次數，信任使用者作為 amendment 層 reviewer（§1.1）
  - `commands/brief-amend.md`：「次數警告」段改「次數軟提醒」，0-1 次靜默、≥2 次（即將第 3 次起）顯示軟提醒後直接進 Step 1
  - `core/control-plane.md`：§Amendment 約束「次數軟限」行改為「無上限 + 3 次起軟提醒」
- **brief_stages 框架（整合測試 + user code review 歸檔前置 stage）**（去專案化回流）
  - `init/claude-md-template.md`：Brief 結束強制清單在 holistic_review 與 sessions 之間插入 `brief_stages.local_test`（actor=agent，role=integration-tester）+ `brief_stages.user_code_review`（actor=user），含 `_tree.yaml.nodes.{root}.brief_stages` schema、依 `pipeline.yaml.pipelines.{recipe}.brief_stages` 決定跑哪些（new_feature 預設含、bug_fix/planning_only 不含、無 harness/未定義則整段跳過）
- **新增 2 個通用角色**（SGC `.claude/agents` 去專案化回流）
  - `roles/architecture-reviewer.md`：advisory 架構健康度 reviewer（抽象洩漏 / 耦合內聚 / 深淺模組 / 對稱性 / 擴充性 / 資訊隱藏），兩插入點（plan_design / implementation_design），議案制不擋流程、blocker 交使用者仲裁。去專案化：`SGC_*` → `{repo}`、provider/mtg 範例 → 通用 driver/vendor、§7 改「Multi-Repo / worktree-disabled override」
  - `roles/integration-tester.md`：producer，依 plan [runtime] 條目跑黑盒整合測試（response 為主、log 為輔；不查 DB），含臨時 patch production code 的 §4.5 改→測→revert→驗證流程。去專案化：`SGC_LocalTest` → `{HARNESS}` harness 抽象、`fake_acewin`/具體 port/ENV/ArkGo protocol → 通用 fake_<provider> / mock_<provider>_<purpose> pattern + 「見 harness 文件」
- **interview tier 選項補 all-opus**（回流）
  - `init/interview.md`：Q4 Tier 偏好新增 `(e) all-opus`（全部 subagent 用 opus；top tier 模型見 models.yaml）
- 設計來源：SGC 部署實例（`D:\CodeSpace\SGC\.framework` 0.2.0 fork）的雙向同步盤點。SGC 端同步收 0.3.0 path-lint 硬規則 + 0.3.1 adversarial cap 3 + implementation-discipline skill + 三階段 dev-team recipe，升至 0.4.0
- 註：其他部署實例（tgbot 等）的 fork lib 未動，需另行回填

## 0.3.1 — 2026-05-27

Adversarial cap 2 → 3（cumulative）。動因：cap=2 在「checklist pass / adversarial fail」反覆的場景下太快觸頂——producer 只被打回 1 次重做就撞 `adversarial-deadlock` 升級，沒留足夠回合讓 producer 真正收斂 adversarial reviewer 指出的 gap。放寬到 3 多給一輪重做空間。純 deadlock 路徑最壞情況 producer 重做 3 次（< 5），故 producer cap=5 仍涵蓋；reviewer cap=4 / explore cap=2 不受影響。動到 lib 共 5 檔（純數值 / 文案，無機制變更）。

- **adversarial cap 2 → 3（cumulative）**
  - `core/review-loop.md`：§3.1 round 表 cap 欄 2→3；§3.2 觸發條件改 `rounds.adversarial >= 3`、迴圈防護場景改寫為 3 輪（adversarial round 3 fail 才升級）；§3.4 歷史軼事的硬編碼 `== 2` 泛述化為「撞 adversarial 上限」（避免日後再調 cap 時數字 drift）
  - `core/control-plane.md`：Cycle 語意段 cumulative 觸發 `>= 3`、footnote `adversarial 自有 cap=3`
  - `core/escalation-rules.md`：adversarial-deadlock 觸發條件 `>= 3`
  - `init/pipeline-yaml-template.md`：`second_review` 註解 `Adversarial cap = 3 cumulative rounds`
  - `recipes/dev-team.yaml`：description 成本警示 `adversarial cap=3`
- 未連動（已驗證無需改）：producer cap=5 / reviewer cap=4 / explore cap=2；各 role 的 §5.y adversarial 模式、`actor.adversarial` boolean 旗標、e2r-tree/typed-interfaces 範例 state 值（皆與 cap 無關）
- 設計來源：使用者直接調整（cap=2 實測太快觸頂、回合不足）

## 0.3.0 — 2026-05-22

機械性引用驗證硬規則（path-lint + main 自驗）。核心：把「引用既有檔路徑 / repo 前綴 / symbol 位置 / 數量」這類機械可驗的事實，從「靠 lessons 注入 + 自覺執行」升級為 producer / reviewer / main 三道強制機械閘門。動因：一次三層連環失守（plan repo 前綴錯、reviewer 數量誇大、main 盲轉），證明這類錯不該靠注意力擋——機械可驗的事該機械驗。動到 lib 共 5 檔（防線本體）；另統一框架版本聲明（見末條）。

- **planner 引用自驗硬步驟**
  - `roles/planner.md`：§4 執行流程新增第 6 步「引用路徑機械自驗（emit 前必跑）」——逐一 Glob 完整 `<repo>/<path>`、數量 / 否定式 claim grep 反證；§6 既有「引用 architecture.md/memory 必驗」鐵律強化為涵蓋 multi-repo repo 前綴（行號吻合 ≠ repo 吻合）+ 否定式反證
- **planning-reviewer 核對升級**
  - `roles/planning-reviewer.md`：§5「真實檔案存在」升級為「真實檔案存在 + 路徑精確」（驗 repo 前綴 + 行號）；新增「引用數量 / 否定式 claim 已反證」檢查項；§6 鐵律新增「evidence 數量 / 位置必機械確認」（不憑印象報數量）
- **main control plane 機械自驗（本次連環失守唯一缺的一道）**
  - `core/control-plane.md`：§4 Step 5 mv plan-draft → plan 前加 path-lint 機械閘門；§8 新增 §8.7（機械可驗 claim 不盲轉 + 定稿前 path-lint）、§8.8（狀態落地自驗 / 查空不單信 / Bash cwd 紀律 / phase self-check）。補強 main 作為唯一無 reviewer 角色的結構性缺口
- **reviewer evidence 數量精確**
  - `core/review-loop.md`：新增 §6.7「fail evidence 數量 / 位置須機械確認」，與 planning-reviewer §6、control-plane §8.7 三層呼應
- **init codex 種子**
  - `init/generator.md`：codex_template §3 已知陷阱加框架預設通用陷阱（引用既有檔 / multi-repo 同名檔 / 否定式 claim），未來 init 的 producer codex 天生帶這道防線
- **版本命名統一**：清掉源頭 repo 殘留的 `1.0.0-alpha.x` 舊命名（0.1.0 起已改走 0.X.0 SemVer，本次補齊聲明面）——`README.md`、`lib/design-summary.md` 文件頭、`commands/framework-status.md` 輸出範例、`design-summary.md` / `init/pipeline-yaml-template.md` / `init/generator.md` 的 pipeline `framework_version` 範例值、專案 MOC 一併對齊 `0.3.0`。註：部署實例（tgbot 等）的 fork lib 未動，需另行回填
- 設計來源：myvault 實作計畫 `framework-path-lint-引用驗證硬規則.md`（SGC brief `2026-05-22-game-runtime-status` escalation）

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
