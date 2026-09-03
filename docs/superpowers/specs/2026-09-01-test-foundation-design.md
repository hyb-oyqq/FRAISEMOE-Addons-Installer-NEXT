# 测试地基设计（子项目 1）

日期：2026-09-01
基线：`master` @ `803f32b`
状态：待实现

---

## 1. 背景

对本仓库的安全与质量审查产出 64 条发现（严重 9 / 高 24 / 中 31），其中「严重 + 高」共 33 条需要修复。审查同时确认了两个约束：

- 仓库**零测试**，没有任何测试文件或测试配置。
- 开发机上**运行时依赖全部缺失**（PySide6 / py7zr / requests / psutil），当前无法运行 GUI、下载、解压中的任何一项。

33 条修复中包含若干「改错了会静默毁坏用户数据」的类型——卸载删除范围、hosts 备份还原、校验时机重排。在没有测试也无法运行的前提下直接动手，风险不可接受。

因此确定的交付路径是：**先建立测试与开发环境，后续所有修复都在测试保护下进行。**

## 2. 目标

1. 建立可用的 Python 3.11 开发环境，使应用可被启动、依赖可被安装。
2. 为高危逻辑开出测试接缝——**不改变任何行为**。
3. 写出两类测试：
   - **红测试**：按「修复后应有的行为」编写，当前必须失败。它们构成后续修复的可执行验收清单。
   - **绿测试**：钉住接缝搬运过程中不应改变的行为，当前必须通过。
4. 为无法自动化验证的发现产出一份手动核查清单。

## 3. 非目标

**本子项目不修复任何 bug。**

接缝提取是纯粹的机械搬运：逻辑原样移入新函数，原调用点改为调用该函数。**已知缺陷一并照搬。**

这条约束保证两件事：

- 本子项目的 `git diff` 是可审查的「零行为变更」，在无法运行时验证的情况下这是唯一可靠的正确性论据。
- 红测试是真红——因为缺陷仍然存在。

行为修复属于子项目 2 与 3。

同样不在本子项目范围内：Qt 层与业务逻辑的彻底分层、线程模型重构、状态机重写。

## 4. 在整体拆分中的位置

| # | 子项目 | 内容 | 依赖 |
|---|---|---|---|
| **1** | **测试地基**（本 spec） | 环境、接缝、红绿测试、手动清单 | — |
| 3 | 崩溃与假死 | 退出 AttributeError、下载线程漏停、暂停按钮空方法、重试队列元组、优选轮询死循环、`STATE_ERROR` 死分支、`sig_filename=None`、`installed_status` KeyError、两个漏复制的 action | 1 |
| 2 | 安全热修 | TLS 校验、URL scheme 校验、aria2c `--` 分隔、fail-open 翻转、卸载 manifest、HostsManager 重写 | 1 |
| 4 | 提权与打包 | `uac_admin=True`、裸文件名改绝对路径、CI 标签注入与权限、build.spec 清理、版本号断言 | 1（弱） |
| 5 | 文档一致性 | PRIVACY.md 三处不符、FAQ 文件名与缺失哈希 | 2、4 |

执行顺序为 **1 → 3 → 2 → 4 → 5**。子项目 3 全是确定性小改动，先做它可以在低风险下验证「测试地基 + 修复流程」这套机制，再去处理子项目 2 中会改变数据流的部分。

## 5. 环境

### 5.1 Python 版本

CI 使用 Python 3.11，`requirements.txt` 钉死 `PySide6==6.9.1`（无 3.14 wheel）。开发环境对齐 CI：**Python 3.11**。

开发机当前只有 3.14，需先安装 3.11：

```
winget install Python.Python.3.11
py -3.11 -m venv .venv
```

### 5.2 依赖拆分

经全源码 grep 确认，实际导入的第三方包仅四个：`PySide6`、`requests`、`py7zr`、`psutil`。现有 `requirements.txt` 含约 80 个包，其中 `playwright`、`fastapi`、`uvicorn`、`redis`、`Eel`、`bottle`、`gevent`、`numpy`、`scipy`、`PyQt5`、`colorthief`、`Nuitka`、`auto-py-to-exe` 等零引用。

拆分为三个文件：

| 文件 | 内容 |
|---|---|
| `source/requirements.txt` | 四个运行时依赖，保留原有版本钉死 |
| `requirements-build.txt` | `-r source/requirements.txt` + `pyinstaller`、`pyinstaller-hooks-contrib` |
| `requirements-dev.txt` | `-r requirements-build.txt` + `pytest`、`pytest-qt`、`pytest-cov` |

CI 的安装步骤改为 `pip install -r requirements-build.txt`。

### 5.3 包结构

`source/` 不是 Python 包，模块之间以 `from config.config import ...` 形式互相引用。测试通过 `tests/conftest.py` 将 `source/` 插入 `sys.path` 解决，不改动现有 import 语句。

