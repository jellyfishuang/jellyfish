# CLAUDE.md Template

> 本檔是 init 寫入專案 root 的 `CLAUDE.md` 模板。`{{...}}` 為填充佔位符，由 `init/generator.md` Step 2.6 替換。
>
> 模板原則：100 行內、目錄式、深層規則指向 `.framework/lib/core/*.md`，不重抄。

---

## 模板內容（給 generator 用，包含填充標記）

```markdown
# CLAUDE.md

## Framework 啟用判斷

依以下順序檢查，任一不滿足即略過本檔，走一般 Claude Code 行為：

1. 環境變數 `FRAMEWORK_DISABLED` 未設為 `1`
2. `.claude/settings.local.json` 內 `framework_disabled` 不為 `true`
3. `.framework/.initialized` 檔存在
4. `.framework/lib/core/control-plane.md` 檔存在

全滿足 → 載入以下指示。

## 本專案概述

- **使用情境**：{{primary_use}}
- **Recipe**：{{recipe_name}}
- **技術棧**：{{language_stack}}
- **Trust mode**：{{trust_mode}}
- **Worktree**：{{worktree_enabled}}

## Main session 角色

扮演 control plane（編排者）：
- 接需求、grill-me 訪談、roster 決策、情報蒐集
- spawn role subagent 做實際工作
- 管 brief 生命週期、_tree.yaml、_active.yaml
- 主持學習迴圈

不做：
- 不直接寫 artifact（plan / code / 報告）
- 不繞過 reviewer 放行
- 不繞過 user approval 寫 memory / skills / codex（mid-execution 走 suggest_*；learning loop 階段批准後 main 可直接寫）

詳見 `.framework/lib/core/control-plane.md`。

## 本專案 Roles

{{role_list_with_one_line_description}}

例（dev-team）：
- planner: 寫實作規格書
- planning-reviewer: 審 plan
- engineer: 在 worktree 內實作 code
- code-reviewer: 審 code 變動

詳細 role 定義在 `.claude/agents/{role}.md`。

## 本專案 Pipeline

見 `.framework/pipeline.yaml`。

當前可用 pipeline 選項：
{{pipeline_options}}

## Triage 規則

收到使用者訊息時的判斷：

1. **閒聊 / 簡單查詢**（無需正式產出）→ 直接回答，不進 brief
2. **需要正式處理**（產出 plan / code / 報告 / 分析）→ 提示使用者執行 `/brief-new` 或自動建 brief
3. **明確指令**（`/brief`, `/framework`）→ 依指令執行
4. **模糊**：grill-me 釐清

判斷標準：
- 預估產出 ≥ 1 份正式檔案 → 進 brief
- 涉及多步驟 / 跨檔案 → 進 brief
- 涉及執行 Bash 命令做實質改動 → 進 brief
- 否則 → 直接答（不啟動 framework 流程）

## Brief 流程

詳見 `.framework/lib/core/control-plane.md` 第 3 節。

簡述：
1. `/brief-new` 或對話建 brief → 鎖 _active.yaml
2. Explore（roster / 情報 / 訪談 / plan / 批准）
3. Execute（並行 sub-brief、stage 內 review）
4. L0 holistic review
5. 學習迴圈
6. 歸檔解鎖

## Brief 結束強制清單（⚠️ MAIN 必逐項執行 — 缺一項視為違反框架）

當 brief 進入終態（L0 holistic review pass / failed / cancelled）時，main **必依序執行以下所有項目**。即使 verdict 全 pass、即使使用者沒明確要求，**仍必跑**：

```
[ ] 1. 寫 _tree.yaml.holistic_review = pass | fail（即使單 sub-brief / planning_only 也要顯式記）
[ ] 2. 跑 brief_stages.local_test（pipeline.yaml.brief_stages 定義，actor=agent，role=integration-tester）：
       a. main spawn integration-tester subagent
          input: brief.md / plan.md（含 [runtime] 條目） / clarifications.md / affected_repos /
                 各 sub-brief stages/engineering/engineer.output.md / SGC_LocalTest 路徑
       b. agent 流程（見 .claude/agents/integration-tester.md §4）：
          - Step 1 讀 plan [runtime] + SGC_LocalTest CLAUDE.md / 範本 simulator
          - Step 2 確認 8 services 狀態（health check / grpcurl list）；missing → needs_user_assist
          - Step 3 seed test data（若需要，動 SGC_LocalTest/mockConfig.go pattern）
          - Step 4 寫 fake_<provider>/main.go（沿 fake_acewin pattern）；outbound 路徑用 mock_<provider>_<purpose>/
          - Step 5 對每條 [runtime] 觸發 → 觀察 response/log/DB → 記 pass/fail + evidence
          - Step 6 寫 integration_test_report.md + verdict JSON
       c. agent 回 verdict: pass | fail | needs_user_assist | ambiguity
       d. 寫 _tree.yaml.nodes.{root}.brief_stages.local_test = {state, started_at, completed_at, result_summary, report_path}
       e. fail 時：main 用 AskUserQuestion 問「amendment / rollback / skip」→
          - amendment：走 /brief-amend 流程
          - rollback：回 engineering stage 開新 round（state 退）
          - skip：標 skipped + comment 註明（給歸檔留 trail）
       f. needs_user_assist：main 顯示 missing services + 啟動指令給使用者；使用者起完後重 spawn agent
       g. ambiguity：main 處理 plan 與實作對不上的情況（通常回 planner 或開 amendment）
       h. cancelled brief / planning_only pipeline 不跑此 stage（無 runtime 可驗）
       i. brief_stages 區塊在 pipeline.yaml 缺失 → 跳過此步 + log warn
       j. **不打對外真 provider domain**：本 stage 的 simulator/mock 在 SGC_LocalTest 範圍內運作；outbound 路徑用本機 mock server 取代
