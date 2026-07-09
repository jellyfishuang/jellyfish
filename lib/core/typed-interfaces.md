# Typed Interfaces — Verdict / Producer Output JSON Schema

> 本文件規範 Producer 與 Reviewer 結束時 emit 的 verdict JSON 格式。Main session 解析此 JSON 決定下一步動作（進下一 stage、retry、回 Explore、升級使用者等）。
>
> 對應 OMC（arXiv:2604.22446）論文的 **Typed Organizational Interfaces** 概念——抽象協定統管 agent 間溝通。

---

## 1. 設計原則

1. **統一寬鬆 schema**：Producer 與 Reviewer 共用一份 schema，由 `actor.type` 與 `verdict` 區分子集（不做 7 個獨立 schema）
2. **Verdict 必填欄位嚴格、選填欄位按 verdict 啟用**：解析方根據 verdict 取對應欄位
3. **JSON 純機器讀**：人類摘要塞進 `summary` 欄位，main 顯示時格式化（取代 v3 的 Handoff Block）
4. **Schema version 由 framework version 統管**：不在 JSON 內版本化（避免每筆 verdict 都重複版本字串）

---

## 2. Verdict Types

### 2.1 七個 verdict

| Verdict | 語意 | 觸發者 | Main 處理 |
|---|---|---|---|
| `pass` | 機械檢查全過 | reviewer | 進下一 stage |
| `fail` | 機械檢查不過 | reviewer | review-loop.md：1-2 輪同 role / 3+ 回 Explore |
| `ambiguity` | 缺資訊無法繼續 | producer / reviewer | 自行補 / 升級 L0 / 累積升級 |
| `needs_decomposition` | 任務太大 | producer | Main 判斷是否拆 sub-brief |
| `needs_dependency` | 需新依賴 | producer | 升級使用者裝 |
| `tool_error` | 工具或前置環境壞（檢查工具失效 / role 前置條件不成立） | producer / reviewer | 升級使用者修 |
| `partial` | 部分完成 | producer | Main 判斷接受或要求補完 |

### 2.2 Verdict 與 actor.type 對應

| Actor type | 可用 verdicts |
|---|---|
| `producer` | `pass`, `partial`, `ambiguity`, `needs_decomposition`, `needs_dependency`, `tool_error` |
| `reviewer` | `pass`, `fail`, `ambiguity`, `tool_error` |

不在上表的組合 → main 拒收，視為 schema 違規（轉 `tool_error` 處理：role 寫錯 verdict）。**例外**：`actor.advisory: true` 的 verdict 不套本表，走 §2.3 advisory 分支。

> **2026-07-09 變更**：`tool_error` 開放給 producer。動機：engineer / test-writer / integration-tester 的 role md 前置閘（§3 prerequisite gate）慣例上以 `tool_error` 回報「前置條件不成立」（worktree 衝突、必要檔缺失、Bash 不可用等），原表僅 reviewer 可用會使這些 verdict 被機械驗證拒收。producer 的 `tool_error` 同樣必附 `tool_error_details`（§3.3），且 `artifact` 可為 null（§3.2）。

### 2.3 Advisory verdict（architecture-reviewer 專用例外）

architecture-reviewer 是**議案制 advisory** role，不回 pass/fail、不卡輪數，故不用上述 7 枚舉。判別開關是 **`actor.advisory: true`**——出現此鍵時整份 verdict 改按本節驗：

| 項目 | 規則 |
|---|---|
| `verdict` | enum：`clean`（無 finding）\| `findings`（有 finding） |
| `actor` | 必填 `role` / `spec_id` / `stage` / `round`（int）；建議附 `type: reviewer` 與 `adversarial: false` |
| `summary` | 必填；**免 200 字上限 WARN**（無 finding 時須說明三個未來測試怎麼看的，天然較長） |
| `findings[]` | `verdict=findings` 時 ≥1、`clean` 時必為空。每項必填七欄：`severity`（`blocker`\|`advisory`）/ `dimension` / `finding` / `why_it_hurts_future` / `suggested_direction` / `evidence` / `spec_checked` |
| `design_sketch` | **每次必附**（與 verdict 健康度無關）。必填八欄：`focus` / `change` / `shape` / `reuse_vs_new` / `overlaps_existing` / `pattern_divergence` / `key_tradeoffs` / `ack_required`（**bool**；字串 `"true"`/`"false"` 驗證器寬收） |