`conftest.py` 同时设置 `QT_QPA_PLATFORM=offscreen`，使 Qt 测试可在无显示环境运行。

## 6. 目录结构

```
requirements-build.txt
requirements-dev.txt
pytest.ini
tests/
  conftest.py
  unit/
    test_hosts_text.py
    test_uninstall_plan.py
    test_archive_select.py
    test_verification.py
    test_config_validate.py
    test_hash_manager.py
    test_resource_path.py
  qt/
    test_smoke.py
  MANUAL-CHECKLIST.md
source/
  utils/hosts_text.py          # 新
  core/uninstall_plan.py       # 新
  core/verification.py         # 新
  workers/archive_select.py    # 新
  config/validate.py           # 新
```

## 7. 接缝设计

五处接缝。每处都遵循同一规则：**逻辑原样搬运，缺陷一并保留，原位置改为调用。**

### 7.1 `utils/hosts_text.py`

来源：`source/utils/helpers.py` 的 `HostsManager`（`:556` 起）。

```python
def parse_entries(text) -> list[tuple[str, list[str]]]
def find_ips_for_host(text, hostname) -> list[str]
def remove_host_entries(text, hostname) -> str
def add_host_entry(text, hostname, ip, marker) -> str
def strip_marked_block(text, marker) -> str
def read_text_with_fallback(path) -> str
def atomic_write(path, text) -> None
```

搬运对应关系：

- `parse_entries` / `find_ips_for_host` ← `get_hostname_entries`（`helpers.py:593-600`，此处逻辑正确，按字段分词匹配）
- `remove_host_entries` ← `clean_hostname_entries`（`helpers.py:649`）。**照搬现有子串匹配 `hostname not in line`**，缺陷保留。
- `add_host_entry` ← `apply_ip`（`helpers.py:686-695`）
- `strip_marked_block` ← `check_and_clean_all_entries`（`helpers.py:775-787`）。**照搬现有「遇标记则无条件丢弃下一行」逻辑**，缺陷保留。
- `read_text_with_fallback` / `atomic_write`：新增，本轮**仅提供实现，不接入调用点**。接入属子项目 2。现有调用点继续用硬编码 `encoding='utf-8'` 与截断写入。

同时 `HostsManager.__init__` 签名改为：

```python
def __init__(self, hosts_path=None, backup_path=None):
```

默认值保持现有的 `os.environ['SystemRoot']` 拼接结果，**行为不变**，仅使测试可注入临时路径。

### 7.2 `core/uninstall_plan.py`

来源：`source/core/managers/patch_manager.py` 的 `uninstall_patch`（`:108-271`）。

```python
@dataclass
class UninstallPlan:
    files: list[str]
    dirs: list[str]
    reasons: dict[str, str]

def derive_patch_file_candidates(game_dir, install_path_base) -> list[str]
def derive_uninstall_plan(game_dir, game_info, game_version) -> UninstallPlan
```

- `derive_patch_file_candidates` ← `patch_manager.py:119-125`。**照搬对完整路径做 `.lower()` / `.upper()` / `.replace("_", "")` / `.replace("_", "-")` 的现有写法**，缺陷保留。
- `derive_uninstall_plan` 汇总现有全部删除目标：补丁文件与 `.fain` 变体、`.sig` 与 `.fain.sig`、`patch/` 三种大小写、`game/patch/` 九种组合、`game/config.json` 与 `game/scripts.json` 各三种大小写。**照搬现有范围**，缺陷保留。

`uninstall_patch` 重构为三段：算出 plan → 展示 → 执行。展示环节本轮维持现有文案不变（告知内容的修正属子项目 2）。

### 7.3 `workers/archive_select.py`

来源：`source/workers/extraction_thread.py` 的 `run()`（`:100-345`）。

```python
@dataclass
class MemberSelection:
    main: str | None
    sig: str | None
    needs_fallback: bool

def select_members(file_list, target_filename, game_version) -> MemberSelection
def reject_unsafe_members(file_list, dest_dir) -> list[str]
```

- `select_members` ← `extraction_thread.py:130-181`。**照搬 After 特殊分支、`if target_filename in file_path` 子串回退、`basename.endswith('.sig')` 无 break 的写法**，缺陷保留。非 After 版本 `sig` 字段照搬为 `None`。
- `reject_unsafe_members`：新增，本轮**仅提供实现，不接入调用点**。接入属子项目 2。

### 7.4 `core/verification.py`

来源三处 fail-open 判定点。

```python
class Verdict(Enum):
    PASSED
    FAILED
    SKIPPED_NO_PATHS

def decide_post_install(install_paths, hash_results, expected) -> tuple[Verdict, str]
```

