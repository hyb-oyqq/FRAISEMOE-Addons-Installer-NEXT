# P0 / P1 修复设计（子项目 2 + 3 + 4 合并）

日期：2026-09-02
基线：`master` @ `dfd8e7c`（源码与审查基线 `803f32b` 完全一致，`dfd8e7c` 仅新增文档）
状态：待实现
前置依赖：[测试地基设计（子项目 1）](2026-09-01-test-foundation-design.md)

---

## 1. 背景

安全与质量审查产出 64 条发现（严重 9 / 高 24 / 中 31）。其中「严重 + 高」共 **33 条**构成 P0 / P1，是本 spec 的核心范围。

原拆分方案（见子项目 1 spec §4）把这些修复分给子项目 2（安全热修）、3（崩溃与假死）、4（提权与打包），执行顺序为 `1 → 3 → 2 → 4 → 5`。本轮决定将 **2 + 3 + 4 合并为一份 spec**，原因是：三者共同覆盖全部 33 条 P0 / P1，拆成三份会在接口边界上反复来回（例如卸载 manifest 由子项目 2 引入，但写入点在子项目 3 修过的 `ExtractionThread` 里）。

合并后**内部仍保留原有的三阶段顺序与风险梯度**，见 §4。

子项目 1 已经为本轮铺好了接缝：它提取了 5 个模块、写了 14 条红测试作为验收清单，并实现了 5 个「修复用」函数但**刻意不接入调用点**。本轮的工作因此大幅缩减为两类动作：**接入调用点** + **翻转照搬过来的缺陷逻辑**。

## 2. 目标

1. 修复全部 33 条 P0 / P1 发现。
2. 顺带修复 6 条与之同源、改动位置重合的「中」级发现（CI、打包、版本号、文档）。
3. 让子项目 1 的 14 条红测试全部转绿。
4. 为无法自动化验证的 6 处产出并执行手动核查结果。

## 3. 非目标

- **不做 Qt 层与业务逻辑的彻底分层。** 本轮只在既有结构内修复缺陷。
- **不做线程模型重构。** 优选流程保留「标志位 + 轮询」模型，只补收尾与看门狗（决策见 §5.2）。
- **不做代码签名。** 需要证书，超出本轮，作为已知缺口记录在 §9。
- **不修「中」「低」级发现**，除非其改动位置与 P0 / P1 重合（如 §7 的 CI 与 build.spec）。
- 剩余的「中」「低」级发现与文档一致性（原子项目 5）留待后续。

## 4. 三阶段结构

| 阶段 | 内容 | 处数 | 是否改数据流 | 可独立发布 |
|---|---|---|---|---|
| 一 | 崩溃与假死 | 22 | 否 | **是** |
| 二 | 安全热修 | 12 | **是** | 否 |
| 三 | 提权与打包 | 5 | 否（改打包与 CI） | 是 |

合计 39 处改动，编号 #1–#39 贯穿全文，与审查台账逐条对应。

顺序为 **一 → 二 → 三**，保留原拆分的风险梯度：先做确定性小改动，在低风险下验证「测试地基 + 修复流程」这套机制确实可用，再去动会静默毁坏用户数据的部分。

**阶段一单独即可发布。** 它只修崩溃与假死，完全不碰数据流。若阶段二中途发现方向有误，阶段一成果可独立发版，用户立即获得「暂停按钮可用、关闭应用不再卡死、优选取消不再锁死主窗口」等实际改善。这是本结构最重要的风险性质。

每阶段为独立提交序列，保持 `git bisect` 可用。

---

## 5. 阶段一：崩溃与假死（22 处）

按根因归组。本阶段全部改动**不改变任何数据流**。

### 5.1 退出路径（4 处）