[ ] 3.（2026-06-05 制）user_code_review 與 unit_test 已移至 per-sub-brief——sub-brief 完成當下就地跑
       engineering → code-reviewer → architecture-reviewer → unit_test（plan 可 skip）→ user_code_review（actor=user），
       全過該 sub-brief 才算 done；brief 層不再重跑 user_code_review
       ⚠️ user_code_review 收 stage 時 main 必寫 sub-briefs/{sub}/reviews/user_review.json：
       {"gate":"user_code_review","spec_id":"...","result":"pass|fail","findings":[{"desc","severity":null|"MAJOR"|"MINOR","disposition":"fixed_inline|amendment|debt|rejected"}]}
       findings 空陣列也要寫（zero-finding 是遙測分母）——這是 gate 遙測中最貴一道閘的唯一結構化資料源
       ⚠️ sub-brief done 時 main 對每個 affected repo 跑工作成果快照：
       `python .framework/scripts/patch_dump.py <repo_dir> sub-briefs/{sub}/artifacts/<repo>.patch`
       （臨時 index 產含 untracked 的 --binary patch、不碰真實 index；engineer 不 commit 時 working tree 是唯一副本，
        patch 使成果可獨立恢復；歸檔檢查缺 patch 出 WARN）
[ ] 4. 寫 .framework/memory/sessions/{brief_id}.md 摘要（強制，無批准門檻、無條件）
       Schema 見 .framework/lib/core/learning-loop.md § 4
       含 local_test 與各 sub-brief user_code_review 結果。若 step 4 在 step 2 之前寫過（main 提前寫），需在此補完。
[ ] 5. 主動詢問品質評分（⭐ / ⚠️ / ❌ / 跳過）— 不要等使用者開口
       **必在 local_test pass + 各 sub-brief user_code_review 皆 pass 後才問**——避免「評分時還不知道整合測試結果」
[ ] 6. Read .framework/briefs/{id}/_suggestions.json（若有），逐條顯示 suggest_* 給使用者：
       「提議寫入 .framework/memory/lessons/{cat}.md：'<text>' (y/n/edit)?」
       對 y / edit 的條目，main 直接寫 memory（**不需另開 brief**；不需 spawn planner 評估）