欄位語意與範例見 `.claude/agents/architecture-reviewer.md` §6 / §6.1（role md 與 `verdict_check.py` 為此契約的雙方，本節為權威收錄）。

> ⚠️ **`advisory` ≠ `adversarial`**：兩鍵近音但語意完全不同。`actor.advisory: true` 是 architecture-reviewer 的 schema 分流開關；`actor.adversarial: true` 是一般 reviewer 的對抗式二審標記（§3.2）。誤把 `advisory` 打成 `adversarial` 會讓 `clean|findings` 掉進 7 枚舉驗證被判非法。

---

## 3. JSON Schema（完整）

> 機械驗證：`python .framework/scripts/verdict_check.py <verdict.json | brief_dir>`（本節全部規則；main 收 verdict 落檔後跑，取代目測——control-plane §6.3）。

### 3.1 結構

```json
{
  "verdict": "pass | fail | ambiguity | needs_decomposition | needs_dependency | tool_error | partial",
  "actor": {
    "role": "code-reviewer",
    "type": "producer | reviewer",
    "spec_id": "2026-05-06-slot-revenue-q2.a",
    "round": 1,
    "stage": "analysis",
    "adversarial": false
  },
  "summary": "<一句話摘要，main 顯示給使用者>",
  "artifact": "<artifact 路徑或 null>",
  "checks": [
    {
      "name": "tests",
      "result": "pass | fail | skipped",
      "evidence": "<具體輸出片段或路徑>"
    }
  ],
  "questions": [
    {"id": "q1", "text": "...", "severity": "blocking | non-blocking"}
  ],
  "decomposition_proposal": {
    "rationale": "...",
    "sub_briefs": [
      {"title": "...", "scope": "...", "depends_on": [], "estimated_complexity": "small | medium | large"}
    ]
  },
  "missing_dependency": {
    "package": "...",
    "version": "...",
    "ecosystem": "pip | npm | go | other",
    "reason": "..."
  },
  "tool_error_details": {
    "tool": "pytest",
    "error": "command not found",
    "remediation_hint": "<建議的修法>"
  },
  "partial_completed": ["..."],
  "partial_missing": ["..."],
  "suggest_lesson": null,
  "suggest_pattern": null,
  "suggest_codex": null,
  "suggest_skill": null
}
```

### 3.2 必備欄位（永遠必填）

| 欄位 | 類型 | 說明 |
|---|---|---|
| `verdict` | string | enum 上述 7 個 |
| `actor.role` | string | role name（匹配 `.claude/agents/{name}.md`）。**例外**：L0 holistic review 由 main 自做，可用合成 role name `main-holistic-review`，無需對應 agent 檔（其他合成名稱不允許） |
| `actor.type` | string | enum: producer, reviewer |
| `actor.spec_id` | string | 當前 brief 或 sub-brief id |
| `actor.round` | integer | review 輪數（producer 預設 0；reviewer 從 1 起）。**reviewer 的 round 為 cumulative**：跨 Explore 重做不重置（與 review-loop.md §3.1 `rounds.reviewer` 同步） |
| `actor.stage` | string | pipeline stage 名稱 |
| `actor.adversarial` | boolean | 預設 `false`。Reviewer 在 `mode: adversarial` 模式跑時必填 `true`（pipeline.yaml `second_review: true` 觸發此模式；見 control-plane.md §5.3 + role md §5.y）。Producer 永遠 `false`。 |
| `summary` | string | ≤ 200 字，人類可讀摘要 |
| `artifact` | string \| null | 主要 artifact 路徑（producer 於 `pass` / `partial` 必填；其餘 verdict 無產出可 null；reviewer 通常 null） |

