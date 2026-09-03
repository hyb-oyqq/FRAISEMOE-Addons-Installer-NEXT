# 子项目交办事项（来自子项目 1 的执行与审查）

日期：2026-09-03
来源：子项目 1「测试地基」的 10 个任务执行 + 逐任务审查 + 最终整分支审查
状态：待后续子项目消化

---

## 为什么有这份文档

子项目 1 的执行过程中，逐任务审查与最终审查产出了一批**不属于本子项目范围、但后续子项目必须知道**的发现。它们此前只存在于执行工作区的 ledger 中，而工作区在交付后即被删除。

其中若干条是**顺序性陷阱**——按错误顺序做正确的事就会踩雷，且症状难以定位。这类知识丢失的代价远高于保存它的成本。

以下每一条都来自本轮的实证发现，非推测。

---

## 给子项目 2（安全热修）

### ★ 动 `except IOError` 之前，必须先给 conftest 打桩 `msgbox_frame`

**已在子项目 1 中预先处理**（`tests/conftest.py` 的 `_stub_msgbox_frame` autouse fixture），此处记录原因，避免日后有人删掉它。

`QT_QPA_PLATFORM=offscreen` **不会**让 `msg_box.exec()` 立即返回，它照样阻塞等待输入。子项目 1 的 5 条 hosts 红测试恰好全部绕开了带 `exec()` 的分支——`test_hosts_manager_backup_reads_gbk_file` 之所以安全，正是因为 `UnicodeDecodeError` 不被 `except IOError` 捕获、没走进 `backup()` 的弹窗分支。

一旦放宽该 `except` 子句而没有桩，`backup()` 会命中 `helpers.py:690` 一带的 `msg_box.exec()`，**整个 pytest 进程挂起，CI 上表现为超时而非失败**。

### ★ 修复卸载路径变形缺陷时，必须一并处理另外三处同源逻辑

同一份「5 个路径变体」缺陷逻辑在 `patch_manager.py` 中另有三处未纳入接缝：

- `check_patch_installed`（约 `:355-361`）
- `check_patch_disabled`（约 `:451`）
- `toggle_patch`（约 `:531-537`）

只修 `uninstall_patch` 会造成「卸载修好了，而检测／禁用／启用仍按旧变体走」的不一致。

### `atomic_write` 接入时会改变 hosts 行尾风格

`atomic_write` 用 `newline=""`，`\n` 原样落盘；而 `HostsManager` 现有写入走默认文本模式，在 Windows 上 `\n` 会转成 `\r\n`。接入时 hosts 行尾会从 CRLF 变 LF。

`test_atomic_write_writes_content` 已改为 `read_bytes()` 逐字节断言，能钉住这一点——接入后若行尾语义变化，该测试会失败而非静默通过。

### 恢复卸载日志时可用 `plan.reasons`

子项目 1 的接缝提取丢失了这些日志：

- `patch_manager.py:162` 的 `logger.warning("未找到 {game_version} 的补丁文件")`——**WARNING 级且不受 `debug_mode` 门控**。其触发条件与 `files_removed == 0` 不等价：补丁本体未找到但 `game/config.json` 被删时，原逻辑会打该 WARNING 且弹「删除 1 个」。
- 8 类带分类标签的 `logger.debug`（删除补丁文件／被禁用补丁／签名文件／被禁用签名／补丁文件夹／game·patch 文件夹／配置文件／脚本文件）被统一为「删除文件」「删除目录」两类。

`UninstallPlan.reasons[path]` 恰好保存了原分类标签，既能还原分类日志，也能按 reason 过滤精确重建「补丁文件本体是否找到」的判定，不必凭空造逻辑。

### `hash_thread.py` 的对齐与死代码

`core/verification.py` 只接入了两处判定点，`hash_thread.py:127-130` 未接入——其 `after` 分支把哈希计算、进度上报、超时检测与判定耦合在同一循环，用可变 `result` dict 记录状态并以 `break` 提前退出，接入前需先拆成「扫描哈希 → 统一判定」两阶段。

同时 `hash_thread.py:143-149` 有一段因 `:127` 已 `continue` 而永远不可达的死代码，修复 fail-open 时一并清理。

**注意**：由于两个接入点都只会命中 `decide_post_install` 的 `if not install_paths` 提前返回，该函数的判定循环在生产路径上从未执行。其三条绿测试钉的是「子项目 2 应有的行为」而非「`hash_thread.py` 当前的行为」——没有测试同时压住两边。子项目 1 已核对过两边语义当前一致（无预期哈希→跳过；文件不存在→跳过；不匹配→失败并提前退出），翻转时请复核这一前提仍然成立。

### 覆盖缺口

