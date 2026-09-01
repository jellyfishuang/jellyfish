# Trust Modes — 三檔信任模式與 Bash 白名單

> 本文件規範 strict / standard / sandbox 三檔信任模式，及各模式對應的 Bash 白名單規則。
>
> 對應 design-summary 第 17.2 節（討論第 14b 題的決議）。

---

## 1. 三模式總覽

| 模式 | 適用情境 | Bash 哲學 | 依賴安裝 |
|---|---|---|---|
| `strict` | 生產 repo / 共用 repo / 不熟環境 | 最小白名單，凡新指令必升級 | 嚴格走 `needs_dependency` 流程 |
| `standard` | 個人熟悉 repo（**framework 預設**） | 合理白名單 | 走 `needs_dependency` |
| `sandbox` | 拋棄式 VM / 全新空專案 | 大幅放寬，只擋災難級 | 直接允許 install |

模式記錄在 `.framework/.initialized.trust_mode`。可透過 `/framework-trust-set <mode>` 切換。

---

## 2. Strict Mode

### 2.1 適用情境
- 動到 production 程式碼的 repo
- 多人共用 repo（CI 設定 / deploy script 都在內）
- 不熟悉的 repo（你不知道哪些動作有副作用）
- 高合規要求（金融 / 醫療 / SOX 範圍）

### 2.2 Allow（白名單）
- `git status` / `git log` / `git diff` / `git show` / `git branch` (read-only)
- `git worktree add/remove/list`（main 用於建管 worktree）
- `git merge`（main 用於 sub-brief merge）
- `git checkout` (限 branch 切換)
- `echo`（不含 redirection）
- `ls` / `pwd` / `cat`（read-only）
- Recipe 設定的 `test_command`（白名單明確列出，不接受 wildcards）
- Recipe 設定的 `lint_command`

### 2.3 Deny（黑名單）

包含 standard 全部 + 額外：
- `git merge --no-ff`（強制 fast-forward）
- 所有 `rm` 指令（含 `rm -f` 等）
- 所有網路指令（`curl` / `wget` / `nc` / `ssh` / `scp` / `rsync`）
- 所有 `cp` 跨目錄（限制 rwx 範圍）
- `find ... -exec`（任意指令執行）
- `xargs ...`（任意指令執行）
- 任何 redirect 寫檔（`>`, `>>`）

### 2.4 安裝任何依賴 → `needs_dependency` verdict 強制升級

producer 不可自己跑 `pip install` / `npm install` / 等。回 verdict 標 `needs_dependency` → 升級使用者批准。

---

## 3. Standard Mode

### 3.1 適用情境
- 個人熟悉的開發 repo
- 部分 production code 但個人有完全 ownership
- 一般日常工作（你 70% 的專案）

### 3.2 Allow（白名單）

包含 strict 全部 + 額外：
- `git fetch`（read remote）
- `git pull --ff-only`（純 fast-forward）
- `git stash` / `git stash pop`
- `git rebase`（限 local branch；不對 main / master）
- Recipe 設定的 build / test / lint 系列指令
- 標準 file ops：`mkdir` / `mv` / `cp`（限當前 repo 範圍）
- `rm` （限當前 repo 範圍，不含 `-rf`）

### 3.3 Deny（黑名單）

| Deny | 理由 |
|---|---|
| `git push` | 對 remote 推送是 explicit user action |
| `git reset --hard` | 不可逆破壞性 |
| `git config` | 改 git 行為，影響長期 |
| `git push --force` | 永遠 deny（除使用者明示 sandbox）|
| `rm -rf` | 災難性 |
| `sudo` / `su` | trust escalation |
| `chmod` | 改權限影響長期 |
| `chown` | 同上 |
| `curl` / `wget` | 不可控網路存取 |
| `pip install` / `npm install` / `go get` / `cargo install` / `gem install` | 走 `needs_dependency` 流程 |
| `ssh` / `scp` / `rsync` | 跨機器存取 |
| `nc` / `netcat` | 任意網路 |

### 3.4 安裝依賴

走 `needs_dependency` verdict（同 strict）。

---

## 4. Sandbox Mode

### 4.1 適用情境
- 拋棄式 Docker / VM
- 全新空專案
- 沙盒實驗
- 你描述的「完全空白的專案」（design-summary 第 17.2 節 14b 討論）

### 4.2 Allow（大幅放寬）