### 3.3 條件必填欄位（按 verdict）

| Verdict | 額外必填 |
|---|---|
| `pass` | `checks`（reviewer 才有；陣列每項 result 須為 pass / skipped） |
| `fail` | `checks`（陣列至少一項 result=fail） |
| `ambiguity` | `questions`（至少一項，severity=blocking 至少一） |
| `needs_decomposition` | `decomposition_proposal`（含 rationale + sub_briefs[] 至少一） |
| `needs_dependency` | `missing_dependency`（含 package / reason） |
| `tool_error` | `tool_error_details`（含 tool / error） |
| `partial` | `partial_completed` + `partial_missing`（兩者都至少一項） |

### 3.4 選填欄位（任何 verdict 都可附）

| 欄位 | 類型 | 用途 |
|---|---|---|
| `suggest_lesson` | object \| null | 提議寫入 .framework/memory/lessons/。格式：`{category, body, rationale}` |
| `suggest_pattern` | object \| null | 提議寫入 .framework/memory/patterns/。同格式 |
| `suggest_codex` | object \| null | 提議更新 codex。格式：`{section, knowledge_point, body, source, confidence}` |
| `suggest_skill` | object \| null | 提議新 skill。格式：`{name, scope, description, draft_body}` |

**規則**：
- 所有 `suggest_*` 欄位都是「提議」，**不直接寫**。Main 收 verdict 後彙整 → brief 結束時詢問使用者批准 → 批准後 main 寫
- Producer 不能直接 Write 到 .framework/memory/skills/codex（防幻覺放大鏈，見 design-summary 第 17.1 節）

---

## 4. 各 Verdict 詳細範例

### 4.1 `pass`（reviewer）

```json
{
  "verdict": "pass",
  "actor": {
    "role": "code-reviewer",
    "type": "reviewer",
    "spec_id": "2026-05-06-feature-x.a",
    "round": 1,
    "stage": "engineering",
    "adversarial": false
  },
  "summary": "Code 實作符合 spec、測試全通過、無 lint 問題",
  "artifact": null,
  "checks": [
    {"name": "tests", "result": "pass", "evidence": "pytest: 47 passed in 3.2s"},
    {"name": "lint", "result": "pass", "evidence": "ruff: 0 issues"},
    {"name": "diff_scope", "result": "pass", "evidence": "8 files in plan.allowed_paths"},
    {"name": "no_new_deps", "result": "pass", "evidence": "pyproject.toml unchanged"}
  ]
}
```

### 4.2 `fail`（reviewer）

```json
{
  "verdict": "fail",
  "actor": {
    "role": "code-reviewer",
    "type": "reviewer",
    "spec_id": "2026-05-06-feature-x.a",
    "round": 2,
    "stage": "engineering",
    "adversarial": false
  },
  "summary": "新增 test 通過，但 unit test 有 2 例 regression",
  "artifact": null,
  "checks": [
    {"name": "tests", "result": "fail", "evidence": "tests/test_user.py::test_login FAILED"},
    {"name": "lint", "result": "pass", "evidence": "ruff: 0 issues"}
  ]
}
```

### 4.3 `ambiguity`（producer）

```json
{
  "verdict": "ambiguity",
  "actor": {
    "role": "data-analyst",
    "type": "producer",
    "spec_id": "2026-05-06-slot-revenue-q2.a",
    "round": 0,
    "stage": "analysis",
    "adversarial": false
  },
  "summary": "需求未指定 cohort 切法，無法繼續分析",
  "artifact": null,
  "questions": [
    {"id": "q1", "text": "Cohort 是按註冊月份還是首次儲值月份？", "severity": "blocking"},
    {"id": "q2", "text": "要排除測試帳號嗎？", "severity": "non-blocking"}
  ]
}
```

### 4.4 `needs_decomposition`（producer）