- `validate_cloud_config` 对「非字典但可迭代」输入（str / list）无红测试。这类输入不崩溃，只是把类型错误误判成缺键错误——与 `None`/数字的崩溃路径是不同的缺陷表现。
- `extraction_thread.py:210-216` 的 `os.path.join(game_folder, None)` 崩溃无红测试。该缺陷位于回退提取分支，`select_members` 的返回值契约结构性地无法暴露它，需在子项目 2 的边界内定义验收。
- `MemberSelection.needs_fallback` 的真值语义在接缝（`is None`）与调用点（`if not ...`）之间不一致，成员名为空串时会分歧。该字段生产代码当前未使用。

---

## 给子项目 4（提权与打包）

### ★ 传递依赖钉死已全部丢失，发布构建不再可复现

`source/requirements.txt` 由 `pip freeze` 全量快照（约 80 行，含所有传递依赖精确版本）裁剪为 4 个顶层包。`urllib3`、`certifi`、`charset-normalizer`、`pyzstd`、`shiboken6` 等现在浮动到最新兼容版。

**裁剪本身是正确的**（原文件被开发机污染，混入 playwright、fastapi、redis、scipy 等零引用包；spec §5.2 即如此规定）。可复现性丢失是副作用而非失误。

但这个 CI 产出的是**对外发布的 exe**：上游任一传递依赖发布坏版本，会在仓库零改动的情况下导致构建失败或产出行为不同的二进制，历史发布也无法复现。

正解是引入 lock 文件（`pip-compile` 或 `uv lock`），把「人写的顶层依赖」与「机器生成的完整锁」分开。

### CI 的 pip 缓存键不覆盖传递引用

`requirements-build.txt` 通过 `-r` 引用 `source/requirements.txt`，而 `cache-dependency-path` 只跟踪前者。只修改 `source/requirements.txt` 时 pip 缓存不会失效。

### 标签注入仍未修复

`.github/workflows/build-release.yml:31` 的 `$version = "${{ github.ref_name }}"` 仍是直接插值进 PowerShell。子项目 1 只在该行加了非法字符替换以修复 artifact 命名，**未**改用 `env:` 传值——注入问题属子项目 4 范围。

已实测确认 `git check-ref-format` 接受 `$(Get-Date)` 与 `v1.0";calc;"` 两种形式，前者在 PowerShell 双引号内会直接执行子表达式。

### `workflow_dispatch` 的真实试跑从未执行

子项目 1 只做了 YAML 静态验证。真实手动触发需要把分支推送到公开仓库，超出当时的授权范围。

已知的一个边界：手动触发时若从下拉框选择 **tag** 而非分支，`github.ref` 仍为 `refs/tags/*`，release 步骤仍会执行——这是该场景下用户主动选择的语义，非缺陷。

---

## 上游 spec 自身的问题（供修订时参考）

- `2026-09-01-test-foundation-design.md` §8.1 的红测试表**从未给缺陷 3（After 分支 `.sig` 匹配无 `break`）分配测试**，尽管 §7.3 明确要求照搬该缺陷。子项目 1 执行中已补上（`test_select_members_after_picks_exact_sig_not_last`）。
- §8.1 表格中的 `test_select_members_no_sig_for_non_after` 是重言式——非 After 分支 `sig_filename` 恒为 `None`，`basename == None` 对任意输入恒假，该测试写出来必然是绿的。已被上一条替换。
- §11 验收标准第 6 条写「覆盖全部 10 条无法自动化的发现」，而 §9 正文只列出 7 项。`tests/MANUAL-CHECKLIST.md` 以 §9 正文的 7 项为准，并保留了该差异说明。
- §7.4 定义 `SKIPPED_NO_PATHS`，而 §8.1 对应测试写「应判 `FAILED`」，二者矛盾。实现选择了 §7.4，测试名 `test_decide_post_install_empty_paths_fails` 因此名实不符（断言的是 `SKIPPED_NO_PATHS`）。

---

## 不阻塞的遗留项

- `tests/unit/test_hosts_text.py` 存在 PEP8 E402（import 不在文件顶部）。仓库当前无 linter。
- `pytest-cov` 已安装但 `pytest.ini` 与 CI 均未引用。
- `extraction_thread.py:130` 有一处搬运残留的死赋值（`target_file_in_archive = None` 被下一行立即覆盖）。
- `archive_select.py` 的 After 分支有一个死局部变量 `sig_filename = target_filename + ".sig"`（该分支比对的是字面量）。
- `UninstallPlan.reasons` 目前仅被测试消费，生产代码未使用。
- `MemberSelection.main` / `sig` 的类型标注应为 `Optional[str]`。
- `test_uninstall_plan_excludes_patch_dir` 断言 `plan.dirs == []`，严于 spec 的「不应包含 `patch/`」。若子项目 2 判定某目录确属本程序写入，这条需改写。
- `test_verification.py` 的 `assert Verdict.SKIPPED_NO_PATHS.name == "SKIPPED_NO_PATHS"` 由 Enum 机制保证恒真，只验证了成员存在。