包含 standard + 額外：
- `pip install` / `npm install` / `go get` / `cargo install` / `gem install`（任意安裝）
- `curl` / `wget`（任意抓）
- `rm -rf ./xxx`（限當前專案內，不可指向 root / home / system）
- `chmod`（限當前專案內）
- 大部分 git 指令（除下方 deny）
- `find ... -exec`（任意指令）
- `xargs`（任意指令）
- 跨目錄 `cp` / `mv`（在 user home 範圍內）

### 4.3 Deny（只擋災難級）

| Deny | 理由 |
|---|---|
| `sudo` / `su` | trust escalation 永遠擋 |
| `rm -rf /` | 砸 host filesystem |
| `rm -rf ~` | 砸 user home |
| `rm -rf $HOME` | 同上 |
| `rm -rf ../` 或 `rm -rf ..` | 跳出當前專案 |
| `chmod -R 777 /` | 系統級權限破壞 |
| `chmod -R 777 ~` | user home 權限破壞 |
| `git push --force` to main / master | 即使沙盒，誤推真 remote 仍可能 |
| `git config --global` | 改全域影響容器外 |
| `ssh` 到非 localhost | 跨機器 |
| `> /etc/...` / `> /usr/...` | 寫系統路徑 |
| `dd` 寫 raw device | 災難 |
| `mkfs` / `format` | 災難 |

**Sandbox 仍擋這些的理由**：
1. **Trust escalation**（sudo / chmod 777）—— 即使沙盒也不該 escalate
2. **跨邊界破壞**（rm -rf / 或 ~）—— 沙盒邊界外的東西不該被誤砸
3. **真 remote 的 push --force**—— 沙盒裡 git remote 可能真的指向 production
4. **全域設定**—— 影響容器外
5. **Raw device / 系統路徑寫**—— 災難級

### 4.4 安裝依賴

直接允許（producer 可自己跑 `pip install` 等），不走 `needs_dependency` 流程。

---

## 5. 使用者覆寫

`.framework/.initialized` 內：

```yaml
trust_mode: standard
bash_extra_allow:                # 在 mode 預設外額外允許
  - pytest --cov
  - go test -race ./...
bash_extra_deny:                 # 在 mode 預設外額外禁止
  - npm install                  # 即使 sandbox 也禁（例：使用者只用 yarn）
```

優先級：`bash_extra_deny` > `bash_extra_allow` > mode 預設。

---

## 5.1 Claude Code permissions sync（**核心機制**）

### 為什麼需要 sync

Framework 的 trust mode 是**邏輯規範**（md 文字描述）。實際攔截 Bash 指令的是 Claude Code 自己的權限系統（讀 `.claude/settings.local.json` 的 `permissions.allow / deny`）。

兩者**不會自動同步**——這也是為什麼 framework 跑時 Claude Code 仍然彈大量「allow this command?」prompt：因為 settings.local.json 的 permissions 是空的。

**解法**：Framework 在 init / 切換 trust mode 時**自動寫 `permissions.allow / deny` 到 settings.local.json**。

### Settings.local.json 結構（含 framework-managed 區塊）

```json
{
  "framework_disabled": false,
  "trust_mode": "standard",
  "_framework_managed_permissions": {
    "allow": ["Bash(git status:*)", "Bash(go test:*)", ...],
    "deny": ["Bash(sudo:*)", ...]
  },
  "permissions": {
    "allow": [
      "Bash(git status:*)",
      "Bash(go test:*)",
      ...framework-managed entries...,
      "Bash(my custom command)"  // 使用者後續手動加的
    ],
    "deny": [
      "Bash(sudo:*)",
      ...
    ]
  }
}
```

**Two-key design**：
- `_framework_managed_permissions.{allow,deny}`: framework 紀錄它**過去**寫入了哪些（追蹤用，Claude Code 忽略）
- `permissions.{allow,deny}`: Claude Code 真正讀的；含 framework-managed + 使用者後加的

### Sync 演算法（main 在 init / trust-set 時執行）

