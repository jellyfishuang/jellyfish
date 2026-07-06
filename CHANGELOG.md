# Framework CHANGELOG

記錄 framework lib（`D:\Claude\.framework\lib`）的版本演變。版號採 SemVer，對應日後的 git tag。
版號真實來源＝`lib/VERSION`；各 repo 複製時以該檔為準。

## 0.11.0 — 2026-07-06

User-away mandate 結構化（離場授權）。動因：使用者離場授權原以散文寫在 `_active.yaml.autonomous_mandate`（2026-07-02 部署實例），接手 session 靠讀 prose 理解邊界、無機械可解析性、無安全欄。新機制主題，minor bump。

- **`_mandate.json`**（briefs/{id}/ 下，仿 `_suggestions.json` 前例）：結構化 schema——`auto_advance`（sub-brief / stage 白名單 + max_review_rounds）、`pre_authorized`（人審關卡逐項預授權，`as` 限 `pass`、`condition` 必填補救路徑）、`do_not_start`（明示不開 + 原因，防接手誤判遺漏）、`on_stop`（停下時的報告產出）；`_active.yaml.autonomous_mandate` 降為指針值，禁散文
- **不可豁免安全欄**（control-plane §5.6.3，mandate 寫什麼都無效）：HOLD 條件（blocker / 真 ambiguity / 設計取捨）永遠生效；git commit/push、memory|codex|skills 寫入、歸檔、品質評分、cancel 永不可預授權；人審 stage 不可進 auto_advance（只能逐項 pre_authorized）
- **`lib/scripts/mandate_check.py`**：寫入 / recover 時機械驗證（欄位枚舉 / 節點存在 / as+condition / rounds cap 只可降 / auto 與 do_not_start 交集 / 人審關卡入 stages 直接擋）；9 測試全綠
- **接線**：control-plane 新 §5.6（載體流程 / schema / 安全欄）；batch-lock §2 schema + 寫入時機；framework-recover step 2.5（驗 mandate → active 問「續跑 / 收回」、壞結構降互動模式、舊制散文唸給使用者建議轉簽）；claude-md-template 深層規則表
- 設計來源：SGC 部署實例 2026-07-02 散文 mandate 教訓；外部模型審視「八點建議」#6

## 0.10.1 — 2026-07-06

遙測判讀觸發機械化。動因：報表判讀原靠「memory 載入提醒 + 人記得」——提示紀律非機械閘。補完：`telemetry_extract.py` 每次歸檔跑完抽取後自動印「遙測觸發狀態: live briefs N/{門檻} | draft 樣本 M/{門檻}」，達門檻印 `>>> 已達判讀門檻 … 依 memory/experiments/ runbook 執行`。門檻為 script 頂部常數（LIVE_READ_TRIGGER=10 / DRAFT_TRIAL_TRIGGER=3）。telemetry_tests 增至 17（+觸發狀態行×2）。無新機制主題，patch bump。

## 0.10.0 — 2026-07-06

訪談改制：Draft+Redline 理解草稿（預設）。動因：訪談歷史 8-22 輪且使用者多數答「採推薦」——多數題目是確認非決策，單題制把使用者注意力花在儀式上；gate 遙測 baseline 另示 planning-reviewer fail 率 45%（plan 初稿品質是最大返工源，訪談品質是其直接上游）。新模式主題，minor bump。

- **clarification.md §2.5**：main 出理解草稿（需求摘要 + scope 邊界 + 假設表 + 真分岔題捆包）→ 使用者紅筆一次收斂（對話回覆或直接改檔由 main diff）。未知數分類：可假設（推薦 + typed 依據 + 影響局部）進表不問；真分岔（架構 / 跨 repo / 不可逆 / 偏好推不出）用既有 §3 題目格式隨附
- **假設表**：ID / 假設 / 依據（`intel:`/`codex:`/`memory:`/`推測` typed）/ 若錯影響 / 級。**兩級沉默契約（使用者親訂）**：⚠ 級（推測+非局部、跨 sub-brief、不可逆）沉默不算數、必明確 ack；「—」級未劃掉視為接受——復用 design_sketch ack_required 同構，不違 §11.3 精神（該條防模型把模糊當同意）
- **防橡皮圖章**：假設 > 15 條＝intel 太薄回補情報（不把不確定性倒給使用者）；紅筆 3 輪未收斂降回逐題；真分岔計 cap 20、假設不計；再入口（sub-brief 升級 / plan fail 補訪談）走 delta 草稿不重入串行
- **接線**：control-plane Step 3 改寫 + 訪談者職責；brief-new；planner 鐵律「假設表已裁決項不得重問、新不確定點以假設格式回供 delta 紅筆」；learning-loop sessions frontmatter 加 `draft_cycles` / `fork_count`
- **試跑判讀（manual validation gate）**：2-3 brief 對照 `clarification_rounds_used` 歷史中位數 8-22 與 planning-reviewer R1 fail 率 45% 雙指標，數據決定去留；逐題 grill-me 降為 fallback 保留（§10 分 10.1/10.2 兩格式）
- 設計來源：SGC 部署實例；外部模型審視「八點建議」#3，三決策點（模式定位 / 沉默契約 / 載體）經使用者逐一拍板

