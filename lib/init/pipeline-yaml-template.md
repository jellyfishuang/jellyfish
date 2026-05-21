# Pipeline.yaml Template

> 本檔規範 init 寫入專案 root 的 `.framework/pipeline.yaml` 模板與其完整 schema。
>
> Pipeline.yaml 是「本專案的 stage DAG 定義」，main session 在 Execute 階段依此排程 role spawn。

---

## 1. 完整 Schema

```yaml
# .framework/pipeline.yaml

# 此檔案的 framework version（與 .framework/lib/VERSION 一致；framework 升級時 init 重生時更新）
framework_version: "1.0.0"

# 此 recipe 的 pipeline 集合
# Key 是 pipeline 名稱（main 在 Explore 階段選擇要走哪條）
pipelines:

  <pipeline_name>:
    description: <一句話描述>

    # Stages 是 DAG，main 依 depends_on 排程
    stages:
      <stage_name>:
        role: <producer role name>
        reviewer: <reviewer role name 或 null>
        depends_on: [<其他 stage_name>, ...]
        # 可選：覆寫 review rounds
        review_rounds:
          same_role_max: 2       # cumulative reviewer rounds 觸發回 Explore
          total_max: 4           # cumulative 強制升級
          explore_max: 2         # explore 上限
        # 可選：對抗式 second-pass 審核
        second_review: false     # true = checklist reviewer pass 後自動再 spawn 一次 reviewer with mode=adversarial（fresh 視角）
                                 #        雙過才算 stage pass；**per-stage 2x reviewer cost**（多 stage 全開 → 累計 N×2x）
                                 #        Adversarial cap = 2 cumulative rounds（review-loop §3.2，避免無窮迴圈）
                                 #        適合：高品質要求、code/plan 易被 producer self-narrative 框住
                                 # false（預設）= 單 pass。**注意：reviewer.md §5.x 對抗式視角仍會跑**——
                                 #        single-pass 已含一個 reviewer 內的對抗式檢查；second_review 只是再加 fresh 視角的第二人 review
        # 可選：此 stage 額外載入 skill（疊加 role frontmatter 的 skills）
        skills_extra: []
        # 可選：此 stage 是否需要 worktree（覆寫 role.worktree）
        worktree: inherit       # inherit | required | forbidden

# 預設使用的 pipeline（若 brief 沒指定，main 用這條）
default: <pipeline_name>

# 全域 review rounds 覆寫（per-pipeline 可再覆寫）
review_rounds_override: null    # null = 用 framework default

# Bash 額外白名單（與 .framework/.initialized 的 bash_extra_allow 合併）
bash_extra_allow: []

# 此 .framework/pipeline.yaml 適用的 brief 偵測 hint（main triage 時參考）
triage_hints:
  match_keywords: []             # brief 含這些關鍵字 → 偏向用此檔
  match_recipes: []              # 此 pipeline 由這個 recipe 產生（紀錄用）
```

---

## 2. dev-team 預設範例

```yaml
framework_version: "1.0.0"

pipelines:
  new_feature:
    description: 新功能開發（規劃 + 實作）
    stages:
      planning:
        role: planner
        reviewer: planning-reviewer
        depends_on: []
      engineering:
        role: engineer
        reviewer: code-reviewer
        depends_on: [planning]

  bug_fix:
    description: 修 bug（直接實作，無正式規劃）
    stages:
      engineering:
        role: engineer
        reviewer: code-reviewer
        depends_on: []

  planning_only:
    description: 只規劃不實作
    stages:
      planning:
        role: planner
        reviewer: planning-reviewer
        depends_on: []

default: new_feature

review_rounds_override: null

bash_extra_allow:
  - go test ./...
  - go vet ./...
  - go build
  - git diff
  - git log --oneline
  - git show

triage_hints:
  match_keywords: []
  match_recipes: [dev-team]
```

---

## 3. finance-advisory 範例（多 stage 範本）