```
def sync_permissions(new_trust_mode):
    settings = read_json('.claude/settings.local.json')

    # 計算新的 framework-managed lists
    new_allow = mode_template[new_trust_mode]['allow'] + recipe.bash_extra_allow + customization.bash_extra_allow
    new_deny = catastrophic_deny_list + customization.bash_extra_deny

    # 取舊的 managed list（追蹤）
    old_managed_allow = settings.get('_framework_managed_permissions', {}).get('allow', [])
    old_managed_deny = settings.get('_framework_managed_permissions', {}).get('deny', [])

    # 計算 actual permissions：移除舊 managed、加入新 managed、保留使用者後加的
    actual_allow = settings['permissions']['allow']
    actual_allow = [x for x in actual_allow if x not in old_managed_allow]   # 移除 framework 過去加的
    actual_allow = list(set(new_allow + actual_allow))                       # 加入新 managed + 保留 user 加的

    actual_deny = settings['permissions']['deny']
    actual_deny = [x for x in actual_deny if x not in old_managed_deny]
    actual_deny = list(set(new_deny + actual_deny))

    # 寫回
    settings['_framework_managed_permissions']['allow'] = new_allow
    settings['_framework_managed_permissions']['deny'] = new_deny
    settings['permissions']['allow'] = sorted(actual_allow)
    settings['permissions']['deny'] = sorted(actual_deny)
    write_json('.claude/settings.local.json', settings)
```

### Catastrophic deny list（三 mode 共用）

只擋災難級。其他靠 prompt 把關（使用者答應第一次後 Claude Code 通常會記住）。

```
"deny": [
  "Bash(sudo:*)",
  "Bash(su:*)",
  "Bash(rm -rf /)",
  "Bash(rm -rf /*)",
  "Bash(rm -rf ~)",
  "Bash(rm -rf ~/*)",
  "Bash(rm -rf $HOME)",
  "Bash(rm -rf $HOME/*)",
  "Bash(rm -rf ../)",
  "Bash(rm -rf ..)",
  "Bash(chmod -R 777 /)",
  "Bash(chmod -R 777 /*)",
  "Bash(chmod -R 777 ~)",
  "Bash(chmod -R 777 ~/*)",
  "Bash(git push --force)",
  "Bash(git push -f)",
  "Bash(git push --force:*)",
  "Bash(git push -f:*)",
  "Bash(git config --global:*)",
  "Bash(dd if=:*)",
  "Bash(dd of=:*)",
  "Bash(mkfs:*)"
]
```

**注意**：原本曾考慮加 fork bomb 模式（`:(){ :|:& };:`），但 Claude Code 的 permission parser 把內含的 `()` 視為「empty parentheses」誤判 → rule 被 skip 並噴 warning。已從清單移除。Fork bomb 防禦改靠 sudo deny + general caution。

### Allow 樣板（按 trust mode）

**strict**（最小 allow set，凡新指令必經 prompt）：
```json
[
  "Bash(git status:*)",
  "Bash(git log:*)",
  "Bash(git diff:*)",
  "Bash(git show:*)",
  "Bash(git branch:*)",
  "Bash(git worktree add:*)",
  "Bash(git worktree list:*)",
  "Bash(git worktree remove:*)",
  "Bash(git checkout:*)",
  "Bash(git merge:*)",
  "Bash(ls:*)",
  "Bash(cat:*)",
  "Bash(head:*)",
  "Bash(tail:*)",
  "Bash(wc:*)",
  "Bash(mkdir:*)",
  "Bash(echo:*)"
  // recipe 設的 test_command / lint_command 在 init 時 append
]
```

**standard**（strict + git 寫入 local + cp/mv/rm 限 framework 範圍）：
```json
[
  ...strict 全部...,
  "Bash(git pull --ff-only:*)",
  "Bash(git stash:*)",
  "Bash(git rebase:*)",
  "Bash(git fetch:*)",
  "Bash(git commit:*)",
  "Bash(git add:*)",
  "Bash(cp:*)",
  "Bash(mv:*)",
  "Bash(rm .framework/briefs/_active/*.yaml)",
  "Bash(rm .framework/briefs/_active/_closing.lock)",
  "Bash(rm -rf .framework/briefs/*/)",
  "Bash(rm -rf .framework/worktrees/*/)",
  // recipe 設的 build / test / lint 系列
  // customization.bash_extra_allow
]
```

**sandbox**（最寬，僅 deny 擋災難級）：
```json
[
  "Bash(*)"
]
```

注：`Bash(*)` 表示所有 Bash 指令前綴匹配。配合 deny 列表，效果是「除災難級外全允許」。

### Init / trust-set 時觸發 sync

- `/framework-init` Step 5：寫 settings.local.json 時呼叫 sync
- `/framework-trust-set <mode>`：切換 mode 後立即呼叫 sync
- `/framework-permissions-sync`（新指令）：手動再 sync 一次（settings.local.json 漂移時用）

### 使用者後續手動編輯 settings.local.json 不會被覆寫