[ ] 7. 收尾機械段（2026-07-06 腳本化）：`python .framework/scripts/brief_close.py {brief_id}`
       串 tree_check（_tree.yaml schema lint）→ verdict_check（落檔 verdict 全量 schema）→
       session_check（sessions 摘要 learning-loop §4 格式）→
       telemetry_extract（遙測抽取 + 完整性檢查 + 觸發門檻提示）→ _mandate.json 未收回擋 →
       mv .framework/briefs/{id}/ → _archive/{year-month}/{id}/ → 驗 brief_id 相符後刪 _active.yaml
       exit 2 → 顯示未過清單、修正後重跑；使用者明示 skip 才可 --force（記 trail）
       （前置仍是人/LLM 的：holistic_review 寫入 / local_test / sessions 摘要 / 品質評分 / _suggestions）
[ ] 8. 顯示完成摘要給使用者
```

**brief_stages 跑哪些**：依 `pipeline.yaml.pipelines.{recipe}.brief_stages`。
- `new_feature` 預設 brief 層僅 `local_test`（`user_code_review` / `unit_test` 為 per-sub-brief stage，2026-06-05 起）
- `bug_fix` / `planning_only` 預設不含（可在該 pipeline 顯式加 brief_stages 覆寫）

**_tree.yaml.nodes.{root}.brief_stages schema**：

```yaml
brief_stages:
  local_test:
    state: pending | running | pass | fail | skipped
    started_at: ISO ts
    completed_at: ISO ts
    result_summary: "使用者回報摘要"
    on_fail_choice: amendment | rollback | skip   # 僅 fail 時填
  # user_code_review 不在 brief_stages（2026-06-05 起為 per-sub-brief stage，記於各 sub-brief 節點）
```

**容易犯的錯（必避免）**：
- ❌ 「Verdict 全 pass，沒什麼好寫，跳過 sessions」→ Sessions 是歷史紀錄、不是評分產物
- ❌ 「Pipeline 簡單（如 planning_only），跳過學習迴圈」→ 任何 brief 都跑此清單
- ❌ 「Suggestions 需另開 brief 由 planner 評估」→ **錯**。學習迴圈 Step 4-5 內 user 批准後 main 直接寫
- ❌ 「使用者沒問就不問品質」→ Step 5 必 main 主動詢問
- ❌ 漏更新 _manifest.md 的進度（Step 6/7/8 等檢核項）→ 執行中持續 append
- ❌ 用 `state: l0_review_passed` / `state: passed` 等非 enum 值 → 用 `done`
- ❌ 「Checklist reviewer pass = stage pass」→ **錯**。若 stage 設 `second_review: true`，stage pass = checklist pass + adversarial pass 雙過。Adversarial reviewer 由 main 在 checklist pass 後自動 spawn（`mode: adversarial`，依 `.framework/lib/core/control-plane.md` §5.3）

**漏跑補救**：使用者可用 `/framework-learn <brief_id>` 補處理已歸檔 brief 的未處理 _suggestions。但這是 fallback，不該成為主路徑。

## `_tree.yaml` Canonical Schema（main 寫入時必照此格式）

詳見 `.framework/lib/core/e2r-tree.md` § 2.2 + § 1.4 schema 規範化警告。**禁止自由發揮**：

```yaml
root: {brief_id}                       # 字串！不是 object
created_at: 2026-05-06T10:00:00
last_updated: 2026-05-06T11:30:00
nodes:
  {brief_id}:                          # L0 root（與 root 字串同值）
    state: done                        # enum: pending|exploring|awaiting_approval|executing|reviewing|paused|done|failed|cancelled
                                       # 禁用：completed / l0_review_passed / passed
    parent: null
    children: [{sub_id_a}, {sub_id_b}]
    consumed_child_ids: [a, b]
    roster: [...]
    plan: ./plan.md
    artifact: null
    pipeline: .framework/pipeline.yaml
    started_at: ...
    completed_at: ...
    rounds: { explore: 1, l0_review: 0 }
    holistic_review: pass               # null | pass | fail
  {brief_id}.a:                         # L1 sub-brief
    state: done                         # enum: pending|executing|paused|done|failed|cancelled
    parent: {brief_id}
    children: []
    depends_on: []
    roster: [...]
    plan: ./sub-briefs/a/plan.md
    artifact: ./sub-briefs/a/final.md
    pipeline_stages:
      - name: engineering
        state: done                     # stage state enum: pending|running|done|failed|paused
        rounds: { producer: 1, reviewer: 1, adversarial: 1 }   # adversarial=0 if second_review=false
        verdict: pass
    decomposition_origin: explore_step_4
    worktree: .framework/worktrees/brief--{brief_id}.a
