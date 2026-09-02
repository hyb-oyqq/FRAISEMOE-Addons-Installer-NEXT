# 测试地基 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 FRAISEMOE 安装器建立可运行的 Python 3.11 开发与测试环境，并为 5 处高危逻辑提取测试接缝，产出 14 条红测试作为后续修复的可执行验收清单——全程**不修复任何缺陷**。

**Architecture:** 从 5 个巨型方法中把纯逻辑机械搬运到独立模块（`hosts_text`、`uninstall_plan`、`archive_select`、`verification`、`validate`），原调用点改为调用新函数。搬运遵循「缺陷一并照搬」原则，使 `git diff` 成为可审查的零行为变更。测试分两类：绿测试钉住搬运不应改变的行为，红测试按「修复后应有的行为」编写并以 `xfail(strict=True)` 标记，当缺陷被修复时会 XPASS 从而使构建失败，强制实现者摘除标记。

**Tech Stack:** Python 3.11 · pytest · pytest-qt · PySide6 6.9.1 · py7zr · requests · psutil

**Spec:** `docs/superpowers/specs/2026-09-01-test-foundation-design.md`

## Global Constraints

- **Python 3.11**（与 CI 一致）。若安装受阻，退化到 3.13 并在 README 记录与 CI 的版本偏差。
- **零行为变更是硬约束。** 接缝提取是纯机械搬运，**已知缺陷必须一并照搬**。任何「顺手改好」都是违规，会使红测试变成假红。
- **运行时依赖仅四个**，版本沿用现有钉死值：`PySide6==6.9.1`、`requests==2.32.4`、`py7zr==1.0.0`、`psutil==7.0.0`。
- **不改动 `source/` 下任何现有 `import` 语句。** `source/` 不是 Python 包，测试通过 `tests/conftest.py` 把 `source/` 插入 `sys.path` 解决。
- **`QT_QPA_PLATFORM=offscreen`** 由 `conftest.py` 设置，使 Qt 测试可在无显示环境运行。
- **红测试恰好 14 条。** 少于 14 说明漏写；多于 14 说明搬运时意外修好了缺陷。二者均视为未通过验收。
- 新增的 5 个「修复用」函数（`read_text_with_fallback`、`atomic_write`、`reject_unsafe_members`、`coerce_config`、`validate_download_url`）**只实现、不接入调用点**。接入属子项目 2。

### 关于 `xfail(strict=True)`

Spec §11.3 要求「14 条红测试全部 FAIL」。本计划以 `@pytest.mark.xfail(strict=True, reason=...)` 实现该要求：

- pytest 报告为 `14 xfailed`，数量可精确核对，满足验收标准；
- 测试套件整体保持绿色，因此真实回归不会被 14 条常驻失败淹没；
- **当子项目 2 / 3 修好某个缺陷时，该测试会 XPASS，而 `strict=True` 使 XPASS 成为失败**，强制实现者摘除标记。这正是 spec 所说「构成后续修复的可执行验收清单」的机制。

### 本轮刻意不写红测试的两处

Spec §8.1.1 已认定以下两处在本轮**没有可注入的调用点**，因此不为其虚构测试覆盖。执行时**不要**尝试补写：

| 发现 | 为何本轮写不了 |
|---|---|
| `validate_download_url` 接入 `download.py:216` | 需先把 aria2c 命令行组装抽成 `build_aria2c_command`，超出「零行为变更」边界 |
| `reject_unsafe_members` 接入解压流程 | 需改动 `ExtractionThread.run` 的控制流，同样超出边界 |

二者的**函数自身**有绿测试（它们是新写的正确实现）；其**接入后的**验收标准由子项目 2 的 spec 定义。

---

## Task 1: 开发环境与测试骨架

**Files:**
- Create: `requirements-build.txt`
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`（空文件）
- Create: `tests/qt/__init__.py`（空文件）
- Modify: `source/requirements.txt`（整体重写为四个运行时依赖）

**Interfaces:**
- Consumes: 无
- Produces: `pytest` 可运行；`tests/conftest.py` 使 `from utils.helpers import ...` 等 `source/` 内模块可在测试中直接导入

- [ ] **Step 1: 安装 Python 3.11 并创建虚拟环境**

```bash
winget install Python.Python.3.11
py -3.11 -m venv .venv
```

若 `winget` 不可用或 3.11 安装失败，改用已有的 3.13（PySide6 6.9.1 支持），并在本文件末尾追加一行记录实际使用的版本。

- [ ] **Step 2: 重写 `source/requirements.txt` 为四个运行时依赖**

```
PySide6==6.9.1
requests==2.32.4
py7zr==1.0.0
psutil==7.0.0
```

原文件约 80 个包，其中 `playwright`、`fastapi`、`uvicorn`、`redis`、`Eel`、`bottle`、`gevent`、`numpy`、`scipy`、`PyQt5`、`colorthief`、`Nuitka`、`auto-py-to-exe` 等经全源码 grep 确认零引用。

- [ ] **Step 3: 创建 `requirements-build.txt`**

```
-r source/requirements.txt
pyinstaller==6.14.1
pyinstaller-hooks-contrib==2025.5
```

- [ ] **Step 4: 创建 `requirements-dev.txt`**

```
-r requirements-build.txt
pytest==8.3.4
pytest-qt==4.4.0
pytest-cov==6.0.0
```

- [ ] **Step 5: 创建 `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra --strict-markers
```

`--strict-markers` 保证拼错的 marker 会直接报错，而不是被静默忽略。

- [ ] **Step 6: 创建 `tests/conftest.py`**

```python
"""测试全局配置：使 source/ 下的模块可被导入，并让 Qt 在无显示环境运行。"""

import os
import sys
from pathlib import Path

# source/ 不是 Python 包，其内部模块以 `from config.config import ...` 形式互相引用。
# 把 source/ 插入 sys.path 使这些 import 在测试中同样成立，避免改动现有源码。
SOURCE_DIR = Path(__file__).resolve().parent.parent / "source"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

# Qt 测试在无显示环境（CI、SSH）下运行需要 offscreen 平台插件。
# 必须在任何 PySide6 模块被导入之前设置。
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

- [ ] **Step 7: 创建两个空的包标记文件**

```bash
mkdir -p tests/unit tests/qt
touch tests/unit/__init__.py tests/qt/__init__.py
```

- [ ] **Step 8: 安装依赖并验证 pytest 可运行**

```bash
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest --collect-only
```

Expected: 安装成功；pytest 收集到 0 个测试并正常退出（`no tests ran`），无 import 错误。

- [ ] **Step 9: 验证应用可启动（证明依赖拆分未漏包）**

```bash
.venv/Scripts/python source/Main.py
```

Expected: 弹出隐私协议对话框。确认后关闭应用。若报 `ModuleNotFoundError`，说明 Step 2 删多了包，把缺失的包加回 `source/requirements.txt` 并记录原因。

- [ ] **Step 10: Commit**

```bash
git add requirements-build.txt requirements-dev.txt pytest.ini tests/ source/requirements.txt
git commit -m "test: 建立 Python 3.11 开发环境与 pytest 骨架"
```

---

## Task 2: `config/validate.py` 接缝

**Files:**
- Create: `source/config/validate.py`
- Create: `tests/unit/test_config_validate.py`
- Modify: `source/workers/config_fetch_thread.py:44-60`

**Interfaces:**
- Consumes: Task 1 的 `conftest.py`
- Produces:
  - `coerce_config(data: object) -> dict` — dict 原样返回，其余一切类型返回 `{}`。**本轮不接入调用点。**
  - `validate_download_url(url: object) -> str` — 合法则原样返回该 URL；否则抛 `ValueError`。合法定义：`str` 类型、`urlparse` 后 `scheme in ("http", "https")` 且 `netloc` 非空。**本轮不接入调用点。**
  - `validate_cloud_config(data: object) -> tuple[dict | None, str]` — 返回 `(配置, 错误信息)`。成功时错误信息为 `""`；失败时配置为 `None`。**照搬现有缺陷：仅检查顶层键是否存在，不校验值的类型。**

- [ ] **Step 1: 写绿测试（钉住搬运不应改变的行为 + 两个新函数的正确性）**