## 0.9.0 — 2026-07-06

工作成果快照（patch dump）。動因：engineer 不 commit（使用者親管 git），sub-brief 完成後成果只存在 uncommitted working tree——唯一副本，errant checkout / 平行 sub-brief 誤動 / 測試臨時 patch revert 意外即滅失；user review 對象也隨 tree 漂移。新耐久化機制主題，minor bump。

- **`lib/scripts/patch_dump.py`**：臨時 index（GIT_INDEX_FILE）read-tree HEAD → add -A → diff --binary --cached——產含 untracked 新檔（尊重 .gitignore）+ binary 內容的完整可 apply patch；**不碰真實 index / stage / working tree**；無變更寫空檔（供存在性檢查）
- **收尾接線**（claude-md-template step 3）：sub-brief done 時 main 對每個 affected repo dump 至 `sub-briefs/{sub}/artifacts/<repo>.patch`；兼作 user_code_review 穩定審查快照
- **`telemetry_extract.py`**：完整性檢查加 code sub-brief 缺 `artifacts/*.patch` → WARN（過渡期不擋，避免對既有 in-flight brief 誤傷；穩定後可升 exit 2）
- **`lib/scripts/patch_dump_tests.py`**：12 檢查（tracked 改/刪 / untracked 巢狀 / binary / ignored 排除 / 真實 index 零改變 / clean clone apply 還原一致 / 空變更 / 非 repo）；telemetry_tests 增至 15（+缺 patch WARN×2）；測試子行程統一 `PYTHONIOENCODING=utf-8`（Windows cp950 console 斷言修正）
- 設計來源：SGC 部署實例首跑即攔到真實敞口（active brief 待審 sub-brief 有 8 檔未 commit 變更，dump 後 reverse-apply 驗證精確）；外部模型審視「八點建議」#4

## 0.8.0 — 2026-07-06

Gate 遙測（流程有效性量測）。動因：框架品質閘豐富（一個 code sub-brief 從 plan 到收尾 6–8 道）但零流程數據——哪道閘攔到多少唯一真缺陷、哪道只在燒輪次，無從得知；砍閘靠感覺、加閘沒煞車。同批修正 verdict 落檔矛盾：§2 表寫「subagent 寫 verdict」但 reviewer 無 Write 工具、§6.3 又要 main 落檔——兩規則打架的結果是誰都沒寫（SGC 20 個歸檔 brief 僅 2 個留 verdict 檔）。新遙測機制主題，minor bump。