只要使用者加的條目不在 `_framework_managed_permissions.allow / deny` 內，sync 不動它們。例：

```
使用者加: "Bash(my-custom-tool:*)" → 這項在 permissions.allow 但不在 _framework_managed_permissions.allow
sync 跑時：保留此項。
```

---

## 6. 自動偵測（init Step 1）

| 偵測 | 推薦 mode |
|---|---|
| `.github/workflows/`、`Dockerfile.production`、`deploy/`、CI 配置 | strict |
| 有真實程式碼但無 production indicator | standard |
| 空專案 / 只有 `.devcontainer/` / `Dockerfile.dev` | sandbox |
| dir 名含 `sandbox`/`scratch`/`playground` | sandbox |
| 偵測不到（無 git history、無 README） | standard（讓使用者自選） |

Init Step 3 Q2 顯示推薦但允許覆寫。

---

## 7. 切換模式

```
/framework-trust-set <mode>
```

行為：
1. 確認當前模式（讀 `.framework/.initialized.trust_mode`）
2. 若新模式 == 當前 → 顯示「無變更」退出
3. 若新模式更寬鬆（standard → sandbox）→ 警告：「將解禁 X / Y / Z 等指令。確定？(y/N)」
4. 若新模式更嚴格（sandbox → standard）→ 直接生效（變更不會破壞東西）
5. 寫入新模式至 `.framework/.initialized.trust_mode`
6. 顯示生效訊息

---

## 8. Verdict 中的權限失敗

producer 試圖跑 deny 的 Bash → Bash tool 直接拒絕（Claude Code 層級）。Producer 應：
- 偵測到禁用指令（例：plan 要求 `npm install` 但當前 strict）
- 不嘗試執行
- 回 `needs_dependency` 或 `tool_error` verdict 升級

---

## 9. Main session 的特權

Main 自己用的 Bash 不在 producer / reviewer 白名單範圍內。Main 永遠可用（不受 trust mode 影響）：

**檔案 / 目錄管理**（init 與一般運作 token 效率關鍵）：
- `cp` / `cp -r`（複製 .framework/ 檔案到 .claude/、複製 template）
- `mv`（重命名 / 歸檔 brief 到 _archive/）
- `mkdir` / `mkdir -p`（建立目錄結構）
- `ls` / `ls -la`
- `rm` 限 `.framework/briefs/_active/` 內（lane 鎖 / _closing.lock）/ `.framework/briefs/{...}/` 內 / `.framework/worktrees/` 內 / `.framework/codex/.backup-*/` 內
- `cat` / `head` / `tail` / `wc`（純讀）

**Git 管理**：
- `git worktree add/remove/list`
- `git branch -d`（刪自己建的 brief branch）
- `git merge`（merge sub-brief 回 main）
- `git status` / `git log` / `git diff`
- `git checkout`（限 branch 切換）

**Echo**：
- `echo`（含 redirection 寫進允許目錄）

但 main 也不能執行：
- `git push`（永遠 deny）
- `git push --force`（永遠 deny）
- `git reset --hard`（永遠 deny；會破壞使用者工作）
- `git config --global`（永遠 deny）
- `sudo` / `su`（永遠 deny）
- 任何 install 指令（`pip install` / `npm install` / `go get` / `cargo install`）
- `curl` / `wget`（main 不抓網路；走 WebFetch tool）

**為什麼 cp / mv 是 main 特權**：
- Init 階段大量複製 .framework/ 檔案進 .claude/。若改用 Read + Write 等於 token 雙倍消耗
- Brief 歸檔 / worktree 管理也需 cp / mv
- 這些指令在「限 repo 內」範圍下是安全的

**Producer / reviewer 仍受 trust mode 限制**：第 2-4 節各模式的規則對 subagent 適用；main 永遠寬鬆。

---

## 10. 給接手 agent 的提醒

- **Trust mode 不是 escape hatch**：sandbox 仍擋災難級，使用者不能用 sandbox 一次性繞過 sudo
- **Recipe 設的 test/lint 命令進白名單**：init 時自動加入 `bash_extra_allow`
- **Producer 偵測到禁用指令時要回 verdict，不要硬試**：硬試會被 Claude Code 拒絕，浪費 round
- **切換模式不重 init**：用 `/framework-trust-set <mode>`
- **使用者覆寫 (extra_allow/deny) 不主動寫進 git**：只在 `.framework/.initialized` 與 `settings.local.json`，個人化