```python
# tests/unit/test_config_validate.py
import pytest

from config.validate import coerce_config, validate_download_url, validate_cloud_config

UPDATE_MSG = "\u8bf7\u4f7f\u7528\u6700\u65b0\u7248\u672c\u7684FraiseMoe2-Next\u8fdb\u884c\u4e0b\u8f7d"


def _full_config():
    return {
        "vol.1.data": {"url": "https://example.com/a.7z"},
        "vol.2.data": {"url": "https://example.com/b.7z"},
        "vol.3.data": {"url": "https://example.com/c.7z"},
        "vol.4.data": {"url": "https://example.com/d.7z"},
        "after.data": {"url": "https://example.com/e.7z"},
    }


def test_validate_cloud_config_accepts_full_config():
    config, error = validate_cloud_config(_full_config())
    assert error == ""
    assert config == _full_config()


def test_validate_cloud_config_reports_missing_keys():
    data = _full_config()
    del data["vol.3.data"]
    config, error = validate_cloud_config(data)
    assert config is None
    assert error == "missing_keys:vol.3.data"


def test_validate_cloud_config_detects_update_required_string():
    config, error = validate_cloud_config(UPDATE_MSG)
    assert config is None
    assert error == "update_required"


def test_validate_cloud_config_detects_update_required_message_field():
    config, error = validate_cloud_config({"message": UPDATE_MSG})
    assert config is None
    assert error == "update_required"


@pytest.mark.parametrize("value", [[], "abc", 123, None, 1.5, True])
def test_coerce_config_returns_empty_dict_for_non_dict(value):
    assert coerce_config(value) == {}


def test_coerce_config_passes_dict_through():
    data = {"debug_mode": True}
    assert coerce_config(data) is data


@pytest.mark.parametrize(
    "url",
    ["http://example.com/a.7z", "https://example.com/a.7z", "https://a.b.c/d?e=f"],
)
def test_validate_download_url_accepts_http_and_https(url):
    assert validate_download_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "--conf-path=\\\\attacker\\share\\a.conf",
        "-x",
        "file:///C:/Windows/System32/config/SAM",
        "ftp://example.com/a.7z",
        "example.com/a.7z",
        "",
        None,
        123,
    ],
)
def test_validate_download_url_rejects_everything_else(url):
    with pytest.raises(ValueError):
        validate_download_url(url)
```

- [ ] **Step 2: 运行绿测试确认失败**

Run: `.venv/Scripts/python -m pytest tests/unit/test_config_validate.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'config.validate'`

- [ ] **Step 3: 创建 `source/config/validate.py`**

```python
"""配置与 URL 校验。

`validate_cloud_config` 由 workers/config_fetch_thread.py 搬运而来，
现有缺陷（仅检查顶层键存在性、不校验值类型）一并照搬。

`coerce_config` 与 `validate_download_url` 是为后续修复新增的实现，
本轮只提供实现，不接入任何调用点。
"""

from urllib.parse import urlparse

# 与 workers/config_fetch_thread.py 中的常量保持一致
UPDATE_REQUIRED_MSG = "\u8bf7\u4f7f\u7528\u6700\u65b0\u7248\u672c\u7684FraiseMoe2-Next\u8fdb\u884c\u4e0b\u8f7d"

REQUIRED_KEYS = [f"vol.{i + 1}.data" for i in range(4)] + ["after.data"]


def validate_cloud_config(data):
    """校验云端配置。

    Returns:
        tuple[dict | None, str]: (配置, 错误信息)。成功时错误信息为 ""。

    注意：照搬自 config_fetch_thread.py:44-60，仅检查顶层键是否存在。
    值为 null 或非对象时不会被发现——这是已知缺陷，由子项目 2 修复。
    """
    if isinstance(data, str) and data == UPDATE_REQUIRED_MSG:
        return None, "update_required"
    if isinstance(data, dict) and data.get("message") == UPDATE_REQUIRED_MSG:
        return None, "update_required"

    missing_keys = [key for key in REQUIRED_KEYS if key not in data]
    if missing_keys:
        return None, f"missing_keys:{','.join(missing_keys)}"

    return data, ""


def coerce_config(data):
    """把任意 JSON 反序列化结果收敛为 dict。

    本轮只提供实现，不接入 utils/helpers.py:232 与 Main.py:49。
    """
    if isinstance(data, dict):
        return data
    return {}


def validate_download_url(url):
    """校验下载 URL，合法则原样返回，否则抛 ValueError。

    scheme 白名单按定义排除 "-" 开头的字符串，从而堵住把云端可控值
    作为裸位置参数交给 aria2c 所导致的选项注入。

    本轮只提供实现，不接入 workers/download.py:216。
    """
    if not isinstance(url, str) or not url:
        raise ValueError(f"下载 URL 必须是非空字符串，实际为: {type(url).__name__}")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"下载 URL 的协议必须是 http 或 https，实际为: {parsed.scheme!r}")
    if not parsed.netloc:
        raise ValueError(f"下载 URL 缺少主机名: {url!r}")

    return url
```

- [ ] **Step 4: 运行绿测试确认通过**

Run: `.venv/Scripts/python -m pytest tests/unit/test_config_validate.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 把 `config_fetch_thread.py` 改为调用接缝**

将 `source/workers/config_fetch_thread.py:44-60` 的整段替换为：

```python
            config_data = response.json()

            validated, validate_error = validate_cloud_config(config_data)
            if validate_error:
                self.finished.emit(None, validate_error)
                return
            config_data = validated
```

并在文件顶部的 import 区加入：

```python
from config.validate import validate_cloud_config
```

**不要**在此处添加 `isinstance(config_data, dict)` 检查——那属于子项目 2 的修复。

- [ ] **Step 6: 再次运行绿测试确认行为未变**

Run: `.venv/Scripts/python -m pytest tests/unit/test_config_validate.py -v`
Expected: PASS（全部）

- [ ] **Step 7: 写红测试（2 条）**

追加到 `tests/unit/test_config_validate.py`：

```python
@pytest.mark.xfail(
    strict=True,
    reason="审查发现：仅检查顶层键，值为 null/数字时 `key not in data` 抛 TypeError。子项目 2 修复",
)
@pytest.mark.parametrize("value", [None, 123, "plain string", []])
def test_validate_cloud_config_rejects_non_dict(value):
    config, error = validate_cloud_config(value)
    assert config is None
    assert error != ""


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：load_config 直接返回 json.load 结果，非 dict 时 Main.py:49 崩在 QApplication 之前。子项目 2 修复",
)
def test_load_config_returns_dict_for_list_json(tmp_path, monkeypatch):
    """走注入到达现有调用路径：把 CONFIG_FILE 指向内容为 [] 的临时文件。

    这一条不测 coerce_config（它是新写的、已正确），而是测尚未接入它的
    utils.helpers.load_config——缺陷仍在，故为红。
    """
    cfg = tmp_path / "config.json"
    cfg.write_text("[]", encoding="utf-8")
    monkeypatch.setattr("utils.helpers.CONFIG_FILE", str(cfg))

    from utils.helpers import load_config

    assert load_config() == {}
```

- [ ] **Step 8: 运行确认红测试为 xfail**

Run: `.venv/Scripts/python -m pytest tests/unit/test_config_validate.py -v`
Expected: 绿测试全部 PASS；`test_validate_cloud_config_rejects_non_dict` 显示为 **XFAIL**（4 个参数各一条，计为 1 条红测试项）。**不得出现 XPASS**——出现即说明搬运时意外修好了缺陷。

- [ ] **Step 9: Commit**

```bash
git add source/config/validate.py tests/unit/test_config_validate.py source/workers/config_fetch_thread.py
git commit -m "test: 提取 config/validate.py 接缝并补红绿测试"
```

---

## Task 3: `utils/hosts_text.py` 接缝

**Files:**
- Create: `source/utils/hosts_text.py`
- Create: `tests/unit/test_hosts_text.py`
- Modify: `source/utils/helpers.py`（`HostsManager.__init__` 签名；`get_hostname_entries`、`clean_hostname_entries`、`apply_ip`、`check_and_clean_all_entries` 改为调用接缝）

**Interfaces:**
- Consumes: Task 1 的 `conftest.py`
- Produces:
  - `parse_entries(text: str) -> list[tuple[str, list[str]]]` — 解析非注释非空行为 `(ip, [域名...])`
  - `find_ips_for_host(text: str, hostname: str) -> list[str]`
  - `remove_host_entries(text: str, hostname: str) -> str` — **照搬子串匹配缺陷**
  - `add_host_entry(text: str, hostname: str, ip: str, marker: str) -> str`
  - `strip_marked_block(text: str, marker: str) -> str` — **照搬「遇标记则无条件丢弃下一行」缺陷**
  - `read_text_with_fallback(path: str) -> str` — utf-8 → gbk → latin-1。**本轮不接入调用点。**
  - `atomic_write(path: str, text: str) -> None` — 同目录临时文件 + `os.replace`。**本轮不接入调用点。**
  - `HostsManager.__init__(self, hosts_path=None, backup_path=None)` — 默认值保持现有 `os.environ['SystemRoot']` 拼接结果，行为不变，仅使测试可注入临时路径

- [ ] **Step 1: 写绿测试**

```python
# tests/unit/test_hosts_text.py
import os