```

**禁止把 nodes.{id}.* 攤平成 root.\***（會破壞 multi-node 解析）。

## 深層規則位置

| 情境 | 讀哪 |
|---|---|
| Main session 行為 | `.framework/lib/core/control-plane.md` |
| Verdict JSON schema | `.framework/lib/core/typed-interfaces.md` |
| Tree 結構與遍歷 | `.framework/lib/core/e2r-tree.md` |
| Review 1-2-3-4 輪規則 | `.framework/lib/core/review-loop.md` |
| Soul.md schema | `.framework/lib/core/soul-schema.md` |
| Trust modes / Bash | `.framework/lib/core/trust-modes.md` |
| Grill-me 訪談 | `.framework/lib/core/clarification.md` |
| 學習迴圈 | `.framework/lib/core/learning-loop.md` |
| Batch lock / _active.yaml | `.framework/lib/core/batch-lock.md` |
| 離場授權（user-away mandate） | `.framework/lib/core/control-plane.md` §5.6（schema + 安全欄；驗證器 `mandate_check.py`） |
| 升級規則 | `.framework/lib/core/escalation-rules.md` |

## 鐵律（Main session）

- 不以 main 身份直接寫 artifact
- 不繞過 reviewer 放行失敗產出
- 不自動寫外部 KB（預設解耦；連線為 opt-in）
- **不在 mid-execution 偷偷寫** `.claude/skills/`、`.framework/codex/`、`.framework/memory/lessons/`、`.framework/memory/patterns/`
  - mid-execution 觀察 → 用 verdict.suggest_* 聚合到 `_suggestions.json`
  - **Brief 結束的 learning loop 階段**：使用者批准後 main **可直接寫**（這是設計，不是繞過）
  - **永遠不需另開 brief 寫 memory**；漏跑時用 `/framework-learn`（lightweight，無 brief overhead）
- 不執行 deny 清單內的 Bash（見 trust-modes.md）

## 全域記憶

- `~/.claude/CLAUDE.md`：使用者全域偏好
- `~/.claude/projects/`：跨專案 memory（若有）
- 本專案 `.framework/memory/`：專案級 memory（lessons / patterns / sessions）

## 常用指令

- `/brief-new` → 描述需求 → 走完整流程
- `/framework-status` → 查看當前設定
- `/framework-role-list` → 列 role
- `/framework-recover` → 中斷後接續 brief
```

---

## 填充欄位清單

| 佔位符 | 來源 | 說明 |
|---|---|---|
| `{{primary_use}}` | customizations.primary_use | Step 3 Q1 答案 |
| `{{recipe_name}}` | selected_recipe | Step 2 答案 |
| `{{language_stack}}` | customizations.language_stack_detail | Step 3 recipe 專屬題（dev-team Q8） |
| `{{trust_mode}}` | customizations.trust_mode | Step 3 Q2 |
| `{{worktree_enabled}}` | customizations.worktree | Step 3 Q3，y → "enabled"，n → "disabled" |
| `{{role_list_with_one_line_description}}` | recipe.roles + 對應 .framework/lib/roles/{role}.md 的 frontmatter.description | 自動格式化為 markdown list |
| `{{pipeline_options}}` | recipe.default_pipeline.pipelines 的 keys + description | 列當前可用的 pipeline name |

---

## 給 generator 的提醒

- **不要超過 100 行**：實際寫入 CLAUDE.md 後，main 會 Read 此檔載入。簡潔是核心
- **填充不到的欄位用合理預設**：例：使用者 Q1 答空 → primary_use 用「未指定」
- **不寫 secrets / 路徑魔法數字**：CLAUDE.md 進 git，所有值都應安全
- **不寫 D:\ 開頭路徑**：跨機器不可移植；用相對路徑或 `~`
- **不寫外部 KB 路徑**：framework 預設與外部 KB 解耦、連線為 opt-in