| # | 位置 | 改动 |
|---|---|---|
| 1 | `download_manager.py:1143/1146/1151` | 三处调用了全仓库不存在的 `DebugManager.log_debug/log_warning/log_error`。改用模块级 `logger`。**并给 `except` 处理器本身加保护**——现状是 `:1143` 抛 `AttributeError` 被 `:1150` 捕获后，处理器自己在 `:1151` 二次抛出且无人接手，异常穿透 `shutdown_app` |
| 2 | `main_window.py:318-319` | `download_manager.current_download_thread` 恒为 `None`（`download_manager.py:40` 初始化后全仓库再无赋值），真实线程在 `download_task_manager.current_download_thread`。改为取后者，并调用它自己的 `stop()`——`requestInterruption()` 对 `DownloadThread` 是空操作（该类全程只读 `_is_running`，从未调用 `isInterruptionRequested()`）。同时删除 `download_manager.py:40` 这个误导性死属性 |
| 3 | `main_window.py:307-335` | `graceful_stop_threads`（`:321`）与 `stop_logging`（`:324`）在退出确认框**之前**执行，用户点「No」后应用带残废状态继续运行。移到确认之后 |
| 4 | `main_window.py:310-319` | Cloudflare 优选线程（`cloudflare_optimizer` 的 `ip_optimizer_thread` / `ipv6_optimizer_thread`）未纳入清理字典，补上 |

### 5.2 流程锁死（4 处）

| # | 位置 | 改动 |
|---|---|---|
| 5 | `download_task_manager.py:241-242` | 删除该空方法重定义（函数体只有 docstring，文件到此结束），它覆盖了 `:63` 的真实现，导致暂停按钮完全失效。补上文件末尾换行 |
| 6 | `extraction_handler.py:238` | `download_queue.appendleft([game_version])` 塞入单元素列表，而 `download_manager.py:749` 按五元组解包。重建完整五元组 `(url, game_folder, game_version, _7z_path, plugin_path)` 入队 |
| 7 | `cloudflare_optimizer.py:128-130, 333-338, 354, 405-410, 411-420` + `download_manager.py:729-733` | 五条退出分支统一走一个收尾函数（置完成标志 + 恢复窗口 `setEnabled(True)` + 恢复 `window_manager` 状态）；`check_optimization_status` 增加 `optimization_cancelled` 检查；**并为轮询链加 60 秒看门狗**，超时强制收尾 |
| 8 | `window_manager.py:73-75` | `STATE_ERROR` 同时 `setEnabled(False)` 并置 `install_button_enabled=False`。禁用的 `QPushButton` 不发 `clicked`，致使 `main_window.py:376-414` 整个错误重试分支不可达。改为错误态保持按钮可点，仅更换文案与样式 |

**决策记录（#7）**：本轮不把优选流程改为信号驱动。理由是当前开发机无法运行应用、Qt 测试基础薄弱，改组件间接口的验证手段不足。看门狗提供的性质是：**即使将来新增退出分支又漏置标志，主窗口也不会永久锁死**，以低成本获得该保证。信号驱动重构留待后续。

### 5.3 崩溃与异常逃逸（6 处）

| # | 位置 | 改动 |
|---|---|---|
| 9 | `extraction_thread.py:210` | 非 After 版本 `sig_filename = None`（`:125`），而 `file.endswith('.sig')` 对任意 `.sig` 成立，致 `:216` 执行 `os.path.join(game_folder, None)` 抛 `TypeError`。改为 `elif sig_filename and file == sig_filename:` |
| 10 | `download_manager.py:777` | `installed_status[game_version]` 裸下标访问（同文件 `:582`、`:596` 用的是 `.get()`）。改 `.get(game_version, False)`。同时删除 `:773` 硬编码的 `game_exe_exists = True`，它使后续条件退化为死逻辑 |
| 11 | `ui_manager.py:62-68` | `setup_ui()` 只复制了 5 个 action 引用，漏了 `ipv6_action`（致 `:145/160/185/192` 抛 `AttributeError`）与 `open_log_action`（致 `debug_manager.py:85` 的 `hasattr` 守卫恒假，菜单项启用状态永不更新）。补上两个引用 |
| 12 | `helpers.py:232-239` | `load_config()` 直接返回 `json.load()` 结果，非 dict 类型时 `Main.py:49` 的 `.get()` 抛 `AttributeError`——且该行在 `Main.py:77` 创建 `QApplication` **之前**，异常钩子的 `QMessageBox` 分支无法工作，表现为无提示闪退。接入子项目 1 的 `coerce_config` |
| 13 | `config_fetch_thread.py:56-59` | `key not in config_data` 对数字 / 布尔 / `null` 抛 `TypeError`，不在捕获列表内，逃出 `run()` 致 `finished` 永不 emit。接入子项目 1 的 `validate_cloud_config`，**并在 `run()` 外层加兜底 `except` 保证信号必发** |
| 14 | `config_manager.py:62` | `ConfigFetchThread` 无 parent，唯一强引用是会被覆盖的属性；并发获取时运行中的 `QThread` 可能被 GC。传 `parent=self` |