```json
{
  "verdict": "needs_decomposition",
  "actor": {
    "role": "engineer",
    "type": "producer",
    "spec_id": "2026-05-06-auth-rewrite",
    "round": 0,
    "stage": "engineering",
    "adversarial": false
  },
  "summary": "auth 重寫範圍跨 3 個服務，建議拆 3 個 sub-brief",
  "artifact": null,
  "decomposition_proposal": {
    "rationale": "原 plan 涵蓋 user-service / session-service / token-service 三模組，互相耦合但測試獨立。並行拆解可大幅縮短時間。",
    "sub_briefs": [
      {"title": "重寫 user-service auth 層", "scope": "services/user/**", "depends_on": [], "estimated_complexity": "medium"},
      {"title": "重寫 session-service token 處理", "scope": "services/session/**", "depends_on": [], "estimated_complexity": "medium"},
      {"title": "重寫 token-service JWT 簽發", "scope": "services/token/**", "depends_on": ["a", "b"], "estimated_complexity": "small"}
    ]
  }
}
```

### 4.5 `needs_dependency`（producer）

```json
{
  "verdict": "needs_dependency",
  "actor": {
    "role": "engineer",
    "type": "producer",
    "spec_id": "2026-05-06-feature-y.a",
    "round": 0,
    "stage": "engineering",
    "adversarial": false
  },
  "summary": "需要 cryptography 套件做 RSA 簽章，目前未安裝",
  "artifact": null,
  "missing_dependency": {
    "package": "cryptography",
    "version": ">=42.0",
    "ecosystem": "pip",
    "reason": "plan 指定用 RSA-PSS 簽章，標準庫無此實作"
  }
}
```

### 4.6 `tool_error`（reviewer；producer 前置閘同構——actor.type 換 producer、artifact null）

```json
{
  "verdict": "tool_error",
  "actor": {
    "role": "code-reviewer",
    "type": "reviewer",
    "spec_id": "2026-05-06-feature-z.a",
    "round": 1,
    "stage": "engineering",
    "adversarial": false
  },
  "summary": "pytest 未安裝，無法執行測試檢查",
  "artifact": null,
  "tool_error_details": {
    "tool": "pytest",
    "error": "bash: pytest: command not found",
    "remediation_hint": "請使用者執行 `pip install pytest` 或檢查虛擬環境"
  }
}
```

### 4.7 `partial`（producer）

```json
{
  "verdict": "partial",
  "actor": {
    "role": "researcher",
    "type": "producer",
    "spec_id": "2026-05-06-fed-policy.a",
    "round": 0,
    "stage": "research",
    "adversarial": false
  },
  "summary": "完成 Fed 與 ECB 兩家政策追蹤，BoJ 因官網結構變動暫缺",
  "artifact": ".framework/briefs/2026-05-06-fed-policy/sub-briefs/a/stages/research/researcher.output.md",
  "partial_completed": [
    "Fed 2026 Q1-Q2 利率決議與聲明",
    "ECB 2026 Q1-Q2 利率決議與聲明"
  ],
  "partial_missing": [
    "BoJ 2026 Q1-Q2 政策資料（官網結構變動，原 selector 失效）"
  ]
}
```

---

## 5. Suggest 欄位範例

### 5.1 `suggest_lesson`

```json
"suggest_lesson": {
  "category": "code-review",
  "body": "Pytest 在 monorepo 子模組需 cd 後才能跑，否則 collect error",
  "rationale": "本次 review 第一輪因從 root 跑 pytest 導致誤判 fail，第二輪進子模組才正確"
}
```

### 5.2 `suggest_pattern`

```json
"suggest_pattern": {
  "category": "engineering",
  "body": "Auth 重寫類任務拆 user / session / token 三 sub-brief，前兩者並行、第三者依賴前兩者",
  "rationale": "本次 brief 套此切法 18 小時內完成，無 cross-service 衝突"
}
```

### 5.3 `suggest_codex`

