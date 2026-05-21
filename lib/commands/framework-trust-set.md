---
name: framework-trust-set
description: 切換 trust mode（strict / standard / sandbox）
allowed_tools: Read, Edit
---

# /framework-trust-set

切換 framework trust mode。對應 `core/trust-modes.md`。

## 用法

```
/framework-trust-set strict
/framework-trust-set standard
/framework-trust-set sandbox
/framework-trust-set            # 顯示當前 mode + 三選項
```

## 行為

```
1. Read .framework/.initialized 取當前 trust_mode
2. 若無參數 → 顯示當前 + 列三選項 + 退出
3. 解析參數：
   - strict / standard / sandbox → 進入切換流程
   - 其他 → 錯誤
4. 若新模式 == 當前 → 顯示「無變更」退出
5. 若新模式更寬鬆（standard → sandbox / strict → standard）：
   顯示警告：
   「將從 {current} → {new}
    解禁的指令類別：
      - {例 pip install / npm install}
      - {curl / wget}
      - {等}

    確定？(y/N)」
   y → 套用；N → 取消
6. 若新模式更嚴格（sandbox → standard / standard → strict）：
   顯示確認（不警告，因更嚴格不會破壞東西）：
   「從 {current} → {new}（將收緊權限）
    確定？(y/N)」
   y → 套用
7. 寫 .framework/.initialized.trust_mode = new
7.4. 寫 .claude/settings.local.json.trust_mode = new（top-level field，與 framework-initialized 同步）
7.5. **Sync `.claude/settings.local.json` 的 permissions**（依 core/trust-modes.md § 5.1 演算法）：
     - 計算新 trust mode 的 allow / deny 樣板
     - 從 settings.local.json 取舊的 _framework_managed_permissions
     - 從 permissions.{allow,deny} 移除舊 managed 項目
     - 加入新 managed 項目
     - 更新 _framework_managed_permissions = 新 managed
     - 保留 permissions 內使用者後加的項目
     - 寫回 settings.local.json
   8. **提醒重啟**：「Trust mode 已切換 + permissions 已 sync。需重啟 Claude Code session 才會生效。」
9. 顯示生效訊息 + 各模式對應 deny 清單參考連結（trust-modes.md）
```

## 顯示範例（無參數）

```
當前 trust mode：standard

三模式：
  - strict     最嚴格，每新指令必升級。生產 / 共用 repo
  - standard   合理白名單。個人熟悉 repo（**當前**）
  - sandbox    僅擋災難級。拋棄式 / 全新空專案

切換：/framework-trust-set <mode>
詳細：.framework/lib/core/trust-modes.md
```

## 顯示範例（standard → sandbox）

```
⚠️ 切換 trust mode：standard → sandbox

將解禁的指令類別：
  - pip install / npm install / go get / cargo install / gem install
  - curl / wget
  - rm -rf ./xxx（限當前專案）
  - chmod（限當前專案）

仍會擋（即使 sandbox）：
  - sudo / su
  - rm -rf / ~ $HOME ../
  - chmod -R 777 / ~
  - git push --force to main / master
  - git config --global
  - ssh 到非 localhost
  - 寫系統路徑（/etc, /usr）

確定切換？(y/N)
```

## 異常

| 狀況 | 處理 |
|---|---|
| Framework 未 init | 顯示錯誤：「未 init，先執行 /framework-init」 |
| 模式名稱錯誤 | 顯示三選項、要求重輸入 |
| 寫檔失敗 | 回滾、顯示錯誤 |

## 影響範圍

切換需重啟 Claude Code 才會完全生效（settings.local.json 內 permissions 由 Claude Code 在 session 啟動時讀入）：
- 重啟後 Bash 白名單採用新模式
- 已在跑的 sub-brief 不受影響（保留啟動時的 mode；見 _active.yaml.trust_mode）
- 同時更新：
  - `.framework/.initialized.trust_mode` = new
  - `.claude/settings.local.json.trust_mode` = new
  - `.claude/settings.local.json._framework_managed_permissions` = 依 new mode 套樣板
  - `.claude/settings.local.json.permissions.{allow,deny}` = sync 後（保留 user 加項）

## 不做的事

- 不切換 main session 自己的 Bash 行為（main 永遠用 framework core 內建白名單）
- 不影響使用者自己 shell 的權限
- 不重 init

## 相關指令

- `/framework-status`
- `/framework-init --reset`（若要重訪 init Step 3 Q2）

## 相關文件

- `core/trust-modes.md`：三模式詳細 deny / allow 清單