### 5.4 状态与交互（8 处）

| # | 位置 | 改动 |
|---|---|---|
| 15 | `download.py:48-55` | `_is_running = False` 写在 `if self.process and ...` 内部，进程未创建时取消无效。提到条件外无条件执行；`Popen` 后立即复查一次，为假则终止刚启动的进程 |
| 16 | `download_task_manager.py:229-231` | `wait()` 无超时，`taskkill` 失败时 GUI 线程无限阻塞。改 `wait(5000)`，超时后 `terminate()` 再 `wait(1000)`；`taskkill` 失败回退 `process.kill()` |
| 17 | `download.py:267-270` + `download_manager.py:871-922` | 手动停止后仍 emit `finished(False, ...)`，致「已取消」与「是否重试」两个框叠加，点「结束」还会二次执行 `on_download_stopped`。失败分支识别「下载已手动停止。」直接 return |
| 18 | `download_manager.py:871-931` | 仅成功分支关闭进度窗，失败后重试会新建 `ProgressWindow` 覆盖引用而旧窗口的模态 `exec()` 仍在栈上。失败分支先关闭当前进度窗再弹错误框 |
| 19 | `cloudflare_optimizer.py:189` | 以 `button.text() == "Cancel"` 判断取消按钮，Qt 本地化即失效。改 `msg_box.standardButton(button) == StandardButton.Cancel` |
| 20 | `cloudflare_optimizer.py:136-138` + `:369-372` | `:137` 注释明写「临时覆盖配置（不保存到文件）」，但 `:369-372` 的 `save_config(self.main_window.config)` 把整个字典写盘，`ipv6_enabled=False` 被永久持久化。改为单独持久化 `last_hosts_optimized_hostname` |
| 21 | `patch_detector.py:135-155` | `:94` 对 `.fain` 也返回「已安装」，致 `:139` 的 `is_patch_installed or hash_check_passed` 把禁用补丁归入已安装，`:146` 的 disabled 检查不可达，`:290-318` 的启用引导成为死代码。改为先判 disabled 再判 installed |
| 22 | `uninstall_handler.py:65-66` | 提示「选择游戏目录」，但 `identify_game_directories_improved` 只枚举所选目录的**子目录**，按提示操作必然失败。提示语改「选择游戏上级目录」（与 `patch_toggle_handler.py:52` 一致），并在 `game_dirs` 为空时回退调用 `identify_game_version(selected_folder)`——该单目录回退能力在重构中丢失（`uninstall_handler.py:236-328` 已无调用者） |


---

## 6. 阶段二：安全热修（12 处）

本阶段是唯一改数据流的阶段，按「恢复哪个安全属性」分组。

### 6.1 传输信任链（2 处）

**#23 删除 `download.py:214` 的 `--check-certificate=false`。**

hosts 将域名指向 Cloudflare 优选 IP 后，TLS 握手仍以**域名作为 SNI**，Cloudflare 边缘节点会返回该域名的有效证书，因此开启校验本就应当正常工作。`:213` 的注释（「证书验证现在总是需要，因为我们依赖hosts文件」）表明原作者理解正确，仅代码写反。

**硬约束**：若优选 IP 并非该域名的有效边缘节点，握手失败、下载中断。此时回退方向**必须**是「放弃优选 IP、还原 hosts、直连重试一次」，**不得**回退为关闭证书校验。此约束需在代码注释中同时写明，避免后续维护者改回。

**#24 URL 校验**：接入子项目 1 的 `validate_download_url`，校验点在 `download_manager.py:129/137` **取到云端 URL 后立即执行**，而非调用 aria2c 前。

scheme 白名单（仅 `http` / `https`）是主防线——它按定义排除 `-` 开头的字符串，从而堵住 `download.py:216` 把云端可控值作为裸位置参数交给 aria2c 所导致的选项注入（可经 `--conf-path` 加载攻击者配置，再由 `on-download-complete` 在管理员权限下执行任意命令）。

在 URI 前加 `--` 分隔属纵深防御。**实现时需确认 aria2c 支持该分隔符**；若不支持则仅保留白名单，不在文档或注释中声称存在该层防护。