```json
"suggest_codex": {
  "section": "1. 領域知識點",
  "knowledge_point": "win_rate vs payout_rate 區分",
  "body": "win_rate = 勝場 / 總場；payout_rate = 派彩金額 / 投注金額。分析 revenue 時用 payout_rate。",
  "source": "本次 brief 透過比對歷史報告確認",
  "confidence": "high"
}
```

### 5.4 `suggest_skill`

```json
"suggest_skill": {
  "name": "monorepo-pytest-runner",
  "scope": "local",
  "description": "本 monorepo 的 pytest 執行慣例（per-module cd + 環境變數）",
  "draft_body": "# Monorepo Pytest Runner\n\n## 慣例\n\n1. 必先 cd 到子模組目錄\n2. 設定 PYTHONPATH=...\n..."
}
```

---

## 6. Main session 解析流程

```
1. Spawn role 後，等 subagent 結束
2. 從最後一段訊息抓 JSON（用 ```json ... ``` 框定）
3. 驗證 schema（機械：`verdict_check.py`）：
   - `actor.advisory: true` → 走 §2.3 advisory 分支（clean|findings + findings 七欄 + design_sketch 八欄）
   - 否則 verdict 在 7 個之中
   - actor.* 欄位齊全
   - 條件必填欄位按 verdict 檢查
4. Schema 通過 → 按 verdict 路由：
   - pass → 進下一 stage（依 .framework/pipeline.yaml）
   - fail → 入 review-loop.md 邏輯
   - ambiguity → 入 clarification.md 處理
   - needs_decomposition → 進 e2r-tree.md 切 sub-brief
   - needs_dependency → 升級使用者
   - tool_error → 升級使用者
   - partial → 提示使用者：接受還是補完
5. Schema 失敗 → 視為 tool_error（role 寫錯），retry 一次或升級使用者
6. 收 suggest_* 欄位 → 暫存於 brief 目錄 `_suggestions.json`，brief 結束時統一處理
```

---

## 7. JSON 嵌入訊息的格式約定

Subagent 結束時，必在最後訊息以 fenced code block 包 JSON：

````markdown
（任何先前的人類可讀說明）

```json
{
  "verdict": "pass",
  ...
}
```
````

**規則**：
- 必須是 ` ```json ` 開頭、` ``` ` 結尾的 fenced block
- 整個訊息只能有**一個** JSON block（多個 → main 視為 schema 違規）
- JSON 必須是合法 JSON（不可註解、不可 trailing comma）
- JSON 之前可有自由文字說明（main 顯示時可附）；JSON 之後不可有任何文字

---

## 8. 給接手 agent 的提醒

- **Schema 驗證在 main 端做**：role md 鐵律可寫「必 emit 此格式 JSON」，但 main 必驗證實際輸出（不能信 role 自我聲稱）
- **Suggest 欄位是「提議」**：never auto-apply，永遠走 brief 結束時的使用者批准流程
- **`actor.round` 從 1 起算（reviewer），producer 預設 0**：avoid off-by-one
- **多個 JSON block 是錯誤**：role md 不可有 example JSON block 在 prompt 末段（會混淆抓取邏輯）；範例放 prompt 中段或用其他語言區塊
- **Schema 版本不寫進 JSON**：版本由 .framework/lib/VERSION 統管。落地專案 framework upgrade 時走 3-way merge

---

## 9. 相關文件

- `core/soul-schema.md`：role md 中的「執行流程」最後步驟必為 emit 此 JSON
- `core/control-plane.md`：main 何時呼叫 / 解析此 JSON
- `core/review-loop.md`：fail verdict 的 1-2-3-4 輪邏輯
- `core/e2r-tree.md`：needs_decomposition verdict 的 tree 操作
- `core/clarification.md`：ambiguity verdict 的問題處理
- `core/escalation-rules.md`：needs_dependency / tool_error 的升級流程
- `core/learning-loop.md`：suggest_* 欄位的批准流程
