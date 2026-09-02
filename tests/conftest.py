"""测试全局配置：使 source/ 下的模块可被导入，并让 Qt 在无显示环境运行。"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# source/ 不是 Python 包，其内部模块以 `from config.config import ...` 形式互相引用。
# 把 source/ 插入 sys.path 使这些 import 在测试中同样成立，避免改动现有源码。
SOURCE_DIR = Path(__file__).resolve().parent.parent / "source"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

# Qt 测试在无显示环境（CI、SSH）下运行需要 offscreen 平台插件。
# 必须在任何 PySide6 模块被导入之前设置。
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _stub_msgbox_frame(monkeypatch):
    """桩掉 utils.helpers.msgbox_frame，防止弹窗分支阻塞测试进程。

    offscreen 平台插件不会让 QMessageBox.exec() 自动返回。当前红测试恰好都
    绕开了带 exec() 的分支，但子项目 2 放宽 HostsManager 过窄的
    except IOError 后就会命中，届时整个 pytest 进程会挂起（CI 上表现为
    超时而非失败）。提前桩掉以消除这个隐患。
    """
    monkeypatch.setattr(
        "utils.helpers.msgbox_frame", lambda *args, **kwargs: MagicMock()
    )