### 6.2 校验时机与判定（3 处）

**#25 校验挪到写入前。** `ExtractionThread.run()` 现有结构为「解压到 `tempfile.TemporaryDirectory()` → `shutil.copy2` 进 `game_folder`」。在这两步之间插入 SHA-256 比对 `PLUGIN_HASH[game_version]`：不匹配则**不复制**，直接 `finished.emit(False, ...)`。

临时目录中的文件与将被安装的文件逐字节相同，故校验对象正确。`extracted_path` 那条离线预解压分支（`:52-57`）在同一位置插入。

此改动使 `_perform_hash_check`（`extraction_handler.py:122`）从主要关卡降级为安装后确认，但**保留**——它仍能捕获复制过程中的损坏。

**#26 fail-open 三处翻转。** 接入子项目 1 的 `core/verification.py`：

| 位置 | 现状 | 改为 |
|---|---|---|
| `extraction_handler.py:146-151` | `install_paths` 为空 → `installed_status = True` | 返回 `SKIPPED_NO_PATHS`，调用方按失败处理 |
| `offline_mode_manager.py:553-566` | 同上，且额外加入 `installed_games` | 同上 |
| `hash_thread.py:127-130` | 目标文件不存在 → `continue`，`passed` 保持 `True` | 置 `passed = False` |

`SKIPPED_NO_PATHS` 枚举值子项目 1 已定义待用，本轮启用。

**#27 离线直装补前置校验。** `offline_mode_manager.py:944` 创建 `ExtractionThread` 前调用 `verify_patch_hash`；`download_manager.py:812-814` 拿不到 `offline_mode_manager` 时的 `hash_valid = True` 改为 fail-closed。

### 6.3 文件系统边界（2 处）

**#28 卸载改为清单驱动。**

manifest 位于 `CACHE/install_manifest.json`，结构：

```json
{
  "NEKOPARA Vol.1": {
    "files": ["D:/.../NEKOPARA Vol. 1/adultsonly.xp3"],
    "installed_at": "2026-09-02T10:00:00"
  }
}
```

由 `ExtractionThread` 在复制成功后写入。

卸载时三条规则，**走 manifest 或走白名单都适用**：

1. **永不 `rmtree`**；永不触碰 `patch/`、`game/patch/`、`game/config.json`、`game/scripts.json`（这些从来不是本程序写入的，见 `patch_manager.py:211/232/255/268`）
2. 删除前把**实际路径逐条**列给用户确认，替换现有「确定要卸载补丁吗」的笼统文案（`uninstall_handler.py:128/208`）
3. 每条路径删除前用 `os.path.commonpath` 断言仍在 `game_dir` 内
4. **只列出实际存在的路径**。manifest 中记录但磁盘上已不存在的条目（用户手动删过、或换过游戏目录）直接跳过，不计入待删清单、不报错。若过滤后清单为空，提示「未发现本程序安装的补丁文件」并结束，不执行任何删除

**无 manifest 的老用户**（既有安装均无 manifest）回退到白名单：从 `GAME_INFO` 推导的 5 个固定 basename（`adultsonly.xp3`、`update00.int`、`vol4adult.xp3`、`afteradult.xp3`、`afteradult.xp3.sig`）及其 `.fain` / `.sig` / `.fain.sig` 变体。老用户因此无感升级，且 manifest 丢失也不会导致误删。

同时修改 `derive_patch_file_candidates`（子项目 1 已提取，缺陷照搬）：停止对**完整路径**做 `.lower()` / `.upper()` / `.replace("_", "")` / `.replace("_", "-")`，改为**只对 basename 做变体**再 join 回 `game_dir`。现状下游戏装在 `D:\game_lib\...` 时会生成指向 `D:\gamelib\...` 与 `D:\game-lib\...` 的路径。

**#29 归档成员路径校验。** 接入子项目 1 的 `reject_unsafe_members`，在 `extraction_thread.py:188`、`:265` 及 `patch_detector.py:189`、`hash_thread.py:380` 的解压调用前过滤（拒绝 `..`、绝对路径、盘符、以分隔符开头的成员）。

同时把 `extraction_thread.py:154` / `:177` 的 `if target_filename in file_path` 子串回退改为对 `os.path.basename(member)` 精确相等匹配；找不到即失败，不再退化为模糊搜索。