统一 `extraction_handler.py:146-151`、`offline_mode_manager.py:553-566`、`hash_thread.py:127-130` 三处。

**本轮 `install_paths` 为空时照搬返回 `PASSED`**（现状即「直接认为安装成功」），缺陷保留。`SKIPPED_NO_PATHS` 枚举值先定义不使用，供子项目 2 翻转时启用。

### 7.5 `config/validate.py`

```python
def coerce_config(data) -> dict
def validate_download_url(url) -> str
def validate_cloud_config(data) -> tuple[dict | None, str]
```

- `coerce_config`：新增，本轮**仅提供实现，不接入** `helpers.py:232` 与 `Main.py:49`。
- `validate_download_url`：新增，本轮**仅提供实现，不接入** `download.py:216`。
- `validate_cloud_config` ← `config_fetch_thread.py:44-60`。照搬现有仅检查顶层键的写法，缺陷保留。

> **接入策略说明**
>
> 五个新增的「修复用」函数（`read_text_with_fallback`、`atomic_write`、`reject_unsafe_members`、`coerce_config`、`validate_download_url`）本轮只写实现，**不接入调用点**。它们本身是新写的正确实现，因此**它们自己的测试是绿的**，用于确认实现无误。
>
> 对应缺陷的红测试另打在**现有调用路径**上——其中两处可通过注入到达（`HostsManager` 注入临时 GBK hosts 文件、`CONFIG_FILE` 指向临时非 dict JSON），本轮即可写成红测试；另两处（`validate_download_url` 接入 `download.py:216`、`reject_unsafe_members` 接入解压流程）在本轮没有可注入的调用点，其验收标准留给子项目 2 定义，本 spec 不虚构覆盖。
>
> 这样既满足「零行为变更」，又让子项目 2 的工作缩减为「把调用点接过去」。

## 8. 测试设计

### 8.1 红测试（当前必须失败）

按「修复后应有的行为」编写。每条对应一个审查发现。

| 测试 | 断言 | 对应发现 |
|---|---|---|
| `test_remove_host_entries_keeps_subdomain` | 清理 `a.com` 不应删除 `cdn.a.com` 所在行 | hosts 子串匹配 |
| `test_remove_host_entries_keeps_comments` | 不应删除纯注释行 | hosts 子串匹配 |
| `test_strip_marked_block_keeps_orphan_neighbor` | 孤儿标记的下一行若非本程序记录，不应被删 | hosts 盲删下一行 |
| `test_hosts_manager_restore_recovers_original` | 注入临时 hosts，apply 后 restore，用户原有条目应完整 | `original_content` 被覆盖 |
| `test_uninstall_plan_excludes_game_config` | plan 不应包含 `game/config.json`、`game/scripts.json` | 卸载超范围 |
| `test_uninstall_plan_excludes_patch_dir` | plan 不应包含 `patch/` 目录 | 卸载超范围 |
| `test_candidates_stay_within_game_dir` | 路径变体不应产生 `game_dir` 之外的路径 | 路径变形误伤 |
| `test_select_members_no_sig_for_non_after` | 非 After 版本，包内任意 `.sig` 不应被选中 | `sig_filename=None` 崩溃 |
| `test_select_members_exact_basename` | `readme_adultsonly.xp3.txt` 不应被选为主补丁 | 子串匹配选错文件 |
| `test_decide_post_install_empty_paths_fails` | `install_paths` 为空应判 `FAILED` | 校验 fail-open |
| `test_decide_post_install_missing_file_fails` | 目标文件不存在应判 `FAILED` | 校验 fail-open |
| `test_validate_cloud_config_rejects_non_dict` | 顶层为 `null` / 数字应返回错误而非抛 `TypeError` | 非 dict JSON 使信号不发 |
| `test_load_config_returns_dict_for_list_json` | `CONFIG_FILE` 内容为 `[]` 时 `load_config()` 应返回 `{}` | `load_config` 类型 |
| `test_hosts_manager_backup_reads_gbk_file` | 注入 GBK 编码的临时 hosts，`backup()` 不应抛 `UnicodeDecodeError` | hosts 编码穿透退出流程 |

预期结果：全部 FAIL。这 14 条构成子项目 2 与 3 的验收清单。

后两条通过注入到达现有调用路径：`test_load_config_returns_dict_for_list_json` 用 `monkeypatch` 改写 `CONFIG_FILE` 指向临时文件；`test_hosts_manager_backup_reads_gbk_file` 用 `HostsManager(hosts_path=tmp)` 注入。

### 8.1.1 本轮无法写红测试的两条

`validate_download_url` 接入 `download.py:216`、`reject_unsafe_members` 接入解压流程——这两处在本轮没有可注入的调用点（前者需先抽出 `build_aria2c_command`，后者需改动 `ExtractionThread.run` 的控制流，均超出「零行为变更」边界）。

