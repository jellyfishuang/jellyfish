---
name: framework-hooks-sync
description: 部署 framework hooks/scripts 並同步 .claude/settings.json 掛載（確定性機械流程）
allowed-tools: Read, Bash
---

# /framework-hooks-sync

跑 `lib/scripts/hooks_sync.py` 完成機械閘部署鏈。合併邏輯在 script 內（確定性），main 只是薄包裝——**不手動編輯 settings.json 的 hooks 區塊**。

## 用法

```
/framework-hooks-sync            # 部署 + 合併 settings + 跑 62-case 回歸
/framework-hooks-sync --dry      # 只顯示將發生的變更, 不寫任何檔
/framework-hooks-sync --no-test  # 部署 + 合併, 跳過回歸（不建議, 除非趕時間）
```

## 何時用

| 情境 | 說明 |
|---|---|
| init 後首次接機械閘 | `/framework-init` 不含 hooks 部署，需跑本指令一次 |
| forward-port / 升級 framework 版本後 | lib/hooks 或 lib/scripts 有更新時重跑 |
| gate script 改動後 | 重部署並自動跑回歸 |
| settings.json hooks 被手動改壞 | 重跑即回框架預期狀態（framework-managed 條目整組重建） |

## Main 執行步驟

1. 找 Python 3 直譯器：偵測順序 `python3 --version` → `py -3 --version` → `python --version`（須確認 3.x；**Windows 上 `python` 可能是 2.x，勿直接假設**）
2. 跑 `<python3> .framework/lib/scripts/hooks_sync.py`（`--dry` → 加 `--dry-run`；`--no-test` → 加 `--skip-tests`）
3. 原樣轉述 script 輸出摘要（deploy 清單 / settings 更新或無變更 / tests 結果行）——數量結論引用 stdout，不自行改寫
4. script exit 1 → 顯示 stderr 給使用者，**不重試、不手動修 JSON**；等使用者處理
5. 提醒：本版 Claude Code 實測 settings.json 寫入後 hooks 即時生效；若未生效用 `/hooks` 重載或重啟 session

## Script 行為（`lib/scripts/hooks_sync.py`）

- `lib/hooks/*.py` → `.framework/hooks/`、`lib/scripts/*.py` → `.framework/scripts/`（byte 相同不重寫）
- 渲染 `hooks-config.template.json`（`{PYTHON}` = 實體直譯器路徑、`{PROJECT_ROOT}` = 專案根）
- 合併 `.claude/settings.json`：command 含 `.framework/hooks/` 的條目 = framework-managed 整組替換；**使用者自加 hook 條目原樣保留**；`_framework_managed_hooks` 鏡像同步更新
- settings.json 非合法 JSON → 拒絕覆寫、exit 1（不 fail-open）
- 跑 `.framework/hooks/run_tests.py`，非 `FAILURES: 0` → exit 1

## 鐵律

- settings.json 的 hooks 區塊由本流程管理；手動編輯會在下次 sync 被重置（framework-managed 部分）
- 使用者自訂 hook（command 不含 `.framework/hooks/`）永遠保留，本指令不動