### 6.4 hosts 状态模型重写（1 处）

**#30。** 现有 `original_content` 同时扮演「原始快照」与「当前内容缓存」两个角色，这是三条 hosts 缺陷的共同根因（`helpers.py:649` 子串删除、`:660`/`:695` 快照被覆盖、`:811-816` 无条件删备份）。

拆为两个字段：

- **`pristine_content`**：`backup()` 时读入一次，**此后任何路径都不得写它**
- **`current_content`**：每次修改前**重新读盘**（顺带修复「用户运行期间通过菜单编辑 hosts 后改动被静默丢弃」，见 `helpers.py:634-636/668-670/686`）

配套四项：

1. 域名匹配改用 `hosts_text.parse_entries` 的按字段精确比对，不再 `hostname not in line`
2. 标记改为成对块 `# >>> FRAISEMOE BEGIN` / `# <<< FRAISEMOE END`，只删完整块，不再「遇标记则无条件丢弃下一行」（`helpers.py:775-787`）
3. 所有读走 `read_text_with_fallback`（UTF-8 → GBK → latin-1），所有写走 `atomic_write`。这修复中文 Windows 上第三方工具写入 GBK 注释时 `UnicodeDecodeError`（`ValueError` 子类，不被 `except IOError` 捕获）穿透 `shutdown_app` 的问题
4. **`backup()` 在备份文件已存在时不覆盖**——这是干净副本熬过一次异常退出的唯一机制。现状 `main_window.py:51` 每次启动都用当前（可能已污染的）hosts 覆盖备份

**迁移**：老用户 hosts 中可能残留旧格式的单行 `# Added by <APP_NAME>` 标记。`strip_marked_block` 必须**同时识别新块格式与旧单行格式**，否则升级后残留永远清不掉。此项有对应测试（见 §8）。

**启动残留检测**：`main_window.py:51` 调 `backup()` 前先检查备份文件是否存在——存在即表明上次非正常退出，提示用户是否从该备份还原。

### 6.5 生命周期与兜底（4 处）

**#31 异常退出兜底。** 注册 `atexit` 与 `QApplication.aboutToQuit` 执行 hosts 清理。

**须在代码注释与 spec 中同时写明其局限**：任务管理器强杀、崩溃、断电都不会触发这两者。因此 §6.4 的「启动残留检测」才是真正的安全网，两者缺一不可。

**#32 隐私协议撤回路径。** `external_links_handler.py:118-122` 的 `subprocess.Popen(...)` + `sys.exit(0)` 绕过 `closeEvent` / `shutdown_app`，致 hosts 不还原、线程不清理。改走 `shutdown_app(force_exit=True)`；frozen 环境下重启只传 exe，不重复传 `argv[0]`。

**#33 不可中断区间。** py7zr 解压期间**无法**响应中断，这是库的性质，改不了。因此 `graceful_stop_threads`（`download_manager.py:1147`）与 `offline_mode_manager.py:333` 的 `terminate()` 实为常态路径而非兜底，可能在写 `game_folder` 中途杀死线程，留下残缺的 `.xp3`。

设计上引入**不可中断区间**：`ExtractionThread` 在「复制进 `game_folder`」这一段设置标志；`graceful_stop_threads` 命中该标志时**只等待、绝不 terminate**。该区间之外允许放弃线程并丢弃结果。

**代价**：用户点击关闭后，最坏情况需等待一次大文件复制完成（数秒至十余秒）才退出。此代价换取「绝不产生残缺补丁文件」的保证。

**#34 `OfflineHashVerifyThread` 生命周期。** `hash_thread.py:239` 的自定义 `finished` 遮蔽 `QThread` 内置信号，且 `offline_mode_manager.py:317` 只用局部变量持有线程——emit 后仍需执行 `TemporaryDirectory.__exit__` 删除数百 MB 临时文件，此期间引用消失可致 `QThread: Destroyed while thread is still running`。

信号改名 `verify_finished`；线程赋给 `self.hash_thread`（`main_window.py:310` 的 shutdown 因此也能取到它）；清理挂真正的 `QThread.finished`。

---

## 7. 阶段三：提权与打包（5 处）

### 7.1 UAC 提权（#35，严重）

