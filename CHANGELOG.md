# Framework CHANGELOG

記錄 framework lib（`lib/`）的版本演變。版號採 SemVer，對應 git tag。版號真實來源＝ `lib/VERSION`。

## 0.1.0 — 2026-05-21

dev-team recipe 起點基準版。

- **Control Plane Pattern**：main session 為唯一編排者，所有 subagent 皆為 leaf（規避 nested-Task 限制）
- **E²R 受限 2 層樹**：Explore → Execute → Review，L0 brief + L1 sub-brief，不允許 L2
- **四層抽象**：Role / Skill / Codex / Directive
- **Typed Verdict**：7 種 verdict（pass / fail / ambiguity / needs_decomposition / needs_dependency / tool_error / partial）驅動 main 下一步
- **Trust Modes**：strict / standard / sandbox 三檔
- **學習迴圈**：brief 完成自動寫 session，使用者批准下沉澱 lesson / pattern（local-only，與外部知識庫解耦）
- **純文件**：Markdown + YAML / JSON，零 shell script、零可執行程式