```yaml
framework_version: "1.0.0"

pipelines:
  full_advisory:
    description: 完整顧問流程（research → analysis → writing）
    stages:
      research:
        role: researcher
        reviewer: source-quality-reviewer
        depends_on: []
        skills_extra: [source-evaluation]
      analysis:
        role: financial-analyst
        reviewer: reasoning-reviewer
        depends_on: [research]
        skills_extra: [dcf-valuation, scenario-analysis]
      writing:
        role: writer
        reviewer: editor
        depends_on: [analysis]
        skills_extra: [technical-writing-style]

  quick_lookup:
    description: 快速查詢（main 直接 WebFetch 回答，不進完整流程）
    stages: {}    # 空 → main 直接處理

default: full_advisory

review_rounds_override: null

bash_extra_allow: []

triage_hints:
  match_keywords: [investment, financial, stock, valuation]
  match_recipes: [finance-advisory]
```

---

## 4. Schema 驗證

`/framework-init` 與 `/framework-pipeline-edit` 寫檔前必驗證：

| 欄位 | 規則 |
|---|---|
| `framework_version` | 必填，semver 格式 |
| `pipelines` | 至少一個 pipeline |
| `pipelines.<name>.stages` | 可空（例 quick_lookup）；若非空，每 stage 必有 role |
| `pipelines.<name>.stages.<s>.role` | 對應 `.claude/agents/{role}.md` 必存在 |
| `pipelines.<name>.stages.<s>.reviewer` | 若非 null，對應 role 必存在 |
| `pipelines.<name>.stages.<s>.depends_on` | 必為已存在的 stage name；無循環依賴 |
| `default` | 對應 `pipelines` 的 key |
| `review_rounds.same_role_max` | 1-5 整數 |
| `review_rounds.total_max` | ≥ same_role_max |
| `review_rounds.explore_max` | 1-3 整數 |
| `bash_extra_allow` | 字串陣列；不含 deny 清單項目 |

驗證失敗 → init 拒寫，提示具體錯誤。

---

## 5. Pipeline 與 Brief 的關係

- Brief 在 Explore 階段，main 從 plan 推測該用哪條 pipeline：
  - 使用者在 brief.md 明確指定（例：「用 bug_fix」）→ 用該條
  - 未指定 → main 看 brief 內容比對 `triage_hints` → 選 best match
  - 都不匹配 → 用 `default`
- 一個 brief 用一條 pipeline；不混用
- Sub-brief 預設繼承 parent 的 pipeline；可在 plan.sub_briefs 個別指定

---

## 6. Stage DAG 解讀

```yaml
stages:
  research:
    depends_on: []
  analysis:
    depends_on: [research]
  writing:
    depends_on: [analysis]
```

對應 DAG：
```
research → analysis → writing
```

並行範例：

```yaml
stages:
  research_a:
    depends_on: []
  research_b:
    depends_on: []
  analysis:
    depends_on: [research_a, research_b]
```

```
research_a ─┐
            ├──→ analysis
research_b ─┘
```

Main 排程時：
1. 找 depends_on 全 done 的 stage
2. 同訊息並行 spawn（依 design-summary 第 7d 規則）
3. 收 verdict 後重排

---

## 7. 給接手 agent 的提醒

- **Stage name 是 pipeline 內唯一識別**：不同 pipeline 可重用 name
- **role / reviewer 引用必為已 init 的 role**：init 後加 role 時要檢查 .framework/pipeline.yaml 是否需更新
- **depends_on 循環是嚴重錯誤**：init 必驗，使用者手改後 main 啟動時也再驗
- **空 pipeline（stages: {}）合法**：表示 main 直接處理，不 spawn role（如 quick_lookup）
- **不在 .framework/pipeline.yaml 內存 model tier**：tier 在 `.claude/agents/{role}.md` frontmatter；pipeline 不重抄
- **此模板由 generator.md 填入**：佔位符在第 8 節