- **verdict 落檔規則收斂**（control-plane §2 表 + §6.3）：main 收驗後**原樣落檔**（記錄非創作，不違反「main 不寫 artifact」）；brief 層路徑 `{root}/reviews/{role}.verdict.json`、多輪 `.round{N}`
- **user_review.json**（claude-md-template step 3）：user_code_review 收 stage 時 main 必寫 result + findings（disposition: fixed_inline|amendment|debt|rejected），**零 findings 也寫**（遙測分母）——最貴一道閘的唯一結構化資料源
- **`lib/scripts/telemetry_extract.py`**：歸檔前跑；抽 reviews/*.verdict.json + user_review.json → append `memory/telemetry/gate_runs.jsonl`（同 brief 重跑冪等）；完整性檢查（code sub-brief 缺 code-reviewer verdict / user_review、root 有 plan.md 缺 planning verdict → exit 2 擋歸檔；--force 降警告記 trail）
- **`lib/scripts/telemetry_report.py`**：per-gate 統計（runs / fail 率 / findings 密度 / zero-finding 率 / severity / disposition / live-retro 來源分列）；判讀提示：密度低 + zero 率高 + severity 輕 → 候選改條件式閘
- **`lib/scripts/telemetry_tests.py`**：13 檢查（抽取 / 冪等 / 缺檔 exit 2 / --force / --check-only / 報表）；歸檔 step 7 改兩段（先遙測後搬移）
- 設計來源：SGC 部署實例；使用者採納外部模型審視「八點建議」#2——gate 遙測先行，數據指導後續流程減法（#1 stage 審計 / #5 鐵律 gate 化的前提）

## 0.7.1 — 2026-07-06

機械閘部署鏈指令化（`/framework-hooks-sync`）。動因：0.7.0 部署流程只記在 `lib/hooks/README.md`（手動複製 + 手動合併 settings.json），init 未接；手動合併 JSON 正是「確定性慣例靠機械閘非 LLM 自律」要消滅的操作。補完 0.7.0 部署鏈、無新閘門主題，patch bump。

- **`lib/scripts/hooks_sync.py`**：確定性部署 script——`lib/hooks|scripts/*.py` → `.framework/hooks|scripts/`（byte 相同不重寫）、渲染 `hooks-config.template.json`（`{PYTHON}` / `{PROJECT_ROOT}`）、合併 `.claude/settings.json`（command 含 `.framework/hooks/` 的條目＝framework-managed 整組替換、使用者自加 hook 原樣保留、`_framework_managed_hooks` 鏡像同步）；settings.json 非合法 JSON 拒寫 exit 1（不 fail-open）；尾跑 62-case gate 回歸
- **`lib/commands/framework-hooks-sync.md`**：command 薄包裝（`--dry` / `--no-test`）；main 只轉述 script 輸出，不手動編輯 hooks 區塊
- **`lib/scripts/hooks_sync_tests.py`**：hooks_sync 生命週期測試（fake root：fresh / idempotent / user hook 保留 / 壞 JSON 拒寫 / dry-run，15 檢查）；改 hooks_sync.py 後必跑
- **`framework-init.md`** 新增步驟 6「部署機械閘」；`lib/hooks/README.md` 部署段改指向指令 + 補測試入口
- 設計來源：SGC 部署實例（真實 root 實跑 SYNC OK、兩測試套件全綠）指令化後去專案化回流

## 0.7.0 — 2026-07-03

機械閘落地（hooks + scope gate）+ 外部審計修正回流。動因：SGC 部署實例做一次性外部審計（76 findings：文件 vs 實作矛盾 / 宣稱自動檢查但無機制在跑），確認框架所有「機械閘門 / BLOCKING」宣稱過去零 hook 零 script 兜底、純靠 LLM 自律，與「確定性慣例靠機械閘非 LLM 自律」原則相反。補上真實機制 + 同批文件矛盾修正。新增 `lib/hooks/` 與 `lib/scripts/` 兩個內容類別，屬新機制主題，minor bump。

- **Claude Code hooks 三閘**（`lib/hooks/`，SGC 實戰經三輪對抗式驗證 pass 後去專案化回流）
  - `bash_gate.py`（PreToolUse/Bash）：`docker rm/rmi/prune`（子指令位置判定）、`compose down -v` → deny；`compose down`、`git commit/push` → ask。比對前剝除引號/heredoc/跳脫序列、換行視同指令分隔、docker-compose 正規化、大小寫不敏感
  - `path_gate.py`（PreToolUse/Write|Edit）：寫 `.framework/memory|codex`、`.claude/skills` → ask（`memory/sessions/` 例外——brief 收尾強制寫）；normpath + cwd join 防 `../`/雙斜線/相對路徑繞過。learning loop 合法寫入時權限提示本身即為批准點，免維護狀態檔
  - `fullwidth_gate.py`（PostToolUse/Write|Edit）：`.go` 註解全形標點寫檔當下攔截回饋行號（剝 string/rune literal 後殘留必在註解，免解析註解結構；rune 用精確單字元文法防撇號假配對）
  - 設計原則：deny 只給確定錯的、不確定一律 ask（不讓 agent 卡死空轉）；gate 內部錯誤 fail-open + 記 gate.log；hooks 對 subagent 工具呼叫同樣生效
  - 部署模式：init/sync 複製 `*.py` → `.framework/hooks/`，hooks 區塊依 `hooks-config.template.json` 寫 `.claude/settings.json`（`_framework_managed_hooks` 鏡像供漂移比對）；62-case `run_tests.py` 回歸（改 gate 必跑）
- **scope gate**（`lib/scripts/scope_check.py`）：multi-repo repo 級越界 / go.mod 偷升機械閘。三模式：無參數（讀 `_active.yaml` 解析 affected_repos 聯集，容忍粗體 markdown 格式）/ `--repos`（sub-brief 白名單）/ `--overlap`（batch-lock 開 brief 前重疊檢查）。exit 2=違規、1=用法錯誤（空參數拒 fail-open）。diff 基準 working tree vs HEAD（engineer 不 commit，`main...HEAD` 恆空=檢查空轉，SGC 實戰 4 次 lesson 的根因收斂）。repo 前綴 `PREFIX` 常數落地時調整
- **審計修正**：
  - 全 21 個 command 檔 frontmatter `allowed_tools` → `allowed-tools`（舊 key 無效 = 工具限制從未生效，含 framework-recall 宣稱的唯讀）
  - `core/e2r-tree.md` amendment「≥3 直接拒絕」→ 無上限 + 軟提醒（對齊 amendment.md §1.3 既定政策）
  - `init/claude-md-template.md` forward-port per-sub-brief review 制（brief 層只剩 local_test；step 3/4/5 + schema + 交叉引用同步）
  - `core/batch-lock.md` §2.2 建 brief 前 `--overlap` 重疊機械閘（防平行/殘留互蓋）
  - `commands/framework-status.md` 版本範例改「以 lib/VERSION 為準」；`framework-recipe-list.md` 範例改實況（1 recipe）
  - review skills ×2 補 worktree-disabled override 引言（diff HEAD 基準 + `??` untracked——engineer 不 stage 時新檔全盲是對抗驗證抓到的兩道閘共同盲區）
- 設計來源：SGC 外部審計（2026-07-03，76 findings 逐條裁決）；hooks 三輪、scope gate 二輪對抗式 agent 驗證全 pass 後回流

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