import pytest

from utils.hosts_text import (
    add_host_entry,
    atomic_write,
    find_ips_for_host,
    parse_entries,
    read_text_with_fallback,
    remove_host_entries,
    strip_marked_block,
)

MARKER = "# Added by FRAISEMOE Addons Installer NEXT"

SAMPLE = """\
# Copyright (c) 1993-2009 Microsoft Corp.
127.0.0.1       localhost
::1             localhost

104.16.0.1      example.com
104.16.0.2      cdn.example.com  alias.example.com
"""


def test_parse_entries_skips_comments_and_blanks():
    entries = parse_entries(SAMPLE)
    assert ("127.0.0.1", ["localhost"]) in entries
    assert ("104.16.0.2", ["cdn.example.com", "alias.example.com"]) in entries
    assert all(not ip.startswith("#") for ip, _ in entries)
    assert len(entries) == 4


def test_find_ips_for_host_matches_exact_domain_field():
    assert find_ips_for_host(SAMPLE, "example.com") == ["104.16.0.1"]
    assert find_ips_for_host(SAMPLE, "alias.example.com") == ["104.16.0.2"]
    assert find_ips_for_host(SAMPLE, "nope.example.com") == []


def test_add_host_entry_appends_marker_and_record():
    result = add_host_entry(SAMPLE, "example.com", "1.2.3.4", MARKER)
    assert MARKER in result
    assert "1.2.3.4\texample.com" in result
    # 原有内容不应丢失
    assert "127.0.0.1       localhost" in result


def test_strip_marked_block_removes_marker_and_its_record():
    text = add_host_entry(SAMPLE, "example.com", "1.2.3.4", MARKER)
    result = strip_marked_block(text, MARKER)
    assert MARKER not in result
    assert "1.2.3.4\texample.com" not in result


def test_read_text_with_fallback_reads_utf8(tmp_path):
    p = tmp_path / "hosts"
    p.write_bytes("127.0.0.1 本机\n".encode("utf-8"))
    assert "本机" in read_text_with_fallback(str(p))


def test_read_text_with_fallback_reads_gbk(tmp_path):
    p = tmp_path / "hosts"
    p.write_bytes("127.0.0.1 本机\n".encode("gbk"))
    assert "本机" in read_text_with_fallback(str(p))


def test_read_text_with_fallback_reads_utf8_bom(tmp_path):
    p = tmp_path / "hosts"
    p.write_bytes("\ufeff127.0.0.1 localhost\n".encode("utf-8"))
    assert "localhost" in read_text_with_fallback(str(p))


def test_atomic_write_writes_content(tmp_path):
    p = tmp_path / "hosts"
    atomic_write(str(p), "127.0.0.1 localhost\n")
    assert p.read_text(encoding="utf-8") == "127.0.0.1 localhost\n"


def test_atomic_write_leaves_no_temp_file_behind(tmp_path):
    p = tmp_path / "hosts"
    atomic_write(str(p), "content\n")
    assert [f.name for f in tmp_path.iterdir()] == ["hosts"]
```

- [ ] **Step 2: 运行绿测试确认失败**

Run: `.venv/Scripts/python -m pytest tests/unit/test_hosts_text.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'utils.hosts_text'`

- [ ] **Step 3: 创建 `source/utils/hosts_text.py`**

```python
"""hosts 文件的纯文本处理。

parse_entries / find_ips_for_host 搬运自 HostsManager.get_hostname_entries
（该处逻辑正确，按字段分词匹配）。

remove_host_entries 搬运自 HostsManager.clean_hostname_entries，
**照搬其整行子串匹配缺陷**——它会误删 cdn.<域名> 与注释行。

strip_marked_block 搬运自 HostsManager.check_and_clean_all_entries，
**照搬其「遇标记则无条件丢弃下一行」缺陷**。

read_text_with_fallback 与 atomic_write 是为后续修复新增的实现，
本轮只提供实现，不接入任何调用点。
"""

import os
import tempfile


def parse_entries(text):
    """把 hosts 文本解析为 [(ip, [域名...]), ...]，跳过空行与注释行。"""
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            entries.append((parts[0], parts[1:]))
    return entries


def find_ips_for_host(text, hostname):
    """返回 hosts 文本中指定域名对应的全部 IP。按域名字段精确比对。"""
    return [ip for ip, domains in parse_entries(text) if hostname in domains]


def remove_host_entries(text, hostname):
    """移除包含指定域名的行。

    注意：照搬 clean_hostname_entries 的整行子串匹配。
    这会连带删除 cdn.<hostname>、<hostname>.lan 以及提及该域名的注释行。
    这是已知缺陷，由子项目 2 修复。
    """
    lines = text.splitlines()
    new_lines = [line for line in lines if hostname not in line]
    return "\n".join(new_lines)


def add_host_entry(text, hostname, ip, marker):
    """追加一条带标记的 hosts 记录。搬运自 apply_ip。"""
    lines = text.splitlines()
    lines.append(f"\n{marker}")
    lines.append(f"{ip}\t{hostname}")
    return "\n".join(lines)


def strip_marked_block(text, marker):
    """移除标记行及其下一行。

    注意：照搬 check_and_clean_all_entries 的实现——遇到标记行即
    无条件丢弃紧随其后的一行，不校验该行是否真是本程序写入的记录。
    孤儿标记会导致用户自己的条目被误删。这是已知缺陷，由子项目 2 修复。
    """
    lines = text.splitlines()
    new_lines = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        if marker in line:
            skip_next = True
            continue
        new_lines.append(line)
    return "\n".join(new_lines)