打包版与开发版分开处理：

**打包版**：`build.spec` 的 `EXE()` 加 `uac_admin=True`，由 Windows 清单声明提权需求，命令行由系统构造。此时 exe 启动即已提权，`request_admin_privileges()` 在打包版实际成为空操作——这是干净的终态。

**开发版**（非 frozen）仍需 `runas`，`helpers.py:465` 保留但改三处：

1. `lpParameters` 传 `None`（本程序不接受任何命令行参数）。现状 `" ".join(sys.argv)` 未加引号、未过滤，可被用于向提权实例注入 Qt 参数（如 `-platformpluginpath`）从攻击者可写目录加载 DLL；路径含空格时还会被错误切分
2. `Main.py:77` 改 `QApplication([sys.argv[0]])`，切断 Qt 对外部参数的解析
3. **检查 `ShellExecuteW` 返回值**（现状被完全忽略）：`<= 32` 为失败，`5` 表示用户拒绝 UAC，应分别给出提示

### 7.2 裸文件名调用（#36，高）

三处各有最优解，**不是统一改绝对路径**：

| 位置 | 现状 | 改为 |
|---|---|---|
| `ipv6_manager.py:93, 238` | `["curl", "-6", "6.ipw.cn"]` | **直接换用 `requests`**，不再拉起外部进程，顺带去除对 curl 存在性的依赖 |
| `download.py:53` | `['taskkill', '/F', '/T', '/PID', ...]` | 绝对路径。**但不使用 `os.environ['SystemRoot']`**——那本身是另一条发现（环境变量由父进程决定）。改用 `ctypes` 调 `GetSystemWindowsDirectoryW` |
| `ui_manager.py:262` | `["powershell", "Start-Process", "notepad", hosts_path, "-Verb", "RunAs"]` | 程序此时**已是管理员**，`-Verb RunAs` 整个多余。改 `os.startfile(hosts_path)`，问题自然消失 |

`GetSystemWindowsDirectoryW` 的 helper 同时用于修复 `helpers.py:556` 与 `ui_manager.py:253` 的 hosts 路径拼接。

### 7.3 CI 工作流（#37）

`.github/workflows/build-release.yml`：

1. `:31` 的 `$version = "${{ github.ref_name }}"` 直接插值进 PowerShell。已用 `git check-ref-format` 实测确认 `$(Get-Date)` 与 `v1.0";calc;"` 均为合法 git ref，前者在 PowerShell 双引号内会直接执行子表达式。改为 `env: VERSION: ${{ github.ref_name }}` 配合 `$env:VERSION`
2. 顶层加 `permissions: contents: read`，仅发布步骤提权至 `contents: write`
3. 四个 action 全部钉到 commit SHA（现为可变 major tag）
4. `tags: ['*']` 收窄为 `tags: ['v[0-9]*']`
5. 构建后生成并上传 `.sha256`——一个请求管理员权限、修改 hosts 的安装器必须让用户能验证完整性

验证手段：子项目 1 已加入的 `workflow_dispatch:` 触发器，可手动试跑而不发布 release。

### 7.4 打包配置（#38）

`source/build.spec`：

1. `datas` 删除 `('core','core')`、`('utils','utils')`、`('workers','workers')`、`('ui','ui')`、`('config','config')` 五项——字节码已在 PYZ 中，重复打包 `.py` 源码既泄露源码又撑大体积。保留 `assets` / `data` / `bin`
2. **加入 `('../PRIVACY.md', 'config')`**。放进 `config` 子目录是有意为之：`privacy_policy.py:74` 的第三条候选路径 `os.path.dirname(__file__)` 在冻结环境下解析为 `_MEIPASS/config/`，正好命中，**零代码改动**
3. `upx=True` 改 `upx=False`——UPX 压缩叠加「请求管理员权限 + 修改 hosts」极易触发杀软误报
4. `uac_admin=True`（见 §7.1）

### 7.5 版本契约与文档（#39）

1. CI 增加一步**断言** `config.py:7` 的 `APP_VERSION` 与 `github.ref_name` 一致，不一致则构建失败。**不由 CI 写入**——真值留在仓库，强制维护者显式 bump。该版本号经 `config.py:86` 拼入 UA，而服务端以 UA 做版本门控（`update_required` 流程），不同步会使最新构建被判「版本过低」
2. `FAQ.md:55` 的「FRAISEMOE Addons Installer NEXT.exe」改为构建实际产出的 `FRAISEMOE_Addons_Installer_NEXT.exe`
3. `FAQ.md:210-233` 的 SHA-256 表补上缺失的 NEKOPARA After 条目（`config.py` 中已有该哈希）