其验收标准由子项目 2 的 spec 定义。**本 spec 不为它们虚构测试覆盖。**

### 8.2 绿测试（当前必须通过）

钉住搬运过程中不应改变的行为，作为接缝提取的安全网：

- `parse_entries` / `find_ips_for_host` 对标准 hosts 文本的解析结果
- `add_host_entry` 生成的文本包含 IP、域名与标记行
- `derive_uninstall_plan` 对典型游戏目录返回的补丁文件与 `.fain` 变体
- `select_members` 对规范压缩包（主补丁名精确匹配）的选择结果
- `select_members` 对 After 版本同时选出主补丁与 `.sig`
- `decide_post_install` 在哈希全部匹配时返回 `PASSED`
- `HashManager.hash_calculate` 对已知内容的 SHA-256
- `resource_path` 在非冻结环境下对 `aria2c-fast_x64.exe`、`ip.txt` 的解析结果

以及五个新增「修复用」函数自身的正确性（它们是新实现，不含缺陷，故为绿）：

- `coerce_config` 对 list / str / int / None 均返回 `{}`，对 dict 原样返回
- `validate_download_url` 拒绝 `-` 开头、拒绝 `file://` / `ftp://`、接受 `http(s)://`
- `read_text_with_fallback` 能读出 UTF-8、GBK、带 BOM 三种编码的文件
- `atomic_write` 写入后内容正确，且写入过程中断不会留下半截文件
- `reject_unsafe_members` 拒绝 `../x`、`C:/x`、`/x`、`x/../../y`，放行正常相对路径

### 8.3 Qt 测试

本轮仅搭骨架：`conftest.py` 配置 offscreen，`tests/qt/test_smoke.py` 用 2~3 个用例证明 `QApplication` 可创建、信号可被 `qtbot` 捕获。

线程生命周期与窗口状态机的 8 条测试留到子项目 3 开工时紧邻编写，避免本子项目膨胀。

## 9. 手动核查清单

`tests/MANUAL-CHECKLIST.md` 收录无法自动化验证的发现，写成可勾选步骤：

- UAC 提权参数转发（`-platformpluginpath` 注入）
- 三处裸文件名的 PATH 劫持（`curl` / `taskkill` / `powershell`）
- CI 标签注入（已用 `git check-ref-format` 确认 `$(Get-Date)` 与 `v1.0";calc;"` 均为合法 ref）
- 打包产物是否仍包含 `.py` 源码
- 内置两个 exe 的签名状态
- 发布产物是否附带 SHA-256
- 真实网络环境下的证书校验行为

该清单**不计入测试覆盖率**，其条目在报告完成度时须单独说明。

## 10. CI 改动

现有工作流 `tags: ['*']` + `draft: false`，任何标签推送都直接发布正式 release，无法安全试验 CI 改动。

本轮加入 `workflow_dispatch:` 触发器，使 CI 可手动运行而不发版。安装步骤同时改指向 `requirements-build.txt`。

标签注入、`permissions`、action 钉 SHA 等修复属子项目 4。

## 11. 验收标准

1. `py -3.11 -m venv .venv` 后 `pip install -r requirements-dev.txt` 成功。
2. `python source/Main.py` 能启动到隐私协议对话框（证明依赖拆分未漏）。
3. `pytest tests/unit` 结果为 **14 条红测试全部 FAIL**（数量与名称与 8.1 表格逐条对应）+ **全部绿测试 PASS**。红测试数量少于或多于 14 均视为未通过验收——少了说明漏写，多了说明搬运时意外修好了缺陷（违反非目标）。
4. `pytest tests/qt` 全部通过。
5. `git diff` 经审查确认为零行为变更：新文件为搬运产物，原文件仅有「删除内联逻辑、改为调用」与 `HostsManager.__init__` 签名两类改动。
6. `MANUAL-CHECKLIST.md` 覆盖全部 10 条无法自动化的发现。

## 12. 风险

| 风险 | 应对 |
|---|---|
| 搬运过程意外改变行为，而无法运行时验证 | 绿测试钉住不变量；`git diff` 逐处人工审查；坚持「照搬缺陷」原则，任何「顺手改好」都是违规 |
| Python 3.11 安装受阻 | 退化到 3.13（PySide6 6.9.1 支持），并在 spec 中记录与 CI 的版本偏差 |
| `pytest-qt` 在 offscreen 下不稳定 | Qt 测试本轮仅冒烟；若不稳定则推迟至子项目 3 并改用纯信号断言 |
| 依赖拆分漏掉 CI 需要的包 | 验收标准第 1、2 条覆盖；`workflow_dispatch` 使 CI 可在不发版的前提下试跑 |
| 红测试写错方向（断言了错误的「正确行为」） | 每条红测试在表格中标注对应发现编号，实现前对照审查台账逐条核对 |