def read_text_with_fallback(path):
    """按 utf-8 → gbk → latin-1 顺序尝试读取文本文件。

    中文 Windows 上第三方工具常往 hosts 写入 GBK 编码的中文注释，
    硬编码 utf-8 会抛 UnicodeDecodeError（ValueError 子类，不被 except IOError 捕获）。

    本轮只提供实现，不接入 HostsManager 的任何读取点。
    """
    for encoding in ("utf-8-sig", "gbk", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    # latin-1 能解码任意字节序列，理论上不会走到这里
    raise UnicodeDecodeError("utf-8", b"", 0, 1, f"无法解码文件: {path}")


def atomic_write(path, text):
    """原子写入：先写同目录临时文件，再 os.replace 覆盖目标。

    避免「截断后写入中途崩溃」留下空文件或半截内容。

    本轮只提供实现，不接入 HostsManager 的任何写入点。
    """
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".hosts_tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
```

- [ ] **Step 4: 运行绿测试确认通过**

Run: `.venv/Scripts/python -m pytest tests/unit/test_hosts_text.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 改造 `HostsManager` 以调用接缝并支持路径注入**

在 `source/utils/helpers.py` 顶部 import 区加入：

```python
from utils.hosts_text import (
    add_host_entry,
    find_ips_for_host,
    strip_marked_block,
    remove_host_entries,
)
```

把 `HostsManager.__init__`（`helpers.py:555` 起）改为：

```python
    def __init__(self, hosts_path=None, backup_path=None):
        # 默认值保持原有行为不变，参数仅供测试注入临时路径
        self.hosts_path = hosts_path or os.path.join(
            os.environ['SystemRoot'], 'System32', 'drivers', 'etc', 'hosts'
        )
        self.backup_path = backup_path or os.path.join(
            os.path.dirname(self.hosts_path), f'hosts.bak.{APP_NAME}'
        )
        self.original_content = None
        self.modified = False
        self.modified_hostnames = set()
        self.auto_restore_disabled = False
```

在四个方法内部，把内联的文本处理替换为接缝调用，**其余逻辑一律不动**：

- `get_hostname_entries` 的解析循环 → `return find_ips_for_host(self.original_content, hostname)`
- `clean_hostname_entries` 的 `new_lines = [line for line in lines if hostname not in line]` 及后续 join → `new_content = remove_host_entries(self.original_content, hostname)`；保留「若长度未变则不写入」的短路判断，改为比较 `new_content != self.original_content`
- `apply_ip` 的 `lines.append(...)` 三行 → `new_content = add_host_entry(self.original_content, hostname, ip_address, f"# Added by {APP_NAME}")`
- `check_and_clean_all_entries` 的 skip_next 循环 → `new_content = strip_marked_block(current_content, f"# Added by {APP_NAME}")`

**不要**改动编码、异常捕获范围、`original_content` 的赋值时机或备份删除逻辑——那些都是子项目 2 的修复范围。

- [ ] **Step 6: 再次运行绿测试确认行为未变**

Run: `.venv/Scripts/python -m pytest tests/unit/test_hosts_text.py -v`
Expected: PASS（全部）

- [ ] **Step 7: 写红测试（5 条）**

追加到 `tests/unit/test_hosts_text.py`：

```python
from config.config import APP_NAME
from utils.helpers import HostsManager

APP_MARKER = f"# Added by {APP_NAME}"

WITH_SUBDOMAIN = """\
127.0.0.1       localhost
1.1.1.1         cdn.example.com
2.2.2.2         example.com
"""

WITH_COMMENT = """\
127.0.0.1       localhost
# 屏蔽 example.com 用
2.2.2.2         other.org
"""


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：remove_host_entries 用整行子串匹配，会误删 cdn.<域名>。子项目 2 修复",
)
def test_remove_host_entries_keeps_subdomain():
    result = remove_host_entries(WITH_SUBDOMAIN, "example.com")
    assert "cdn.example.com" in result
    assert "2.2.2.2         example.com" not in result


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：remove_host_entries 会删除仅提及该域名的注释行。子项目 2 修复",
)
def test_remove_host_entries_keeps_comments():
    result = remove_host_entries(WITH_COMMENT, "example.com")
    assert "# 屏蔽 example.com 用" in result


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：strip_marked_block 无条件丢弃标记行的下一行。子项目 2 修复",
)
def test_strip_marked_block_keeps_orphan_neighbor():
    # 孤儿标记：标记行存在，但其后并非本程序写入的记录
    text = f"127.0.0.1 localhost\n{APP_MARKER}\n9.9.9.9 user-own-entry.com\n"
    result = strip_marked_block(text, APP_MARKER)
    assert "9.9.9.9 user-own-entry.com" in result


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：apply_ip 覆盖 original_content，restore 写回的是已修改内容。子项目 2 修复",
)
def test_hosts_manager_restore_recovers_original(tmp_path, monkeypatch):
    hosts = tmp_path / "hosts"
    original = "127.0.0.1 localhost\n5.5.5.5 example.com\n"
    hosts.write_text(original, encoding="utf-8")

    manager = HostsManager(
        hosts_path=str(hosts), backup_path=str(tmp_path / "hosts.bak")
    )
    # 绕过管理员权限检查与自动还原开关，只验证内容语义
    monkeypatch.setattr(manager, "is_auto_restore_disabled", lambda: False)
    monkeypatch.setattr("utils.helpers.AdminPrivileges.is_admin", lambda self: True)

    manager.backup()
    manager.apply_ip("example.com", "1.2.3.4")
    manager.restore()

    assert "5.5.5.5 example.com" in hosts.read_text(encoding="utf-8")
```

追加第 4 条红测试（GBK 编码，走注入到达现有调用路径）：

```python
@pytest.mark.xfail(
    strict=True,
    reason="审查发现：hosts 读写硬编码 utf-8 且只捕获 IOError，GBK 内容抛 UnicodeDecodeError 穿透。子项目 2 修复",
)
def test_hosts_manager_backup_reads_gbk_file(tmp_path, monkeypatch):
    hosts = tmp_path / "hosts"
    hosts.write_bytes("127.0.0.1 localhost\n# 加速器写入的中文注释\n".encode("gbk"))

    manager = HostsManager(
        hosts_path=str(hosts), backup_path=str(tmp_path / "hosts.bak")
    )
    monkeypatch.setattr("utils.helpers.AdminPrivileges.is_admin", lambda self: True)

    assert manager.backup() is True
```

> 本任务共 5 条红测试。Spec §8.1 表格把 GBK 一条单列，此处与之一致。

- [ ] **Step 8: 运行确认红测试为 xfail**

Run: `.venv/Scripts/python -m pytest tests/unit/test_hosts_text.py -v`
Expected: 绿测试全部 PASS；5 条红测试全部 **XFAIL**，无 XPASS。

- [ ] **Step 9: Commit**

```bash
git add source/utils/hosts_text.py source/utils/helpers.py tests/unit/test_hosts_text.py
git commit -m "test: 提取 utils/hosts_text.py 接缝并补红绿测试"
```

---

## Task 4: `core/uninstall_plan.py` 接缝

**Files:**
- Create: `source/core/uninstall_plan.py`
- Create: `tests/unit/test_uninstall_plan.py`
- Modify: `source/core/managers/patch_manager.py:108-271`（`uninstall_patch` 重构为「算 plan → 展示 → 执行」三段）

**Interfaces:**
- Consumes: Task 1 的 `conftest.py`
- Produces:
  - `UninstallPlan` dataclass，字段 `files: list[str]`、`dirs: list[str]`、`reasons: dict[str, str]`
  - `derive_patch_file_candidates(game_dir: str, install_path_base: str) -> list[str]` — **照搬对完整路径做 `.lower()` / `.upper()` / `.replace("_", "")` / `.replace("_", "-")` 的缺陷**
  - `derive_uninstall_plan(game_dir: str, game_info: dict, game_version: str) -> UninstallPlan` — **照搬现有全部删除范围**（含 `patch/`、`game/patch/`、`game/config.json`、`game/scripts.json`）

- [ ] **Step 1: 写绿测试**

```python
# tests/unit/test_uninstall_plan.py
import os

import pytest

from core.uninstall_plan import (
    UninstallPlan,
    derive_patch_file_candidates,
    derive_uninstall_plan,
)

GAME_INFO = {
    "NEKOPARA Vol.1": {
        "exe": "nekopara_vol1.exe",
        "install_path": "NEKOPARA Vol. 1/adultsonly.xp3",
        "plugin_path": "vol.1/adultsonly.xp3",
    },
    "NEKOPARA After": {
        "exe": "nekopara_after.exe",
        "install_path": "NEKOPARA After/afteradult.xp3",
        "plugin_path": "after/afteradult.xp3",
        "sig_path": "after/afteradult.xp3.sig",
    },
}


def test_candidates_include_base_and_case_variants():
    candidates = derive_patch_file_candidates(r"D:\Games\Vol1", "adultsonly.xp3")
    base = os.path.join(r"D:\Games\Vol1", "adultsonly.xp3")
    assert base in candidates
    assert base.lower() in candidates
    assert base.upper() in candidates


def test_plan_includes_patch_file_and_fain_variant():
    plan = derive_uninstall_plan(r"D:\Games\Vol1", GAME_INFO, "NEKOPARA Vol.1")
    base = os.path.join(r"D:\Games\Vol1", "adultsonly.xp3")
    assert base in plan.files
    assert f"{base}.fain" in plan.files


def test_plan_includes_sig_only_for_after():
    after = derive_uninstall_plan(r"D:\Games\After", GAME_INFO, "NEKOPARA After")
    base = os.path.join(r"D:\Games\After", "afteradult.xp3")
    assert f"{base}.sig" in after.files
    assert f"{base}.fain.sig" in after.files

    vol1 = derive_uninstall_plan(r"D:\Games\Vol1", GAME_INFO, "NEKOPARA Vol.1")
    assert not any(p.endswith(".sig") for p in vol1.files)


def test_plan_returns_dataclass_with_reasons():
    plan = derive_uninstall_plan(r"D:\Games\Vol1", GAME_INFO, "NEKOPARA Vol.1")
    assert isinstance(plan, UninstallPlan)
    assert all(p in plan.reasons for p in plan.files)
```

- [ ] **Step 2: 运行绿测试确认失败**

Run: `.venv/Scripts/python -m pytest tests/unit/test_uninstall_plan.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'core.uninstall_plan'`

- [ ] **Step 3: 创建 `source/core/uninstall_plan.py`**

```python
"""卸载计划推导。

搬运自 core/managers/patch_manager.py 的 uninstall_patch(:108-271)。

**照搬两处已知缺陷**：
1. derive_patch_file_candidates 对完整路径（而非文件名）做大小写与下划线变形，
   游戏装在 D:\\game_lib\\ 时会生成指向 D:\\gamelib\\ 的路径。
2. derive_uninstall_plan 包含 patch/、game/patch/、game/config.json、
   game/scripts.json——这些从来不是本程序写入的。

二者均由子项目 2 修复。
"""

import os
from dataclasses import dataclass, field


@dataclass
class UninstallPlan:
    """一次卸载操作的待删清单。"""

    files: list = field(default_factory=list)
    dirs: list = field(default_factory=list)
    reasons: dict = field(default_factory=dict)


def derive_patch_file_candidates(game_dir, install_path_base):
    """推导补丁文件的候选路径。

    注意：照搬 patch_manager.py:119-125，变形作用于**完整路径**而非文件名。
    这是已知缺陷，由子项目 2 修复。
    """
    patch_file_path = os.path.join(game_dir, install_path_base)
    return [
        patch_file_path,
        patch_file_path.lower(),
        patch_file_path.upper(),
        patch_file_path.replace("_", ""),
        patch_file_path.replace("_", "-"),
    ]


def derive_uninstall_plan(game_dir, game_info, game_version):
    """推导一次卸载要删除的全部文件与目录。

    注意：照搬 patch_manager.py:194-271 的全部删除范围，
    包括本程序从未写入过的 patch/ 目录与 game/config.json。
    这是已知缺陷，由子项目 2 修复。
    """
    plan = UninstallPlan()

    def add_file(path, reason):
        if path not in plan.files:
            plan.files.append(path)
            plan.reasons[path] = reason

    def add_dir(path, reason):
        if path not in plan.dirs:
            plan.dirs.append(path)
            plan.reasons[path] = reason

    install_path_base = os.path.basename(game_info[game_version]["install_path"])
    candidates = derive_patch_file_candidates(game_dir, install_path_base)

    for patch_path in candidates:
        add_file(patch_path, "补丁文件")
        add_file(f"{patch_path}.fain", "被禁用的补丁文件")

    if game_version == "NEKOPARA After":
        for patch_path in candidates:
            add_file(f"{patch_path}.sig", "签名文件")
            add_file(f"{patch_path}.fain.sig", "被禁用补丁的签名文件")

    for name in ("patch", "Patch", "PATCH"):
        add_dir(os.path.join(game_dir, name), "补丁文件夹")

    game_folders = ("game", "Game", "GAME")
    patch_folders = ("patch", "Patch", "PATCH")
    for game_folder in game_folders:
        for patch_folder in patch_folders:
            add_dir(os.path.join(game_dir, game_folder, patch_folder), "game/patch 文件夹")

    for game_folder in game_folders:
        game_path = os.path.join(game_dir, game_folder)
        for config_file in ("config.json", "Config.json", "CONFIG.JSON"):
            add_file(os.path.join(game_path, config_file), "配置文件")
        for script_file in ("scripts.json", "Scripts.json", "SCRIPTS.JSON"):
            add_file(os.path.join(game_path, script_file), "脚本文件")

    return plan
```

- [ ] **Step 4: 运行绿测试确认通过**

Run: `.venv/Scripts/python -m pytest tests/unit/test_uninstall_plan.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 把 `uninstall_patch` 重构为三段**

在 `source/core/managers/patch_manager.py` 顶部加入：

```python
from core.uninstall_plan import derive_uninstall_plan
```

把 `uninstall_patch`（`:108-271`）中「推导路径 + 逐个删除」的内联代码替换为：

```python
            plan = derive_uninstall_plan(game_dir, self.game_info, game_version)

            files_removed = 0
            for path in plan.files:
                if os.path.exists(path):
                    self.logger.debug(f"删除文件: {path}")
                    os.remove(path)
                    files_removed += 1
            for path in plan.dirs:
                if os.path.exists(path):
                    self.logger.debug(f"删除目录: {path}")
                    shutil.rmtree(path)
                    files_removed += 1
```

**展示环节本轮维持现有文案不变**——把待删清单展示给用户确认属子项目 2 的修复。`patch_file_found` 相关的日志分支可保留或按上述计数改写，但**删除范围必须与改造前完全一致**。

- [ ] **Step 6: 再次运行绿测试确认行为未变**

Run: `.venv/Scripts/python -m pytest tests/unit/test_uninstall_plan.py -v`
Expected: PASS（全部）

- [ ] **Step 7: 写红测试（3 条）**

追加到 `tests/unit/test_uninstall_plan.py`：

```python
@pytest.mark.xfail(
    strict=True,
    reason="审查发现：卸载会删除本程序从未写入的 game/config.json 与 scripts.json。子项目 2 修复",
)
def test_uninstall_plan_excludes_game_config():
    plan = derive_uninstall_plan(r"D:\Games\Vol1", GAME_INFO, "NEKOPARA Vol.1")
    assert not any(p.endswith(("config.json", "Config.json", "CONFIG.JSON")) for p in plan.files)
    assert not any(p.endswith(("scripts.json", "Scripts.json", "SCRIPTS.JSON")) for p in plan.files)


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：卸载会 rmtree 整个 patch/ 与 game/patch/ 目录。子项目 2 修复",
)
def test_uninstall_plan_excludes_patch_dir():
    plan = derive_uninstall_plan(r"D:\Games\Vol1", GAME_INFO, "NEKOPARA Vol.1")
    assert plan.dirs == []


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：路径变体作用于完整路径，可生成 game_dir 之外的路径。子项目 2 修复",
)
def test_candidates_stay_within_game_dir():
    game_dir = r"D:\game_lib\Vol1"
    candidates = derive_patch_file_candidates(game_dir, "adultsonly.xp3")
    for path in candidates:
        assert os.path.commonpath([game_dir, path]) == game_dir