---

## 8. 测试策略

### 8.1 红测试转绿分配

子项目 1 的 14 条红测试按阶段转绿：

| 阶段 | 数量 | 测试 |
|---|---|---|
| 一 | **3** | `test_select_members_no_sig_for_non_after`、`test_validate_cloud_config_rejects_non_dict`、`test_load_config_returns_dict_for_list_json` |
| 二 | **11** | hosts 四条、卸载三条、校验两条、`test_select_members_exact_basename`、`test_hosts_manager_backup_reads_gbk_file` |
| 三 | **0** | — |

### 8.2 新增测试

**阶段一**：补写子项目 1 推迟的 8 条 Qt 线程生命周期与窗口状态机测试（子项目 1 spec §8.3 明确将其留到「子项目 3 开工时紧邻编写」，即本阶段）。重点覆盖 §5.1 的退出路径与 §5.2 的看门狗。

**阶段二**：
- manifest 推导与回退白名单（有 manifest / 无 manifest 两条路径）
- `pristine_content` 在 apply → restore 后完整还原用户原有条目
- `strip_marked_block` 同时清除新块格式与**旧单行格式**标记
- 校验失败时**不发生复制**（断言 `game_folder` 中无目标文件）

### 8.3 无法自动化的部分

阶段三**零自动化覆盖**。其验收完全依赖 `tests/MANUAL-CHECKLIST.md`（子项目 1 已建立）的 6 项：

1. UAC 提权参数转发
2. 三处裸文件名的 PATH 劫持
3. CI 标签注入
4. 打包产物是否仍包含 `.py` 源码
5. 内置两个 exe 的签名状态
6. 发布产物是否附带 SHA-256

**报告完成度时，这 6 项须与自动化测试结果分开声明**，不得混入「测试全绿」的表述。

---

## 9. 验收标准

1. `pytest tests/unit` 中子项目 1 的 14 条红测试**全部转绿**，且全部绿测试保持通过。
2. `pytest tests/qt` 全部通过，包含新增的 8 条线程 / 状态机测试。
3. §8.2 的新增测试全部通过。
4. 每阶段的 `git diff` 经逐处人工审查。**阶段二为必需项**——该阶段改动可静默毁坏用户数据，且开发机无法运行应用验证。
5. `MANUAL-CHECKLIST.md` 的 6 项全部执行并记录结果。
6. CI 经 `workflow_dispatch` 试跑成功，产出物包含 `.sha256`，且不含 `.py` 源码。
7. 三阶段各自为独立提交序列，`git bisect` 可用。

**已知缺口**（不阻塞验收，须在交付说明中列出）：

- 代码签名未实施，需要证书
- 优选流程仍为「标志位 + 轮询」模型，未改为信号驱动
- 原子项目 5 的文档一致性（PRIVACY.md 三处与实现不符）未处理

## 10. 风险

| 风险 | 应对 |
|---|---|
| 开发机无法运行应用 | 阶段一、二依靠单元测试 + `git diff` 审查；阶段三**完全**依靠手动清单，报告时单独声明 |
| 阶段二可能静默毁坏用户数据 | 11 条红测试为硬门槛；`git diff` 逐处人工审查列为必需项而非可选 |
| 开启 TLS 校验后部分用户下载失败 | 回退到「放弃优选 + 直连重试」；**绝不回退为关闭校验**，该约束写入代码注释 |
| 三阶段合并后 diff 过大难以审查 | 每阶段独立提交序列；阶段一可独立发布，构成天然的中途止损点 |
| 旧格式 hosts 标记清不掉 | `strip_marked_block` 同时识别新块格式与旧单行格式，有对应测试 |
| 不可中断区间导致退出变慢 | 已知代价，换取「绝不产生残缺补丁文件」；区间仅覆盖复制步骤，不覆盖解压 |
| manifest 与实际文件不一致 | 卸载一律先列实际路径供用户确认；`commonpath` 断言兜底；manifest 缺失时回退白名单 |