```

- [ ] **Step 8: 运行确认红测试为 xfail**

Run: `.venv/Scripts/python -m pytest tests/unit/test_uninstall_plan.py -v`
Expected: 绿测试全部 PASS；3 条红测试全部 **XFAIL**，无 XPASS。

- [ ] **Step 9: Commit**

```bash
git add source/core/uninstall_plan.py source/core/managers/patch_manager.py tests/unit/test_uninstall_plan.py
git commit -m "test: 提取 core/uninstall_plan.py 接缝并补红绿测试"
```

---

## Task 5: `workers/archive_select.py` 接缝

**Files:**
- Create: `source/workers/archive_select.py`
- Create: `tests/unit/test_archive_select.py`
- Modify: `source/workers/extraction_thread.py:130-181`

**Interfaces:**
- Consumes: Task 1 的 `conftest.py`
- Produces:
  - `MemberSelection` dataclass，字段 `main: str | None`、`sig: str | None`、`needs_fallback: bool`
  - `select_members(file_list: list[str], target_filename: str, game_version: str) -> MemberSelection` — **照搬 After 特殊分支、`in` 子串回退、`.sig` 无 break 的缺陷**。非 After 版本 `sig` 字段照搬为 `None`
  - `reject_unsafe_members(file_list: list[str], dest_dir: str) -> list[str]` — 返回**被拒绝的**成员名列表，空列表表示全部安全。**本轮不接入调用点。**

- [ ] **Step 1: 写绿测试**

```python
# tests/unit/test_archive_select.py
import pytest

from workers.archive_select import MemberSelection, reject_unsafe_members, select_members


def test_select_members_exact_match_for_vol1():
    result = select_members(["vol.1/adultsonly.xp3"], "adultsonly.xp3", "NEKOPARA Vol.1")
    assert isinstance(result, MemberSelection)
    assert result.main == "vol.1/adultsonly.xp3"
    assert result.needs_fallback is False


def test_select_members_after_picks_main_and_sig():
    files = ["after/afteradult.xp3", "after/afteradult.xp3.sig"]
    result = select_members(files, "afteradult.xp3", "NEKOPARA After")
    assert result.main == "after/afteradult.xp3"
    assert result.sig == "after/afteradult.xp3.sig"


def test_select_members_flags_fallback_when_nothing_matches():
    result = select_members(["readme.txt"], "adultsonly.xp3", "NEKOPARA Vol.1")
    assert result.main is None
    assert result.needs_fallback is True


@pytest.mark.parametrize(
    "member",
    ["../evil.xp3", "a/../../evil.xp3", "C:/Windows/evil.xp3", "/etc/passwd", "\\\\server\\share\\x"],
)
def test_reject_unsafe_members_rejects_traversal(member):
    assert reject_unsafe_members([member], r"D:\temp\extract") == [member]


def test_reject_unsafe_members_allows_normal_relative_paths():
    safe = ["vol.1/adultsonly.xp3", "after/afteradult.xp3.sig", "readme.txt"]
    assert reject_unsafe_members(safe, r"D:\temp\extract") == []
```

- [ ] **Step 2: 运行绿测试确认失败**

Run: `.venv/Scripts/python -m pytest tests/unit/test_archive_select.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'workers.archive_select'`

- [ ] **Step 3: 创建 `source/workers/archive_select.py`**

```python
"""从压缩包成员列表中挑选待安装文件。

select_members 搬运自 workers/extraction_thread.py:130-181。

**照搬三处已知缺陷**：
1. 非 After 版本的 sig 字段恒为 None，而调用方对任意 .sig 都会命中；
2. 主补丁的宽松回退用 `target_filename in file_path` 子串匹配，
   readme_adultsonly.xp3.txt 之类会被选中；
3. After 分支的 .sig 匹配没有 break，取到的是列表中最后一个 .sig。

三者均由子项目 2 修复。

reject_unsafe_members 是为后续修复新增的实现，本轮只提供实现，不接入调用点。
"""

import os
from dataclasses import dataclass


@dataclass
class MemberSelection:
    """一次压缩包成员挑选的结果。"""

    main: str = None
    sig: str = None
    needs_fallback: bool = False


def select_members(file_list, target_filename, game_version):
    """从成员列表中挑出主补丁与签名文件。

    注意：照搬 extraction_thread.py:130-181 的全部匹配逻辑与缺陷。
    """
    target_file_in_archive = None
    sig_file_in_archive = None

    if game_version == "NEKOPARA After":
        sig_filename = target_filename + ".sig"
        for file_path in file_list:
            basename = os.path.basename(file_path)
            if basename == "afteradult.xp3" and not basename.endswith(".sig"):
                target_file_in_archive = file_path
            elif basename == "afteradult.xp3.sig" or basename.endswith(".sig"):
                # 照搬：此处没有 break，取到的是最后一个 .sig
                sig_file_in_archive = file_path

        if not target_file_in_archive:
            for file_path in file_list:
                if "afteradult.xp3" in file_path and not file_path.endswith(".sig"):
                    target_file_in_archive = file_path
                    break
    else:
        # 照搬：非 After 版本 sig_filename 为 None
        sig_filename = None
        for file_path in file_list:
            basename = os.path.basename(file_path)
            if basename == target_filename and not basename.endswith(".sig"):
                target_file_in_archive = file_path
            elif basename == sig_filename:
                sig_file_in_archive = file_path

        if not target_file_in_archive:
            # 照搬：子串匹配的宽松回退
            for file_path in file_list:
                if target_filename in file_path and not file_path.endswith(".sig"):
                    target_file_in_archive = file_path
                    break

    return MemberSelection(
        main=target_file_in_archive,
        sig=sig_file_in_archive,
        needs_fallback=target_file_in_archive is None,
    )


def reject_unsafe_members(file_list, dest_dir):
    """返回会写出 dest_dir 之外的成员名列表。空列表表示全部安全。

    拒绝：绝对路径、盘符、UNC 路径、以分隔符开头、以及归一化后逃出 dest_dir 的路径。

    本轮只提供实现，不接入 extraction_thread.py 的解压调用点。
    """
    rejected = []
    dest_real = os.path.realpath(dest_dir)

    for member in file_list:
        normalized = member.replace("\\", "/")

        if os.path.isabs(member) or normalized.startswith("/"):
            rejected.append(member)
            continue
        if len(member) >= 2 and member[1] == ":":
            rejected.append(member)
            continue
        if normalized.startswith("//"):
            rejected.append(member)
            continue

        target = os.path.realpath(os.path.join(dest_real, member))
        if os.path.commonpath([dest_real, target]) != dest_real:
            rejected.append(member)

    return rejected
```

- [ ] **Step 4: 运行绿测试确认通过**

Run: `.venv/Scripts/python -m pytest tests/unit/test_archive_select.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 把 `extraction_thread.py` 改为调用接缝**

在 `source/workers/extraction_thread.py` 顶部加入：

```python
from workers.archive_select import select_members
```

把 `:130-181` 整段匹配逻辑替换为：

```python
                    selection = select_members(file_list, target_filename, self.game_version)
                    target_file_in_archive = selection.main
                    sig_file_in_archive = selection.sig
```

`sig_filename` 变量在 `:120-127` 的赋值保持不动——后续 `:210`、`:216`、`:334` 仍在使用它，本轮不得改变其取值。

- [ ] **Step 6: 再次运行绿测试确认行为未变**

Run: `.venv/Scripts/python -m pytest tests/unit/test_archive_select.py -v`
Expected: PASS（全部）

- [ ] **Step 7: 写红测试（2 条）**

追加到 `tests/unit/test_archive_select.py`：

```python
@pytest.mark.xfail(
    strict=True,
    reason="审查发现：非 After 版本 sig 恒为 None，调用方却对任意 .sig 命中致 join(None) 崩溃。子项目 2/3 修复",
)
def test_select_members_no_sig_for_non_after():
    files = ["vol.1/adultsonly.xp3", "vol.1/unrelated.sig"]
    result = select_members(files, "adultsonly.xp3", "NEKOPARA Vol.1")
    assert result.sig is None
    # 修复后：非 After 版本不应把任何 .sig 视为待安装文件
    assert not any(f.endswith(".sig") for f in filter(None, [result.main, result.sig]))


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：宽松回退用子串匹配，readme_<目标名>.txt 会被选为主补丁。子项目 2 修复",
)
def test_select_members_exact_basename():
    files = ["vol.1/readme_adultsonly.xp3.txt"]
    result = select_members(files, "adultsonly.xp3", "NEKOPARA Vol.1")
    assert result.main is None
```

- [ ] **Step 8: 运行确认红测试为 xfail**

Run: `.venv/Scripts/python -m pytest tests/unit/test_archive_select.py -v`
Expected: 绿测试全部 PASS；2 条红测试 **XFAIL**，无 XPASS。

- [ ] **Step 9: Commit**

```bash
git add source/workers/archive_select.py source/workers/extraction_thread.py tests/unit/test_archive_select.py
git commit -m "test: 提取 workers/archive_select.py 接缝并补红绿测试"
```

---

## Task 6: `core/verification.py` 接缝

**Files:**
- Create: `source/core/verification.py`
- Create: `tests/unit/test_verification.py`
- Modify: `source/core/handlers/extraction_handler.py:146-151`
- Modify: `source/core/managers/offline_mode_manager.py:553-566`

**Interfaces:**
- Consumes: Task 1 的 `conftest.py`
- Produces:
  - `Verdict` 枚举，成员 `PASSED`、`FAILED`、`SKIPPED_NO_PATHS`
  - `decide_post_install(install_paths: dict, hash_results: dict, expected: dict) -> tuple[Verdict, str]` — 返回 `(判定, 消息)`。**照搬缺陷：`install_paths` 为空时返回 `PASSED`**。`SKIPPED_NO_PATHS` 本轮定义但不返回，供子项目 2 启用

- [ ] **Step 1: 写绿测试**

```python
# tests/unit/test_verification.py
import pytest

from core.verification import Verdict, decide_post_install

EXPECTED = {"NEKOPARA Vol.1": "aabb"}


def test_all_hashes_match_returns_passed():
    verdict, message = decide_post_install(
        {"NEKOPARA Vol.1": "D:/g/adultsonly.xp3"},
        {"D:/g/adultsonly.xp3": "aabb"},
        EXPECTED,
    )
    assert verdict is Verdict.PASSED
    assert message == ""


def test_hash_mismatch_returns_failed():
    verdict, message = decide_post_install(
        {"NEKOPARA Vol.1": "D:/g/adultsonly.xp3"},
        {"D:/g/adultsonly.xp3": "ffff"},
        EXPECTED,
    )
    assert verdict is Verdict.FAILED
    assert "NEKOPARA Vol.1" in message


def test_hash_calculation_failure_returns_failed():
    verdict, message = decide_post_install(
        {"NEKOPARA Vol.1": "D:/g/adultsonly.xp3"},
        {"D:/g/adultsonly.xp3": None},
        EXPECTED,
    )
    assert verdict is Verdict.FAILED


def test_skipped_no_paths_enum_member_exists():
    # 子项目 2 会启用该值；本轮仅确认它已定义
    assert Verdict.SKIPPED_NO_PATHS.name == "SKIPPED_NO_PATHS"
```

- [ ] **Step 2: 运行绿测试确认失败**

Run: `.venv/Scripts/python -m pytest tests/unit/test_verification.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'core.verification'`

- [ ] **Step 3: 创建 `source/core/verification.py`**

```python
"""安装后校验判定。

统一三处 fail-open 判定点：
- core/handlers/extraction_handler.py:146-151
- core/managers/offline_mode_manager.py:553-566
- workers/hash_thread.py:127-130

**照搬已知缺陷：install_paths 为空时返回 PASSED**（现状即「直接认为安装成功」）。
SKIPPED_NO_PATHS 本轮定义但不返回，供子项目 2 翻转时启用。
"""

from enum import Enum


class Verdict(Enum):
    """安装后校验的判定结果。"""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED_NO_PATHS = "skipped_no_paths"


def decide_post_install(install_paths, hash_results, expected):
    """根据哈希结果判定安装是否成功。

    Args:
        install_paths: {游戏版本: 安装路径}
        hash_results: {安装路径: 实际哈希或 None}
        expected: {游戏版本: 预期哈希}

    Returns:
        tuple[Verdict, str]: (判定, 面向用户的消息)。PASSED 时消息为 ""。

    注意：照搬现有缺陷——install_paths 为空时返回 PASSED 而非 SKIPPED_NO_PATHS。
    这是「找不到安装路径就直接认为安装成功」的 fail-open 行为，由子项目 2 修复。
    """
    if not install_paths:
        return Verdict.PASSED, ""

    for game_version, install_path in install_paths.items():
        expected_hash = expected.get(game_version)
        if not expected_hash:
            continue

        if install_path not in hash_results:
            # 照搬 hash_thread.py:127-130——目标文件不存在时直接跳过，
            # passed 保持 True。这是 fail-open 缺陷，由子项目 2 修复。
            # 注意与下面 actual is None 的区别：那是「文件在但哈希算不出来」，
            # 现状下会正确判 FAILED，不属于本轮要照搬的缺陷。
            continue

        actual = hash_results[install_path]
        if actual is None:
            return (
                Verdict.FAILED,
                f"\n无法计算 {game_version} 的文件哈希值，文件可能已损坏或被占用。\n",
            )
        if actual != expected_hash:
            return (
                Verdict.FAILED,
                f"\n检测到 {game_version} 的文件哈希值不匹配。\n",
            )

    return Verdict.PASSED, ""
```

- [ ] **Step 4: 运行绿测试确认通过**

Run: `.venv/Scripts/python -m pytest tests/unit/test_verification.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 把两处判定点改为调用接缝**

`source/core/handlers/extraction_handler.py`：顶部加入 `from core.verification import Verdict, decide_post_install`，把 `:146-151` 的

```python
        if not install_paths:
            logger.warning(f"未找到 {game_version} 的安装路径，跳过哈希校验")
            self.main_window.installed_status[game_version] = True
            self.main_window.download_manager.on_extraction_finished(True)
            return
```

替换为：

```python
        if not install_paths:
            # 判定统一走接缝：本轮接缝照搬返回 PASSED，因此 installed_status
            # 仍被置为 True，行为不变。子项目 2 只需把接缝改为返回
            # SKIPPED_NO_PATHS，此处即自动变为 fail-closed。
            verdict, _ = decide_post_install(install_paths, {}, {})
            logger.warning(f"未找到 {game_version} 的安装路径，跳过哈希校验")
            self.main_window.installed_status[game_version] = verdict is Verdict.PASSED
            self.main_window.download_manager.on_extraction_finished(True)
            return
```

`source/core/managers/offline_mode_manager.py:553-566` 做等价改造，保留其额外的 `installed_games.append` 与 `process_next_offline_install_task` 调用。

改造后 `installed_status` 仍被置为 `True`（因为接缝照搬返回 `PASSED`），**行为不变**。子项目 2 只需把接缝的返回值改为 `SKIPPED_NO_PATHS`，这两处即自动变为 fail-closed。

- [ ] **Step 6: 再次运行绿测试确认行为未变**

Run: `.venv/Scripts/python -m pytest tests/unit/test_verification.py -v`
Expected: PASS（全部）

- [ ] **Step 7: 写红测试（2 条）**

追加到 `tests/unit/test_verification.py`：

```python
@pytest.mark.xfail(
    strict=True,
    reason="审查发现：install_paths 为空时判为 PASSED（源码注释：直接认为安装成功）。子项目 2 修复",
)
def test_decide_post_install_empty_paths_fails():
    verdict, message = decide_post_install({}, {}, EXPECTED)
    assert verdict is Verdict.SKIPPED_NO_PATHS
    assert message != ""


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：目标文件不存在时 hash_thread 只 continue，passed 保持 True。子项目 2 修复",
)
def test_decide_post_install_missing_file_fails():
    # 安装路径存在于映射中，但哈希结果里没有它——对应文件不存在的情形
    verdict, message = decide_post_install(
        {"NEKOPARA Vol.1": "D:/g/adultsonly.xp3"},
        {},
        EXPECTED,
    )
    assert verdict is Verdict.FAILED
```

- [ ] **Step 8: 运行确认红测试为 xfail**

Run: `.venv/Scripts/python -m pytest tests/unit/test_verification.py -v`
Expected: 绿测试全部 PASS；2 条红测试 **XFAIL**，无 XPASS。

> `test_decide_post_install_missing_file_fails` 当前会 XFAIL 是因为 `hash_results.get(path)` 返回 `None` 走进 `FAILED` 分支——若它意外 PASS，说明实现偏离了照搬要求，需回到 Step 3 核对。

- [ ] **Step 9: Commit**

```bash
git add source/core/verification.py source/core/handlers/extraction_handler.py source/core/managers/offline_mode_manager.py tests/unit/test_verification.py
git commit -m "test: 提取 core/verification.py 接缝并补红绿测试"
```

---

## Task 7: 既有工具函数的绿测试

**Files:**
- Create: `tests/unit/test_hash_manager.py`
- Create: `tests/unit/test_resource_path.py`

**Interfaces:**
- Consumes: Task 1 的 `conftest.py`；`utils.helpers.HashManager`、`utils.helpers.resource_path`
- Produces: 无新接口。纯测试补充，不修改任何源码。

- [ ] **Step 1: 写 `HashManager` 的绿测试**

```python
# tests/unit/test_hash_manager.py
import hashlib

from utils.helpers import HashManager


def test_hash_calculate_matches_hashlib(tmp_path):
    content = b"nekopara patch payload" * 1000
    f = tmp_path / "payload.bin"
    f.write_bytes(content)

    manager = HashManager(1024)
    assert manager.hash_calculate(str(f)) == hashlib.sha256(content).hexdigest()


def test_hash_calculate_handles_empty_file(tmp_path):
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")

    manager = HashManager(1024)
    assert manager.hash_calculate(str(f)) == hashlib.sha256(b"").hexdigest()


def test_calculate_hashes_in_parallel_returns_none_for_missing_file(tmp_path):
    good = tmp_path / "good.bin"
    good.write_bytes(b"abc")
    missing = tmp_path / "missing.bin"

    manager = HashManager(1024)
    results = manager.calculate_hashes_in_parallel([str(good), str(missing)])

    assert results[str(good)] == hashlib.sha256(b"abc").hexdigest()
    assert results[str(missing)] is None
```

- [ ] **Step 2: 写 `resource_path` 的绿测试**

```python
# tests/unit/test_resource_path.py
import os

from utils.helpers import resource_path


def test_resource_path_maps_executables_to_bin():
    result = resource_path("aria2c-fast_x64.exe")
    assert os.path.basename(os.path.dirname(result)) == "bin"
    assert result.endswith("aria2c-fast_x64.exe")


def test_resource_path_maps_data_files_to_data():
    result = resource_path("ip.txt")
    assert os.path.basename(os.path.dirname(result)) == "data"


def test_resource_path_returns_absolute_path():
    assert os.path.isabs(resource_path("aria2c-fast_x64.exe"))
```

- [ ] **Step 3: 运行并确认全部通过**

Run: `.venv/Scripts/python -m pytest tests/unit/test_hash_manager.py tests/unit/test_resource_path.py -v`
Expected: PASS（全部）

若 `test_resource_path_returns_absolute_path` 失败，说明非冻结分支返回了相对路径——**这是既有行为，不要在本轮修改 `resource_path`**。改为断言实际行为并在测试上加注释说明。

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_hash_manager.py tests/unit/test_resource_path.py
git commit -m "test: 补 HashManager 与 resource_path 的绿测试"
```

---

## Task 8: Qt 冒烟测试

**Files:**
- Create: `tests/qt/test_smoke.py`

**Interfaces:**
- Consumes: Task 1 的 `conftest.py`（已设置 `QT_QPA_PLATFORM=offscreen`）；`pytest-qt` 的 `qtbot` fixture
- Produces: 证明 Qt 测试基础设施可用，供子项目 3 编写线程与状态机测试

- [ ] **Step 1: 写冒烟测试**

```python
# tests/qt/test_smoke.py
"""Qt 测试基础设施冒烟验证。

本轮只证明 QApplication 可创建、信号可被 qtbot 捕获。
线程生命周期与窗口状态机的测试留到子项目 3。
"""

from PySide6.QtCore import QObject, Signal


class _Emitter(QObject):
    fired = Signal(str)


def test_qapplication_is_available(qapp):
    assert qapp is not None


def test_qtbot_captures_signal(qtbot):
    emitter = _Emitter()
    with qtbot.waitSignal(emitter.fired, timeout=1000) as blocker:
        emitter.fired.emit("hello")
    assert blocker.args == ["hello"]


def test_offscreen_platform_is_active():
    import os

    assert os.environ["QT_QPA_PLATFORM"] == "offscreen"
```

- [ ] **Step 2: 运行并确认通过**

Run: `.venv/Scripts/python -m pytest tests/qt -v`
Expected: PASS（全部）

若 `pytest-qt` 在 offscreen 下不稳定（挂起或段错误），按 spec §12 的应对：把 Qt 测试推迟至子项目 3，删除本文件并在本计划末尾记录该偏差，然后继续 Task 9。

- [ ] **Step 3: Commit**

```bash
git add tests/qt/test_smoke.py
git commit -m "test: 添加 Qt 测试基础设施冒烟验证"
```

---

## Task 9: 手动核查清单

**Files:**
- Create: `tests/MANUAL-CHECKLIST.md`

**Interfaces:**
- Consumes: 无
- Produces: 供子项目 2 / 3 / 4 交付时逐条勾选的核查清单

- [ ] **Step 1: 创建 `tests/MANUAL-CHECKLIST.md`**

```markdown
# 手动核查清单

以下发现无法用单元测试覆盖，须人工执行并记录结果。

**本清单不计入测试覆盖率。** 报告完成度时须与自动化测试结果分开声明。

---

## 1. UAC 提权参数转发

- [ ] 以 `安装器.exe -platformpluginpath C:\Users\Public\evil` 启动，同意 UAC
- [ ] 确认提权后的进程**未**从该目录加载 DLL
- [ ] 确认安装路径含空格（如 `C:\Program Files\...`）时提权仍能正常启动
- [ ] 确认用户拒绝 UAC 时程序给出明确提示而非静默退出

对应发现：`utils/helpers.py:465`

## 2. 三处裸文件名的 PATH 劫持

- [ ] 在安装器同目录放置无害的 `curl.exe`，点击「IPv6 连接测试」，确认**未**执行该文件
- [ ] 同样方式验证 `taskkill.exe`（取消下载时触发）
- [ ] 同样方式验证 `powershell.exe`（菜单「打开 hosts 文件」时触发）

对应发现：`ipv6_manager.py:93,238`、`download.py:53`、`ui_manager.py:262`

## 3. CI 标签注入

- [ ] 推送形如 `v0.0.0-test-$(Get-Date)` 的标签到测试仓库
- [ ] 确认 runner 上**未**执行该子表达式
- [ ] 已确认前提：`git check-ref-format` 接受 `$(Get-Date)` 与 `v1.0";calc;"` 两种形式

对应发现：`.github/workflows/build-release.yml:31`

## 4. 打包产物是否仍包含 .py 源码

- [ ] 用 7-Zip 或 `pyinstxtractor` 解开发布的 exe
- [ ] 确认其中**不含** `core/`、`utils/`、`workers/`、`ui/`、`config/` 下的 `.py` 文件

对应发现：`source/build.spec:29-36`

## 5. 内置两个 exe 的签名状态

- [ ] `Get-AuthenticodeSignature source/bin/aria2c-fast_x64.exe`
- [ ] `Get-AuthenticodeSignature source/bin/cfst.exe`
- [ ] 记录结果，并在仓库中登记两者的上游版本号与 SHA-256

对应发现：`source/bin/` 二进制无校验记录

## 6. 发布产物是否附带 SHA-256

- [ ] 确认 Release 页面存在 `.sha256` 文件
- [ ] 确认其内容与实际 exe 的哈希一致

对应发现：`.github/workflows/build-release.yml` 无校验和步骤

## 7. 真实网络环境下的证书校验行为

- [ ] 在启用 Cloudflare 优选（已改写 hosts）的情况下执行一次完整下载
- [ ] 确认证书校验开启时握手成功
- [ ] 若握手失败，确认程序回退为「放弃优选 + 直连重试」，而**不是**关闭证书校验

对应发现：`workers/download.py:214`
```

> **注**：Spec §11 验收标准第 6 条写「覆盖全部 10 条无法自动化的发现」，而 §9 正文只列出 7 项。本清单以 §9 正文的 7 项为准。该计数差异已记录，若后续确认存在遗漏项，追加到本文件即可。

- [ ] **Step 2: Commit**

```bash
git add tests/MANUAL-CHECKLIST.md
git commit -m "docs: 添加无法自动化验证项的手动核查清单"
```

---

## Task 10: CI 支持手动试跑

**Files:**
- Modify: `.github/workflows/build-release.yml`

**Interfaces:**
- Consumes: Task 1 产出的 `requirements-build.txt`
- Produces: CI 可经 `workflow_dispatch` 手动触发而不发布 release，供子项目 4 安全试验 CI 改动

- [ ] **Step 1: 加入 `workflow_dispatch` 触发器**

把文件顶部的

```yaml
on:
  push:
    tags:
      - '*'  # 任意 tag 都会触发构建
```

改为

```yaml
on:
  push:
    tags:
      - '*'  # 任意 tag 都会触发构建
  workflow_dispatch:  # 允许手动触发，用于在不发版的前提下试跑构建
```

**本轮不收窄 tag 过滤、不加 `permissions`、不钉 action SHA**——那些属子项目 4。

- [ ] **Step 2: 安装步骤改指向 `requirements-build.txt`**

把

```yaml
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r source/requirements.txt
```

改为

```yaml
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-build.txt
```

同时把 `cache-dependency-path` 从 `'source/requirements.txt'` 改为 `'requirements-build.txt'`。

- [ ] **Step 3: 手动触发一次并确认构建成功**

在 GitHub Actions 页面对当前分支执行 Run workflow。

Expected: 构建成功，产出 `FRAISEMOE_Addons_Installer_NEXT.exe`，且**未创建 release**（`workflow_dispatch` 不带 tag，`softprops/action-gh-release` 会跳过）。

若 release 步骤报错，为其加上 `if: startsWith(github.ref, 'refs/tags/')` 条件。

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build-release.yml
git commit -m "ci: 支持手动触发构建并改用 requirements-build.txt"
```

---

## 最终验收

全部任务完成后，逐条核对 spec §11：

- [ ] **1.** `py -3.11 -m venv .venv` 后 `pip install -r requirements-dev.txt` 成功
- [ ] **2.** `python source/Main.py` 能启动到隐私协议对话框
- [ ] **3.** `pytest tests/unit -v` 结果为 **恰好 14 条 XFAIL** + 全部绿测试 PASS + **0 条 XPASS**

红测试分布核对表：

| 文件 | 红测试 | 条数 |
|---|---|---|
| `test_config_validate.py` | `test_validate_cloud_config_rejects_non_dict`、`test_load_config_returns_dict_for_list_json` | 2 |
| `test_hosts_text.py` | `test_remove_host_entries_keeps_subdomain`、`test_remove_host_entries_keeps_comments`、`test_strip_marked_block_keeps_orphan_neighbor`、`test_hosts_manager_restore_recovers_original`、`test_hosts_manager_backup_reads_gbk_file` | 5 |
| `test_uninstall_plan.py` | `test_uninstall_plan_excludes_game_config`、`test_uninstall_plan_excludes_patch_dir`、`test_candidates_stay_within_game_dir` | 3 |
| `test_archive_select.py` | `test_select_members_no_sig_for_non_after`、`test_select_members_exact_basename` | 2 |
| `test_verification.py` | `test_decide_post_install_empty_paths_fails`、`test_decide_post_install_missing_file_fails` | 2 |
| **合计** | | **14** |

- [ ] **4.** `pytest tests/qt -v` 全部通过
- [ ] **5.** `git diff dfd8e7c..HEAD -- source/` 经逐处审查确认为零行为变更：新文件为搬运产物，原文件仅有「删除内联逻辑、改为调用」与 `HostsManager.__init__` 签名两类改动
- [ ] **6.** `tests/MANUAL-CHECKLIST.md` 已创建，7 项均有可执行步骤

---

## 实际环境记录

> 执行 Task 1 时若发生版本偏差，在此记录：
>
> - 实际 Python 版本：
> - 是否保留 Qt 测试：
> - `source/requirements.txt` 是否需要加回额外包：
